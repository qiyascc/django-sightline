"""
The write path.

The browser sends batches, this module turns them into rows. It runs on
every recorded page view, so two rules shape it:

  * Nothing here may raise into the response. A broken payload is dropped,
    never reported to the visitor, and never allowed to break the page.
  * Nothing here may be slow. Counters are updated with F expressions,
    grid cells with a single upsert per cell, and no query runs inside a
    per-event loop.
"""
from __future__ import annotations

import logging
from datetime import timedelta

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from .conf import get_setting
from .models import (Device, ElementStat, Event, HeatCell, Page, PageView,
                     ScrollBand, Session)
from .utils import bucket, clean_path, device_of, is_excluded

log = logging.getLogger("sightline")

# Anything the browser sends that is not one of these is dropped. An open
# list would let a stray script fill the table with junk kinds.
KINDS = {choice[0] for choice in Event.Kind.choices}


def _num(value, default=0):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _pct(value):
    try:
        out = float(value)
    except (TypeError, ValueError):
        return 0.0
    return min(max(out, 0.0), 1.0)


@transaction.atomic
def ingest(payload: dict, *, request) -> dict:
    """
    One batch from one page.

    Returns the ids the browser should keep using, so the next batch of the
    same visit does not open a second session.
    """
    url = payload.get("url") or "/"
    path = clean_path(url)
    if is_excluded(path):
        return {"ok": False, "reason": "excluded"}

    width = _num(payload.get("viewportWidth"))
    height = _num(payload.get("viewportHeight"))
    agent = request.META.get("HTTP_USER_AGENT", "")[:300]

    session = _session_for(payload, request, agent, width, height)
    page = _page_for(path, payload.get("title") or "")
    view = _pageview_for(payload, session, page, width, height)

    events = payload.get("events") or []
    events = events[: get_setting("MAX_BATCH")]
    written = _write_events(view, events)

    _update_counters(session, view, page, payload, written)
    _rollup(view, events)

    return {"ok": True, "session": str(session.pk), "pageview": view.pk,
             "written": written}


def _session_for(payload, request, agent, width, height) -> Session:
    """
    The visit this batch belongs to.

    The browser sends back the id it was given. If it is unknown or stale,
    a new visit starts: a session that has been idle longer than the
    timeout is a different visit even from the same browser.
    """
    from .utils import is_bot, visitor_key

    given = payload.get("session")
    cutoff = timezone.now() - timedelta(minutes=get_setting("SESSION_TIMEOUT_MINUTES"))
    if given:
        found = Session.objects.filter(pk=given, last_seen_at__gte=cutoff).first()
        if found:
            Session.objects.filter(pk=found.pk).update(last_seen_at=timezone.now())
            return found

    user = getattr(request, "user", None)
    return Session.objects.create(
        visitor_key=visitor_key(request),
        user=user if getattr(user, "is_authenticated", False) else None,
        device=device_of(agent, width),
        viewport_width=width,
        viewport_height=height,
        user_agent=agent,
        language=(request.META.get("HTTP_ACCEPT_LANGUAGE", "") or "")[:12],
        referrer=(payload.get("referrer") or "")[:500],
    )


def _page_for(path: str, title: str) -> Page:
    page, created = Page.objects.get_or_create(
        path=path, defaults={"title": title[:300]})
    if not created and title and page.title != title[:300]:
        Page.objects.filter(pk=page.pk).update(title=title[:300])
    return page


def _pageview_for(payload, session, page, width, height) -> PageView:
    given = payload.get("pageview")
    if given:
        found = PageView.objects.filter(pk=given, session=session).first()
        if found:
            return found
    return PageView.objects.create(
        session=session, page=page,
        viewport_width=width, viewport_height=height,
        document_height=_num(payload.get("documentHeight")),
    )


def _write_events(view: PageView, rows: list) -> int:
    """Rows in, rows out. One insert for the whole batch."""
    keep = []
    for row in rows:
        kind = row.get("k")
        if kind not in KINDS:
            continue
        keep.append(Event(
            pageview=view,
            kind=kind,
            t_ms=max(_num(row.get("t")), 0),
            x=_num(row.get("x")),
            y=_num(row.get("y")),
            x_pct=_pct(row.get("xp")),
            y_pct=_pct(row.get("yp")),
            scroll_y=_num(row.get("s")),
            selector=(row.get("sel") or "")[:300],
            label=(row.get("lbl") or "")[:160],
            meta=row.get("m") if isinstance(row.get("m"), dict) else {},
        ))
    if keep:
        Event.objects.bulk_create(keep, batch_size=500)
    return len(keep)


