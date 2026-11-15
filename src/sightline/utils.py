###############
# Qiyas Sadıqov CC
###############

from __future__ import annotations

import hashlib
import ipaddress
import json
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


PATH_RE = re.compile(r"^/(?![/\\])[A-Za-z0-9/_\-.%~:@!$&'()*+,;=]*$")
QUERY_RE = re.compile(r"^[A-Za-z0-9/_\-.%~:@!$&'()*+,;=?]*$")

SCRIPT_ESCAPES = {ord("<"): "\\u003C", ord(">"): "\\u003E", ord("&"): "\\u0026",
                  0x2028: "\\u2028", 0x2029: "\\u2029"}


def _ip(value: str) -> str:
    value = (value or "").strip()
    try:
        return str(ipaddress.ip_address(value))
    except ValueError:
        return ""


def client_ip(request) -> str:
    """The address used for visitor keys and throttling.

    SIGHTLINE["IP_SOURCE"] picks where it comes from:
    "remote_addr" (default) trusts only the socket address, "x-real-ip"
    trusts the X-Real-IP header set by your proxy, and "xff-last" trusts
    the last hop of X-Forwarded-For, the one your own proxy appended.
    The first X-Forwarded-For entry is never used, the client writes it.
    """
    remote = request.META.get("REMOTE_ADDR", "") or ""
    source = str(get_setting("IP_SOURCE") or "remote_addr").lower().replace("_", "-")
    if source == "x-real-ip":
        return _ip(request.META.get("HTTP_X_REAL_IP", "")) or remote
    if source == "xff-last":
        hops = [hop for hop in request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")
                if hop.strip()]
        return (_ip(hops[-1]) if hops else "") or remote
    return remote


def script_json(value) -> str:
    """JSON that is safe to place inside an inline <script> element."""
    return json.dumps(value).translate(SCRIPT_ESCAPES)


def visitor_key(request, day: date | None = None) -> str:
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
    try:
        parts = urlsplit(url or "/")
    except ValueError:
        return ""
    path = parts.path or "/"
    if get_setting("KEEP_QUERY_STRING") and parts.query:
        path = f"{path}?{parts.query}"
    return path[:500]


def is_safe_path(path: str) -> bool:
    """A site relative path that cannot point anywhere else.

    It starts with exactly one slash, holds only plain URL characters and
    has no backslash, so it cannot turn into //host or /\\host when a
    browser follows it.
    """
    if not isinstance(path, str) or not path:
        return False
    head, mark, query = path.partition("?")
    if not PATH_RE.match(head):
        return False
    return not mark or bool(QUERY_RE.match(query))


def overlay_link(path: str, **params) -> str:
    """The heatmap overlay link for a recorded path, or "" when unsafe."""
    from urllib.parse import urlencode

    if not is_safe_path(path):
        return ""
    head = path.partition("?")[0]
    return f"{head}?{urlencode({'sightline': 'overlay', **params})}"


def resolves(path: str) -> bool:
    from django.urls import Resolver404, get_script_prefix, resolve
    from django.utils import translation

    head = path.partition("?")[0]
    prefix = get_script_prefix()
    if prefix != "/" and head.startswith(prefix):
        head = "/" + head[len(prefix):]
    try:
        resolve(head)
        return True
    except Resolver404:
        pass
    if getattr(settings, "USE_I18N", False):
        for code, _name in getattr(settings, "LANGUAGES", []):
            with translation.override(code):
                try:
                    resolve(head)
                    return True
                except Resolver404:
                    continue
    return False


def can_view_panel(user) -> bool:
    """Staff who also hold SIGHTLINE["PERMISSION"]. Superusers always pass."""
    if not (getattr(user, "is_active", False) and getattr(user, "is_staff", False)):
        return False
    perm = get_setting("PERMISSION")
    return not perm or user.has_perm(perm)


def throttle(bucket_name: str, ident: str, limit, seconds) -> bool:
    """Count one hit; False once `limit` hits were seen within `seconds`."""
    if not limit or not seconds:
        return True
    from django.core.cache import caches

    digest = hashlib.sha256(ident.encode("utf-8", "ignore")).hexdigest()[:32]
    key = f"sightline:throttle:{bucket_name}:{digest}"
    try:
        cache = caches[get_setting("THROTTLE_CACHE")]
        cache.add(key, 0, int(seconds))
        try:
            count = cache.incr(key)
        except ValueError:
            cache.set(key, 1, int(seconds))
            count = 1
    except Exception:
        return True
    return count <= int(limit)


def is_excluded(path: str) -> bool:
    return any(path.startswith(prefix) for prefix in get_setting("EXCLUDE_PATHS"))


def should_record(request) -> bool:
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
    cols = get_setting("GRID_COLUMNS")
    rows = get_setting("GRID_ROWS")
    col = min(max(int(x_pct * cols), 0), cols - 1)
    row = min(max(int(y_pct * rows), 0), rows - 1)
    return col, row
