# Settings reference

All settings live in one dict named `SIGHTLINE` in your Django settings. Every key is optional; a key you leave out keeps its default. Settings are read on every request, so `override_settings` works in tests.

```python
SIGHTLINE = {
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
```

The block above is exactly the default configuration. List values replace the default list; they are not merged with it.

In the tables, **Browser** means the value is sent to the visitor's browser with the tracker, and **Server** that it is only used on your side.

## Recording

| Key | Type | Default | Used in |
| --- | --- | --- | --- |
| `SAMPLE_RATE` | float, 0 to 1 | `1.0` | Browser |

Share of visitors to record. The tracker draws once per browser tab and keeps the decision for the whole visit. `0.1` records about one visitor in ten. See [Sampling](../guides/sampling.md).

| Key | Type | Default | Used in |
| --- | --- | --- | --- |
| `AUTO_INJECT` | bool | `True` | Server |

Whether the middleware adds the tracker to pages. With `False`, nothing is recorded, while the staff overlay keeps working.

| Key | Type | Default | Used in |
| --- | --- | --- | --- |
| `EXCLUDE_PATHS` | list of str | `["/admin/", "/static/", "/media/", "/sightline/"]` | Server |

Path prefixes that are never recorded. Checked with `startswith` when a page is served and again when a batch arrives. Keep the Sightline mount prefix in the list. See [Excluding pages and visitors](../guides/excluding-pages.md).

| Key | Type | Default | Used in |
| --- | --- | --- | --- |
| `KEEP_QUERY_STRING` | bool | `False` | Server |

With `False`, `/shop/?page=2` is stored as `/shop/`. With `True`, every distinct query string becomes its own page. Paths are cut to 500 characters either way.

| Key | Type | Default | Used in |
| --- | --- | --- | --- |
| `IGNORE_STAFF` | bool | `True` | Server |

Skip pages served to users with `is_staff`. Turn it off while testing.

| Key | Type | Default | Used in |
| --- | --- | --- | --- |
| `RESPECT_DNT` | bool | `True` | Server |

Skip requests that carry the header `DNT: 1`.

## Visits

| Key | Type | Default | Used in |
| --- | --- | --- | --- |
| `SESSION_TIMEOUT_MINUTES` | int | `30` | Server |

A batch for a session that has not been seen for longer than this starts a new visit, even in the same tab.

| Key | Type | Default | Used in |
| --- | --- | --- | --- |
| `SALT` | str | `""` | Server |

Secret mixed into the daily visitor key. Empty means `SECRET_KEY` is used. Set it explicitly if you rotate `SECRET_KEY` and want keys within a day to stay stable. See [Privacy](../guides/privacy.md).

## Pointer and clicks

| Key | Type | Default | Used in |
| --- | --- | --- | --- |
| `MOVE_SAMPLE_MS` | int, milliseconds | `120` | Browser |

Minimum time between two recorded pointer moves. Higher means fewer events and a coarser attention map and replay. See [Attention map](../guides/attention-map.md).

| Key | Type | Default | Used in |
| --- | --- | --- | --- |
| `RAGE_CLICK_COUNT` | int | `3` | Browser |
| `RAGE_CLICK_WINDOW_MS` | int, milliseconds | `1000` | Browser |
| `RAGE_CLICK_RADIUS_PX` | int, pixels | `32` | Browser |

A click becomes a rage click when at least `RAGE_CLICK_COUNT` clicks, itself included, happened within the last `RAGE_CLICK_WINDOW_MS` and within `RAGE_CLICK_RADIUS_PX` of it horizontally and vertically. See [Rage and dead clicks](../guides/rage-and-dead-clicks.md).

| Key | Type | Default | Used in |
| --- | --- | --- | --- |
| `MASK_SELECTORS` | list of str | `[]` | Browser |

CSS selectors of areas whose text must never be stored as a click label. See [Masking](../guides/masking.md).

## Popups

| Key | Type | Default | Used in |
| --- | --- | --- | --- |
| `OVERLAY_SELECTORS` | list of str | `["dialog", "[role=dialog]", "[aria-modal=true]", "[data-overlay]", ".modal", ".popup"]` | Browser |

CSS selectors of popups, dialogs and drawers whose opening and closing is recorded and replayed. An empty list switches popup recording off. See [Popups and dialogs](../guides/popups.md).

| Key | Type | Default | Used in |
| --- | --- | --- | --- |
| `OVERLAY_POLL_MS` | int, milliseconds | `400` | Browser |

How often the tracker checks whether a popup opened or closed.

## Heatmap grid

| Key | Type | Default | Used in |
| --- | --- | --- | --- |
| `GRID_COLUMNS` | int | `60` | Server |
| `GRID_ROWS` | int | `200` | Server |

Resolution of the grid that clicks and pointer moves are counted into. Change it only before collecting data, because existing cells are drawn with the current values. See [Click heatmap](../guides/click-heatmap.md).

