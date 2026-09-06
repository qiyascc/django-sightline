"""
Small helpers shared by the collector and the reports.

Two of them carry the privacy promise: ``visitor_key`` never stores an
address, and ``clean_path`` never stores a query string unless the host
project asks for one.
"""
from __future__ import annotations

import hashlib
import re
from datetime import date
from urllib.parse import urlsplit

from django.conf import settings

from .conf import get_setting

MOBILE_RE = re.compile(r"(android|iphone|ipod|windows phone|mobile)", re.I)
TABLET_RE = re.compile(r"(ipad|tablet|playbook|silk)", re.I)
BOT_RE = re.compile(
    r"(bot|crawl|spider|slurp|bingpreview|facebookexternalhit|headlesschrome"
    r"|lighthouse|pingdom|uptime|monitor|curl|wget|python-requests)", re.I)


def client_ip(request) -> str:
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "") or ""


def visitor_key(request, day: date | None = None) -> str:
    """
    A stable id for one browser on one day.

    Address and user agent go in, a hash comes out, and the day is part of
    the input so the hash changes at midnight. That is enough to count
    unique visitors and not enough to follow one across a week.
    """
    day = day or date.today()
    salt = get_setting("SALT") or getattr(settings, "SECRET_KEY", "")
    raw = "|".join([
        client_ip(request),
        request.META.get("HTTP_USER_AGENT", "")[:200],
        request.META.get("HTTP_ACCEPT_LANGUAGE", "")[:60],
        day.isoformat(),
        str(salt),
    ])
    return hashlib.sha256(raw.encode("utf-8", "ignore")).hexdigest()[:40]


def device_of(user_agent: str, width: int = 0) -> str:
    """
    Desktop, tablet or phone.

    Width wins when it is known: a phone held sideways is still a phone,
    and a desktop window dragged narrow is still a desktop, but the layout
    the visitor saw is what a heatmap has to match.
    """
    from .models import Device

    if width:
        if width < 768:
            return Device.MOBILE
        if width < 1024:
            return Device.TABLET
        return Device.DESKTOP
    if TABLET_RE.search(user_agent or ""):
        return Device.TABLET
    if MOBILE_RE.search(user_agent or ""):
        return Device.MOBILE
    return Device.DESKTOP


def is_bot(user_agent: str) -> bool:
    return bool(BOT_RE.search(user_agent or ""))


def clean_path(url: str) -> str:
    """
    The path a heatmap is drawn for.

    Query strings are dropped by default. Keeping them turns one busy page
    into a hundred thin ones, and a heatmap needs volume to mean anything.
    """
    parts = urlsplit(url or "/")
    path = parts.path or "/"
    if get_setting("KEEP_QUERY_STRING") and parts.query:
        path = f"{path}?{parts.query}"
    return path[:500]


def is_excluded(path: str) -> bool:
    return any(path.startswith(prefix) for prefix in get_setting("EXCLUDE_PATHS"))


def should_record(request) -> bool:
    """Whether this request is allowed to carry the tracker."""
    if request.method != "GET":
        return False
    if is_excluded(request.path):
        return False
    if get_setting("RESPECT_DNT") and request.META.get("HTTP_DNT") == "1":
        return False
    if is_bot(request.META.get("HTTP_USER_AGENT", "")):
        return False
    user = getattr(request, "user", None)
    if get_setting("IGNORE_STAFF") and getattr(user, "is_staff", False):
        return False
    return True


def bucket(x_pct: float, y_pct: float) -> tuple[int, int]:
    """A point on the page becomes a cell in the grid."""
    cols = get_setting("GRID_COLUMNS")
    rows = get_setting("GRID_ROWS")
    col = min(max(int(x_pct * cols), 0), cols - 1)
    row = min(max(int(y_pct * rows), 0), rows - 1)
    return col, row
