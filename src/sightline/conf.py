###############
# Qiyas Sadıqov CC
###############

from __future__ import annotations

from django.conf import settings

DEFAULTS = {
    "SAMPLE_RATE": 1.0,

    "RETAIN_DAYS": 90,

    "PRUNE_SESSIONS": False,

    "SESSION_TIMEOUT_MINUTES": 30,

    "MOVE_SAMPLE_MS": 120,

    "GRID_COLUMNS": 60,
    "GRID_ROWS": 200,

    "RAGE_CLICK_COUNT": 3,
    "RAGE_CLICK_WINDOW_MS": 1000,
    "RAGE_CLICK_RADIUS_PX": 32,

    "EXCLUDE_PATHS": ["/admin/", "/static/", "/media/", "/sightline/"],

    "KEEP_QUERY_STRING": False,

    "IGNORE_STAFF": True,

    "RESPECT_DNT": True,

    "AUTO_INJECT": True,

    "MAX_BATCH": 500,

    "SALT": "",

    "OVERLAY_SELECTORS": [
        "dialog", "[role=dialog]", "[aria-modal=true]",
        "[data-overlay]", ".modal", ".popup",
    ],

    "OVERLAY_POLL_MS": 400,

    "MASK_SELECTORS": [],

    "PERMISSION": "sightline.view_session",

    "IP_SOURCE": "remote_addr",

    "THROTTLE_CACHE": "default",
    "THROTTLE_BATCHES": 600,
    "THROTTLE_BATCHES_SECONDS": 600,
    "THROTTLE_SESSIONS": 60,
    "THROTTLE_SESSIONS_SECONDS": 3600,

    "MAX_EVENTS_PER_SESSION": 5000,

    "MAX_META_BYTES": 1024,

    "RESOLVE_PATHS": True,

    "ROLLUP_RETAIN_DAYS": 365,
}


def get_setting(name: str):
    configured = getattr(settings, "SIGHTLINE", None) or {}
    if name in configured:
        return configured[name]
    return DEFAULTS[name]


def as_dict() -> dict:
    return {key: get_setting(key) for key in DEFAULTS}
