"""
Settings for Sightline.

Everything lives under a single ``SIGHTLINE`` dict so a host project never
has to learn a dozen setting names:

    SIGHTLINE = {
        "SAMPLE_RATE": 1.0,
        "RETAIN_DAYS": 90,
    }

Anything not set falls back to the defaults below. Read values through
``get_setting`` rather than touching ``settings.SIGHTLINE`` directly, so a
missing key never raises.
"""
from __future__ import annotations

from django.conf import settings

DEFAULTS = {
    # Share of visits that get recorded. 1.0 records everyone, 0.1 records
    # one in ten. The decision is made once per session, not per page, so a
    # recorded visitor stays recorded for the whole visit.
    "SAMPLE_RATE": 1.0,

    # Raw events are the bulky part. They are rolled up into grid cells and
    # then dropped after this many days. Rollups are kept forever.
    "RETAIN_DAYS": 90,

    # Sessions with no activity for this long are considered finished.
    "SESSION_TIMEOUT_MINUTES": 30,

    # Pointer positions are sampled, not streamed. One sample per this many
    # milliseconds is enough for an attention map and keeps payloads small.
    "MOVE_SAMPLE_MS": 120,

    # Heatmaps are drawn from a grid, not from raw points. The grid is
    # relative to page width, so a 1440px desktop and a 390px phone land in
    # the same buckets when their layouts match.
    "GRID_COLUMNS": 60,
    "GRID_ROWS": 200,

    # A burst of clicks in the same spot means something is not working.
    "RAGE_CLICK_COUNT": 3,
    "RAGE_CLICK_WINDOW_MS": 1000,
    "RAGE_CLICK_RADIUS_PX": 32,

    # Paths that are never recorded. Matched as prefixes.
    "EXCLUDE_PATHS": ["/admin/", "/static/", "/media/", "/sightline/"],

    # Query parameters are dropped from the recorded path by default: they
    # split one page into many and heatmaps get thin.
    "KEEP_QUERY_STRING": False,

    # Staff visits are noise in a heatmap: you click your own site far more
    # than a customer does.
    "IGNORE_STAFF": True,

    # Honour the browser Do Not Track header.
    "RESPECT_DNT": True,

    # The overlay and the replay player are staff only, always. This only
    # decides whether the tracker script is injected at all.
    "AUTO_INJECT": True,

    # Maximum events accepted in a single request. A batch larger than this
    # is truncated rather than rejected, so one bad page cannot lose a whole
    # session.
    "MAX_BATCH": 500,

    # Identifiers are hashed with this salt plus a daily rotation, so the
    # same visitor cannot be followed across days.
    "SALT": "",

    # Overlays are pages too, in the way that matters: the visitor is
    # looking at them. They have no URL, so nothing else records them.
    # Anything matching one of these is watched for opening and closing.
    "OVERLAY_SELECTORS": [
        "dialog", "[role=dialog]", "[aria-modal=true]",
        "[data-overlay]", ".modal", ".popup",
    ],

    # How often overlays are checked. Polling rather than watching every
    # attribute change: an overlay can be opened by a class, an attribute,
    # a style or a native dialog call, and one cheap loop catches all of
    # them where a mutation filter would miss three out of four.
    "OVERLAY_POLL_MS": 400,

    # CSS selectors whose clicks are recorded without text. Useful for
    # anything showing a name, an address or an order number.
    "MASK_SELECTORS": [],
}


def get_setting(name: str):
    """One setting, with the default filled in."""
    configured = getattr(settings, "SIGHTLINE", None) or {}
    if name in configured:
        return configured[name]
    return DEFAULTS[name]


def as_dict() -> dict:
    """Every setting at once. Handy for the client bootstrap payload."""
    return {key: get_setting(key) for key in DEFAULTS}
