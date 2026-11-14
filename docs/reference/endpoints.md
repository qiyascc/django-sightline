# HTTP endpoints

`sightline.urls` defines six URLs in the `sightline` namespace. The paths below assume you included them under `sightline/`.

| Name | Path | Method | Access |
| --- | --- | --- | --- |
| `sightline:collect` | `/sightline/collect/` | POST | Public |
| `sightline:dashboard` | `/sightline/panel/` | GET | Staff |
| `sightline:heat_data` | `/sightline/panel/heat/` | GET | Staff |
| `sightline:sessions` | `/sightline/panel/visits/` | GET | Staff |
| `sightline:replay` | `/sightline/panel/replay/<uuid>/` | GET | Staff |
| `sightline:replay_data` | `/sightline/panel/replay/<uuid>/data/` | GET | Staff |

"Staff" means an active user with `is_staff`, checked with Django's `staff_member_required`. Anybody else is redirected to the admin login page.

## collect

Receives batches from the tracker.

* Method: `POST` only. Other methods get 405.
* CSRF: exempt.
* Body: JSON. The content type is not checked, because `sendBeacon` sends `text/plain`.

### Request body

```json
{
  "session": "b6187e14-2e51-47f5-ab29-5d984ed2d1ba",
  "pageview": 412,
  "url": "/shop/?sort=price",
  "title": "Shop | Northwind Coffee",
  "referrer": "https://www.google.com/",
  "viewportWidth": 1440,
  "viewportHeight": 900,
  "documentHeight": 2310,
  "maxScrollPct": 64,
  "durationMs": 11250,
  "first": false,
  "final": false,
  "events": [
    {"k": "move", "t": 10480, "x": 712, "y": 455, "xp": 0.49, "yp": 0.19, "s": 0},
    {"k": "click", "t": 10920, "x": 731, "y": 470, "xp": 0.51, "yp": 0.2, "s": 0,
     "sel": "[data-sightline=\"add-huila\"]", "lbl": "Add to cart"},
    {"k": "custom", "t": 11010, "lbl": "plan-picked", "m": {"plan": "pro"}}
  ]
}
```

| Field | Meaning |
| --- | --- |
| `session` | Session id from the previous answer, or `null` on the first batch of a visit |
| `pageview` | Page view id from the previous answer, or `null` on the first batch of a page |
| `url` | Path and query string. The query string is dropped unless `KEEP_QUERY_STRING` |
| `title` | Document title |
| `referrer` | `document.referrer` |
| `viewportWidth`, `viewportHeight` | Window size |
| `documentHeight` | Full document height |
| `maxScrollPct` | Deepest scroll so far on this page, 0 to 100 |
| `durationMs` | Time since the page loaded |
| `first` | True for the first batch of a page load. Counts the page view |
| `final` | True for the batch sent on unload. Not used by the server |
| `events` | List of events, cut to `MAX_BATCH` |

Event fields:

| Key | Meaning |
| --- | --- |
| `k` | Kind: `click`, `move`, `scroll`, `rage`, `dead`, `input`, `resize`, `overlay`, `error` or `custom`. Anything else is dropped |
| `t` | Milliseconds since the page loaded |
| `x`, `y` | Position in document pixels |
| `xp`, `yp` | Position as a fraction of the document, 0 to 1 |
| `s` | Scroll offset |
| `sel` | Selector of the target |
| `lbl` | Label: visible text, error message or custom event name |
| `m` | Object with extra data (popup state, custom event data) |

Missing fields default to zero or empty.

### Answers

| Case | Status | Body |
| --- | --- | --- |
| Stored | 200 | `{"ok": true, "session": "<uuid>", "pageview": 412, "written": 3}` |
| Path excluded | 200 | `{"ok": false, "reason": "excluded"}` |
| Unexpected error while storing | 200 | `{"ok": false, "reason": "error"}` |
| Not JSON | 400 | `{"ok": false, "reason": "bad_json"}` |
| JSON but not an object | 400 | `{"ok": false, "reason": "bad_shape"}` |
| `Content-Length` above 512 KB | 413 | `{"ok": false, "reason": "too_large"}` |

