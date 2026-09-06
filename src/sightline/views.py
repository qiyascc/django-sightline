"""
Endpoints.

One is public and takes writes from the browser. The rest are staff only
and take none: they read, and they read from rollups wherever they can.
"""
from __future__ import annotations

import json
from datetime import timedelta

from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count, Q, Sum
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from .collector import ingest
from .conf import get_setting
from .models import (Device, ElementStat, Event, HeatCell, Page, PageView,
                     ScrollBand, Session)
from .utils import should_record

MAX_BODY = 512 * 1024


@csrf_exempt
@require_POST
def collect(request):
    """
    The write endpoint.

    No CSRF token: the tracker fires from ``sendBeacon`` during page unload,
    where a token round trip is not available and the request carries no
    credentials worth protecting. Nothing here reads or changes anything
    belonging to a signed in user, so there is nothing for a forged request
    to steal. The guards that matter are size and shape, below.
    """
    if int(request.META.get("CONTENT_LENGTH") or 0) > MAX_BODY:
        return JsonResponse({"ok": False, "reason": "too_large"}, status=413)
    try:
        payload = json.loads(request.body.decode("utf-8", "ignore") or "{}")
    except ValueError:
        return JsonResponse({"ok": False, "reason": "bad_json"}, status=400)
    if not isinstance(payload, dict):
        return JsonResponse({"ok": False, "reason": "bad_shape"}, status=400)

    try:
        result = ingest(payload, request=request)
    except Exception:                                # noqa: BLE001
        # A recorder that breaks the site it records is worse than no
        # recorder. The failure is logged by Django and the page moves on.
        return JsonResponse({"ok": False, "reason": "error"}, status=200)
    return JsonResponse(result)


# ---------------------------------------------------------------- reports

def _range(request):
    """Days requested, capped so nobody asks for a decade by accident."""
    try:
        days = int(request.GET.get("days", 30))
    except ValueError:
        days = 30
    days = min(max(days, 1), 365)
    end = timezone.localdate()
    return end - timedelta(days=days - 1), end, days


def _device(request) -> str:
    value = request.GET.get("device", "")
    return value if value in dict(Device.choices) else ""


@staff_member_required
@require_GET
def heat_data(request):
    """
    The numbers behind one heatmap.

    Cells come back as flat triples so the payload stays small: a page with
    a busy grid is a few thousand numbers, not a few thousand objects.
    """
    page = get_object_or_404(Page, pk=request.GET.get("page"))
    start, end, days = _range(request)
    device = _device(request)
    kinds = request.GET.get("kinds", "click,rage,dead").split(",")
    kinds = [k for k in kinds if k in dict(Event.Kind.choices)] or ["click"]

    rows = HeatCell.objects.filter(page=page, day__range=(start, end), kind__in=kinds)
    if device:
        rows = rows.filter(device=device)
    rows = (rows.values("col", "row")
            .annotate(n=Sum("count")).order_by("-n")[:6000])

    cells = [[r["col"], r["row"], r["n"]] for r in rows]
    peak = max((c[2] for c in cells), default=0)

    bands = ScrollBand.objects.filter(page=page, day__range=(start, end))
    if device:
        bands = bands.filter(device=device)
    band_rows = dict(bands.values_list("band").annotate(n=Sum("reached")))
    top_band = max(band_rows.values(), default=0) or 1
    scroll = [round(band_rows.get(i, 0) / top_band * 100) for i in range(1, 21)]

    views = PageView.objects.filter(page=page, started_at__date__range=(start, end))
    if device:
        views = views.filter(session__device=device)
    totals = views.aggregate(n=Count("id"), clicks=Sum("click_count"))

    elements = (ElementStat.objects
                .filter(page=page, day__range=(start, end))
                .values("selector", "label")
                .annotate(clicks=Sum("clicks"), rage=Sum("rage_clicks"),
                          dead=Sum("dead_clicks"))
                .order_by("-clicks")[:25])

    return JsonResponse({
        "page": {"id": page.pk, "path": page.path, "title": page.title},
        "days": days,
        "device": device,
        "columns": get_setting("GRID_COLUMNS"),
        "rows": get_setting("GRID_ROWS"),
        "peak": peak,
        "cells": cells,
        "scroll": scroll,
        "views": totals["n"] or 0,
        "clicks": totals["clicks"] or 0,
        "elements": list(elements),
    })