## Limits

| Key | Type | Default | Used in |
| --- | --- | --- | --- |
| `MAX_BATCH` | int | `500` | Server |

Most events stored from one batch. Longer batches are cut, not rejected. The tracker itself never queues more than 400 events between two sends. Independent of this setting, request bodies larger than 512 KB are refused with status 413.

## Retention

| Key | Type | Default | Used in |
| --- | --- | --- | --- |
| `RETAIN_DAYS` | int, days | `90` | `sightline_prune` |

Age after which `sightline_prune` deletes raw events. Can be overridden per run with `--days`.

| Key | Type | Default | Used in |
| --- | --- | --- | --- |
| `PRUNE_SESSIONS` | bool | `False` | `sightline_prune` |

Whether the prune also deletes old visits and their page views. Can be overridden per run with `--sessions`. See [Retention and pruning](../guides/retention.md).

| Key | Type | Default | Used in |
| --- | --- | --- | --- |
| `ROLLUP_RETAIN_DAYS` | int, days | `365` | `sightline_prune` |

Age after which `sightline_prune` deletes heatmap rollups (heat cells, scroll bands, element counts) and then pages with no page view and no rollup left. `0` or `None` keeps them forever. Can be overridden per run with `--rollup-days`.

## Access and abuse protection

| Key | Type | Default | Used in |
| --- | --- | --- | --- |
| `PERMISSION` | str or `None` | `"sightline.view_session"` | Server |

Permission a staff user needs, checked with `user.has_perm`, to open the panel, the visit list, replays, heat data and the live overlay. Superusers always pass. `None` lets every active staff user in. See [Privacy](../guides/privacy.md#who-can-see-the-data).

| Key | Type | Default | Used in |
| --- | --- | --- | --- |
| `IP_SOURCE` | str | `"remote_addr"` | Server |

Where the client address comes from: `"remote_addr"`, `"x-real-ip"` or `"xff-last"` (last `X-Forwarded-For` hop). Used for the visitor key and the throttle. See [Proxies, CDNs and CSP](../guides/proxies-and-csp.md).

| Key | Type | Default | Used in |
| --- | --- | --- | --- |
| `THROTTLE_CACHE` | str | `"default"` | Server |
| `THROTTLE_BATCHES` | int | `600` | Server |
| `THROTTLE_BATCHES_SECONDS` | int | `600` | Server |
| `THROTTLE_SESSIONS` | int | `60` | Server |
| `THROTTLE_SESSIONS_SECONDS` | int | `3600` | Server |

Per address limits on the collect endpoint: batches per window, and new visits per window. Past either limit the endpoint answers 429. `0` turns a limit off. The tracker sends at most one batch every 5 seconds per open tab, plus one on rage clicks, popups and leaving, so the default leaves room for several tabs or a small office behind one address. Counters are kept in the cache with the alias `THROTTLE_CACHE`; with several worker processes use a shared cache, because a per process memory cache counts each process separately. If the cache raises, the request is let through.

| Key | Type | Default | Used in |
| --- | --- | --- | --- |
| `MAX_EVENTS_PER_SESSION` | int | `5000` | Server |

Most events stored for one visit. Later batches of a full visit are answered with `session_full` and stored nowhere. `0` is unlimited.

| Key | Type | Default | Used in |
| --- | --- | --- | --- |
| `MAX_META_BYTES` | int | `1024` | Server |

Largest `meta` object, as compact JSON, stored on an event. A bigger one is replaced with `{}`. `0` is unlimited.

| Key | Type | Default | Used in |
| --- | --- | --- | --- |
| `RESOLVE_PATHS` | bool | `True` | Server |

Only record paths that `django.urls.resolve` matches (under any of `LANGUAGES` with i18n), so a script posting made up paths cannot fill the page list. Turn it off when pages are served outside the URLconf, for example flatpages from `FlatpageFallbackMiddleware`.

Independently of these settings, a path must be a plain site path: one leading slash, then only letters, digits and `/_-.%~:@!$&'()*+,;=`, with no backslash. Anything else is refused with 400.

## Reading settings in your code

`sightline.conf` exposes two helpers:

```python
from sightline.conf import as_dict, get_setting

get_setting("RETAIN_DAYS")
as_dict()
```

`get_setting(name)` returns your value or the default, and raises `KeyError` for an unknown name. `as_dict()` returns every key with its effective value.

## Settings outside the dict

Sightline also depends on a few standard Django settings:

| Setting | Why |
| --- | --- |
| `SECRET_KEY` | Default salt for the visitor key |
| `STATIC_URL` | Where the tracker, overlay, player and stylesheet are served from |
| `AUTH_USER_MODEL` | Visits link to this model |
| `USE_TZ`, `TIME_ZONE` | Days of the rollup tables and date ranges of the reports follow the current time zone |
