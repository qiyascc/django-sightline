# How recording works

This page follows one visit from the first request to the heatmap, so you know exactly what is collected, when and where it ends up.

## 1. The page is served

When Django renders a page, `SightlineMiddleware` looks at the finished response and decides whether to add the tracker. It adds it only when **all** of these hold:

| Check | Why |
| --- | --- |
| The request is a `GET` | Form posts and API calls are not page views. |
| The path does not start with anything in `EXCLUDE_PATHS` | The admin, static files, media and the panel itself stay out. |
| `RESPECT_DNT` is off, or the request has no `DNT: 1` header | Visitors who ask not to be tracked are not. |
| The user agent does not look like a bot | Crawlers and uptime checks would only add noise. |
| `IGNORE_STAFF` is off, or the user is not staff | Your own clicks are not data. |
| `AUTO_INJECT` is on | You can switch injection off entirely. |
| The response is HTML, status 200, not streamed, and has `</body>` | Only real pages get a script. |
| The response has no `sightline_skip` attribute set to true | A view can opt out, see [Recording only some pages](../examples/some-pages-only.md). |

The bot check is a single case insensitive pattern over the user agent. It matches `bot`, `crawl`, `spider`, `slurp`, `bingpreview`, `facebookexternalhit`, `headlesschrome`, `lighthouse`, `pingdom`, `uptime`, `monitor`, `curl`, `wget` and `python-requests`.

When everything passes, two tags are inserted right before the last `</body>`:

```html
<script>window.__sightline = {"collect": "/sightline/collect/", "moveSampleMs": 120, "sampleRate": 1.0, ...};</script>
<script src="/static/sightline/js/tracker.js" defer></script>
```

The first carries the settings the browser needs. The second loads the tracker, deferred so it never delays rendering. If the response had a `Content-Length` header, it is updated.

## 2. The tracker decides whether to run

`tracker.js` is plain JavaScript with no dependencies. Before recording anything it checks three things:

1. **The configuration exists.** Without `window.__sightline` it stops.
2. **It is the top window.** A page loaded inside an iframe does not record. Otherwise a page that embeds part of itself, or a widget in a frame, would show up as a separate visit with a path like `srcdoc` or `about:blank`.
3. **This tab is sampled.** With `SAMPLE_RATE` below 1, the tracker draws a random number once per tab and remembers the result in `sessionStorage` under `sightline.sampled`. A visitor is recorded for the whole visit or not at all. See [Sampling](sampling.md).

## 3. What the tracker listens to

| Event kind | Recorded when | What is stored |
| --- | --- | --- |
| `click` | Any click | Position on the page, position as a fraction of the page, scroll offset, a short CSS selector of the target and its visible text |
| `rage` | The third click within `RAGE_CLICK_WINDOW_MS` and `RAGE_CLICK_RADIUS_PX` of each other | Same as a click |
| `dead` | A click on something that is not a link, button, form field, label, `summary`, `[role=button]` or element with an `onclick` attribute | Same as a click |
| `move` | The pointer moves, at most once per `MOVE_SAMPLE_MS` | Position and scroll offset |
| `scroll` | The page scrolls | Scroll offset and how far down the page the bottom of the window is |
| `input` | The visitor types into a field or changes it (a select, a checkbox) | The field's selector only. Never the value |
| `resize` | The window is resized | New width and height |
| `overlay` | An element matching `OVERLAY_SELECTORS` opens or closes | Its selector, a name and whether it opened or closed |
| `error` | A JavaScript error reaches `window` | The error message, cut to 160 characters |
| `custom` | Your code calls `sightline.mark()` | The name you gave and an optional dict |

The selector of an element is built to be short and stable: its `id` if it has one, otherwise its `data-sightline` attribute, otherwise its tag with up to two class names and its position among siblings of the same tag, prefixed with the parent's `id` when there is one. Long CSS paths are avoided because they break with every redesign.

The visible text label is the element's text, trimmed to 160 characters. Form fields (`input`, `textarea`, `select`) never get a label, and nothing inside an element matching `MASK_SELECTORS` does either.

## 4. Batches are sent

Events go into a queue, at most 400 at a time. The queue is sent to the collect URL:

* about 1.2 seconds after the page loads, so even a short visit creates a session,
* every 5 seconds after that, if anything is waiting,
* immediately after a rage click, a dead click or a popup opening,
* when the page is hidden or closed, using `navigator.sendBeacon` so the request survives the unload.

Each batch carries the page URL and title, the referrer, the window and document size, the deepest scroll reached so far, the time on the page, and the session and page view ids the server returned for the previous batch. The [HTTP endpoints](../reference/endpoints.md) page documents the exact format.

## 5. The server stores it

The collect view accepts the batch and hands it to `sightline.collector.ingest`, inside a single transaction:

1. **The path is cleaned.** The query string is dropped unless `KEEP_QUERY_STRING` is on, and the path is cut to 500 characters. An excluded path is refused here as well.
2. **The visit is found or started.** If the batch names a session that was seen within `SESSION_TIMEOUT_MINUTES`, it continues. Otherwise a new `Session` row starts, with a daily rotating visitor key, the device type, the window size, the user agent, the first 12 characters of the `Accept-Language` header and the referrer. If a signed in user sends a batch for a session that has no user yet, the session is linked to that user.
3. **The page and the page view are found or created.** Pages are stored once per path, and each load of a page in a visit is one `PageView`.
4. **Events are written** with one bulk insert. Unknown event kinds are dropped, and a batch longer than `MAX_BATCH` is cut, not rejected.
5. **Counters are updated** on the page view, the session and the page: duration, deepest scroll, clicks, number of events and pages, and the rage, dead click and error flags.
6. **The rollups are updated.** Clicks, rage clicks, dead clicks and pointer moves are counted into `HeatCell` rows: one row per page, day, device, event kind and grid cell. Clicks are also counted per element into `ElementStat`. Scroll depth is credited to `ScrollBand` rows.

The device is decided from the window width of the first batch: below 768 pixels is mobile, below 1024 is tablet, anything wider is desktop. When the width is unknown, the user agent decides.

Nothing in this path is allowed to break the page. A broken body, a wrong shape or an unexpected error is answered with a small JSON object and the visitor never notices.

## 6. Reports read the rollups

The heatmap does not scan raw events. It sums `HeatCell` rows for the page, date range, device and event kinds you picked. A page with a busy grid is a few thousand numbers, whatever the traffic, and the rollups survive the [prune](retention.md), so a heatmap from last year still draws after its raw events are gone.

Replay is the one place that reads raw events, because it needs every step of one visit.

## What is never recorded

* The text people type, unless `CAPTURE_INPUTS` is on. By default only the fact that they typed into a field is kept. Password fields keep only their length unless `CAPTURE_PASSWORDS` is on too.
* The contents of the page. Replay shows the page as it is now, not as it was. See [Session replay](session-replay.md).
* IP addresses. The visitor key is a hash that includes the date, so it changes every day. See [Privacy](privacy.md).
* Anything from staff accounts, visitors sending Do Not Track or known bots, with the default settings.