def _update_counters(session, view, page, payload, written) -> None:
    """Totals kept on the row itself, so a list page never aggregates."""
    scroll = min(max(_num(payload.get("maxScrollPct")), 0), 100)
    duration = max(_num(payload.get("durationMs")), 0)
    clicks = sum(1 for row in (payload.get("events") or []) if row.get("k") == "click")

    PageView.objects.filter(pk=view.pk).update(
        duration_ms=max(view.duration_ms, duration),
        max_scroll_pct=max(view.max_scroll_pct, scroll),
        click_count=F("click_count") + clicks,
        document_height=_num(payload.get("documentHeight")) or view.document_height,
    )

    flags = {}
    kinds = {row.get("k") for row in (payload.get("events") or [])}
    if "rage" in kinds:
        flags["has_rage"] = True
    if "dead" in kinds:
        flags["has_dead_click"] = True
    if "error" in kinds:
        flags["has_error"] = True

    Session.objects.filter(pk=session.pk).update(
        last_seen_at=timezone.now(),
        event_count=F("event_count") + written,
        duration_ms=F("duration_ms") + duration,
        **flags,
    )
    if payload.get("first"):
        Session.objects.filter(pk=session.pk).update(page_count=F("page_count") + 1)
        Page.objects.filter(pk=page.pk).update(
            view_count=F("view_count") + 1, last_seen_at=timezone.now())


def _rollup(view: PageView, rows: list) -> None:
    """
    The same events, counted into the grid.

    Done at write time rather than in a nightly job: a heatmap that only
    appears tomorrow is a heatmap nobody trusts. The cost is one upsert per
    distinct cell in the batch, which for a normal page is a handful.
    """
    day = timezone.localdate()
    device = view.session.device
    cells: dict[tuple, int] = {}
    elements: dict[str, dict] = {}

    for row in rows:
        kind = row.get("k")
        if kind not in {"click", "move", "rage", "dead"}:
            continue
        col, cell_row = bucket(_pct(row.get("xp")), _pct(row.get("yp")))
        cells[(kind, col, cell_row)] = cells.get((kind, col, cell_row), 0) + 1

        selector = (row.get("sel") or "")[:300]
        if kind in {"click", "rage", "dead"} and selector:
            slot = elements.setdefault(selector, {
                "label": (row.get("lbl") or "")[:160],
                "clicks": 0, "rage_clicks": 0, "dead_clicks": 0,
            })
            if kind == "click":
                slot["clicks"] += 1
            elif kind == "rage":
                slot["rage_clicks"] += 1
            else:
                slot["dead_clicks"] += 1

    for (kind, col, cell_row), count in cells.items():
        obj, created = HeatCell.objects.get_or_create(
            page=view.page, day=day, device=device, kind=kind,
            col=col, row=cell_row, defaults={"count": count})
        if not created:
            HeatCell.objects.filter(pk=obj.pk).update(count=F("count") + count)

    for selector, slot in elements.items():
        obj, created = ElementStat.objects.get_or_create(
            page=view.page, day=day, selector=selector,
            defaults={"label": slot["label"], "clicks": slot["clicks"],
                      "rage_clicks": slot["rage_clicks"],
                      "dead_clicks": slot["dead_clicks"]})
        if not created:
            ElementStat.objects.filter(pk=obj.pk).update(
                clicks=F("clicks") + slot["clicks"],
                rage_clicks=F("rage_clicks") + slot["rage_clicks"],
                dead_clicks=F("dead_clicks") + slot["dead_clicks"])

    _rollup_scroll(view, day, device)


def _rollup_scroll(view: PageView, day, device) -> None:
    """
    Scroll depth, counted once per page view.

    Every band up to the deepest one reached is credited, because somebody
    who got to 80 percent also saw 40 percent. The counter only moves when
    the view reaches a band it had not reached before, so a batch arriving
    every few seconds does not inflate it.
    """
    view.refresh_from_db(fields=["max_scroll_pct", "scroll_band"])
    reached = view.max_scroll_pct // 5
    if reached <= view.scroll_band:
        return
    for band in range(view.scroll_band + 1, reached + 1):
        obj, created = ScrollBand.objects.get_or_create(
            page=view.page, day=day, device=device, band=band,
            defaults={"reached": 1})
        if not created:
            ScrollBand.objects.filter(pk=obj.pk).update(reached=F("reached") + 1)
    PageView.objects.filter(pk=view.pk).update(scroll_band=reached)