`written` is the number of events stored. The tracker keeps `session` and `pageview` for the next batch and stores the session id in `sessionStorage` so the next page of the visit continues it.

An unexpected error is answered with 200 on purpose: a recorder that breaks the page it records is worse than no recorder, and the browser has nothing useful to do with an error status.

The collect view does not check staff, Do Not Track or bots. Those decide whether a page gets the tracker in the first place.

## dashboard

The panel page. Query parameters:

| Parameter | Values | Default |
| --- | --- | --- |
| `days` | 1 to 365 | 30 |
| `device` | `desktop`, `tablet`, `mobile` | all |

## heat_data

JSON behind the overlay. Query parameters:

| Parameter | Meaning | Default |
| --- | --- | --- |
| `page` | Page id | |
| `path` | Page path, used when `page` is not given | |
| `days` | 1 to 365 | 30 |
| `device` | `desktop`, `tablet`, `mobile` | all |
| `kinds` | Comma separated event kinds for the cells | `click,rage,dead` |

Answer:

```json
{
  "page": {"id": 2, "path": "/shop/", "title": "Shop | Northwind Coffee"},
  "days": 7,
  "device": "",
  "columns": 60,
  "rows": 200,
  "peak": 9,
  "cells": [[31, 52, 9], [30, 52, 7], [12, 40, 3]],
  "scroll": [100, 100, 97, 94, 90, 84, 74, 68, 65, 52, 45, 0, 0, 0, 0, 0, 0, 0, 0, 0],
  "views": 35,
  "clicks": 80,
  "elements": [
    {"selector": "[data-sightline=\"add-yirgacheffe\"]", "label": "Add to cart", "clicks": 20, "rage": 0, "dead": 0}
  ]
}
```

| Field | Meaning |
| --- | --- |
| `cells` | `[column, row, count]` triples, summed over the range, busiest first, at most 6000 |
| `peak` | Highest count among the cells |
| `scroll` | Twenty values, one per five percent band from the top, each as a percentage of the most reached band |
| `views` | Page views in the range |
| `clicks` | Plain clicks on those page views |
| `elements` | The 25 most clicked elements, summed over the range |

For a path with no recorded data the answer has the same shape with `"id": 0`, empty `cells` and `elements`, and zeros.

## sessions

The visit list page. Query parameters: `signal` (`known`, `guest`, `rage`, `dead`, `error`), `device`, `q` (search over account email, visitor key and referrer) and `page`. 50 visits per page.

## replay

The player page for one visit. Answers 404 if the visit does not exist or has no page views.

## replay_data

JSON with the whole visit, read by the player:

```json
{
  "session": "b6187e14-2e51-47f5-ab29-5d984ed2d1ba",
  "device": "desktop",
  "startedAt": "2026-11-14T00:19:02.413Z",
  "durationMs": 61200,
  "userAgent": "Mozilla/5.0 ...",
  "flags": {"rage": true, "dead": true, "error": false},
  "views": [
    {
      "path": "/",
      "title": "Northwind Coffee",
      "startedAt": "2026-11-14T00:19:02.420Z",
      "durationMs": 16000,
      "viewport": [1440, 900],
      "documentHeight": 1385,
      "events": [
        ["move", 640, 700, 410, 0, "", "", {}],
        ["click", 1210, 172, 432, 0, "#hero-shop", "Shop the beans", {}],
        ["overlay", 9120, 0, 0, 0, "#signin", "Sign in", {"state": "open"}]
      ]
    }
  ]
}
```

Each event is `[kind, t_ms, x, y, scroll_y, selector, label, meta]`, ordered by time.

## Overlay parameters

These are not endpoints but query parameters understood by the middleware on any page, for staff only:

| Parameter | Meaning |
| --- | --- |
| `sightline=overlay` | Inject the overlay instead of the tracker |
| `sl_page` | Page id to load the data for |
| `sl_path` | Path to load the data for, when there is no id. Defaults to the current path |
| `sl_days`, `sl_device` | Passed along by the panel. Not applied by the overlay in 0.2.0 |