@staff_member_required
@require_GET
def replay_data(request, session_id):
    """
    One visit, ready to play back.

    Events are grouped by page view because a replay is a sequence of
    pages, not one long stream: the player reloads the page frame between
    them.
    """
    session = get_object_or_404(Session, pk=session_id)
    views = (PageView.objects.filter(session=session)
             .select_related("page").order_by("started_at"))

    out = []
    for view in views:
        rows = (Event.objects.filter(pageview=view)
                .order_by("t_ms", "id")
                .values("kind", "t_ms", "x", "y", "scroll_y", "selector", "label"))
        out.append({
            "path": view.page.path,
            "title": view.page.title,
            "startedAt": view.started_at.isoformat(),
            "durationMs": view.duration_ms,
            "viewport": [view.viewport_width, view.viewport_height],
            "documentHeight": view.document_height,
            "events": [[r["kind"], r["t_ms"], r["x"], r["y"], r["scroll_y"],
                        r["selector"], r["label"]] for r in rows],
        })

    return JsonResponse({
        "session": str(session.pk),
        "device": session.device,
        "startedAt": session.started_at.isoformat(),
        "durationMs": session.duration_ms,
        "userAgent": session.user_agent,
        "flags": {"rage": session.has_rage, "dead": session.has_dead_click,
                  "error": session.has_error},
        "views": out,
    })


@staff_member_required
@require_GET
def dashboard(request):
    """Pages, sessions and the two entry points into the visual tools."""
    start, end, days = _range(request)
    device = _device(request)

    views = PageView.objects.filter(started_at__date__range=(start, end))
    if device:
        views = views.filter(session__device=device)

    pages = (views.values("page__id", "page__path", "page__title")
             .annotate(views=Count("id"), clicks=Sum("click_count"),
                       scroll=Sum("max_scroll_pct"))
             .order_by("-views")[:50])
    pages = [{
        "id": row["page__id"],
        "path": row["page__path"],
        "title": row["page__title"],
        "views": row["views"],
        "clicks": row["clicks"] or 0,
        "scroll": round((row["scroll"] or 0) / max(row["views"], 1)),
    } for row in pages]

    sessions = Session.objects.filter(started_at__date__range=(start, end))
    if device:
        sessions = sessions.filter(device=device)
    totals = sessions.aggregate(
        n=Count("id"),
        rage=Count("id", filter=Q(has_rage=True)),
        dead=Count("id", filter=Q(has_dead_click=True)),
        errors=Count("id", filter=Q(has_error=True)),
    )

    recent = (sessions.order_by("-started_at")
              .select_related("user")[:40])

    return render(request, "sightline/dashboard.html", {
        **_admin_context(request),
        "title": "Sightline",
        "pages": pages,
        "sessions": recent,
        "totals": totals,
        "days": days,
        "device": device,
        "devices": Device.choices,
        "ranges": [1, 7, 30, 90],
    })


@staff_member_required
@require_GET
def replay(request, session_id):
    """The player page. All the work happens in the browser."""
    session = get_object_or_404(Session, pk=session_id)
    first = PageView.objects.filter(session=session).order_by("started_at").first()
    if first is None:
        raise Http404("This visit has no recorded pages")
    return render(request, "sightline/replay.html", {
        **_admin_context(request),
        "title": "Session replay",
        "session": session,
        "first_path": first.page.path,
    })


def _admin_context(request) -> dict:
    """
    Admin chrome around our own pages.

    The dashboard lives inside the admin so it inherits the host project's
    theme, whether that is stock Django or something like Unfold.
    """
    from django.contrib import admin
    return admin.site.each_context(request)
