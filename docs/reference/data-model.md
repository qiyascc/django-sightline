# Data model

Sightline uses seven tables. Four hold what happened, three hold the same events already counted for the reports.

```text
Session 1───* PageView 1───* Event
               *
               │
Page 1─────────┘
Page 1───* HeatCell
Page 1───* ScrollBand
Page 1───* ElementStat
```

The split matters. Raw events answer "what did this one person do", which needs every row and is asked rarely. Rollups answer "where does everybody click", which is asked on every heatmap load and must never scan millions of rows. So raw events are pruned after a while and rollups are kept.

All models live in `sightline.models`.

## Session

One visit: one browser tab, from the first page until it has been idle for `SESSION_TIMEOUT_MINUTES`.

| Field | Type | Notes |
| --- | --- | --- |
| `id` | UUID, primary key | Sent to the browser and back with every batch |
| `visitor_key` | char(64), indexed | Daily rotating salted hash, 40 hex characters |
| `user` | FK to `AUTH_USER_MODEL`, nullable | Set when the visitor was signed in at any point. `on_delete=SET_NULL`, related name `sightline_sessions` |
| `device` | `desktop`, `tablet` or `mobile`, indexed | From the window width of the first batch |
| `viewport_width`, `viewport_height` | int | Window size of the first batch |
| `user_agent` | char(300) | |
| `language` | char(12) | Start of `Accept-Language` |
| `referrer` | char(500) | |
| `started_at` | datetime, indexed | |
| `last_seen_at` | datetime | Updated by every batch |
| `duration_ms` | int | Sum of the time reported by the batches |
| `page_count` | int | Pages loaded in the visit |
| `event_count` | int | Events stored |
| `has_rage` | bool, indexed | At least one rage click |
| `has_dead_click` | bool | At least one dead click |
| `has_error` | bool | At least one JavaScript error |

Properties:

* `duration_seconds`: `duration_ms` rounded to seconds.
* `is_interesting`: true when any of the three flags is set or the visit lasted longer than two minutes.

Default ordering is newest first.

## Page

One recorded path.

| Field | Type | Notes |
| --- | --- | --- |
| `path` | char(500), unique | Without query string unless `KEEP_QUERY_STRING` |
| `title` | char(300) | The document title, updated when it changes |
| `first_seen_at` | datetime | |
| `last_seen_at` | datetime, indexed | |
| `view_count` | int, indexed | Page loads, all time |

## PageView

One load of a page inside a visit.

| Field | Type | Notes |
| --- | --- | --- |
| `session` | FK to `Session`, cascade | Related name `pageviews` |
| `page` | FK to `Page`, cascade | Related name `views` |
| `started_at` | datetime, indexed | |
| `duration_ms` | int | Longest time on the page reported by a batch |
| `viewport_width`, `viewport_height` | int | Window size, used by replay |
| `document_height` | int | Height of the whole document |
| `max_scroll_pct` | int | Deepest scroll, 0 to 100 |
| `click_count` | int | Plain clicks |
| `scroll_band` | int | Deepest scroll band already credited to `ScrollBand` |

## Event

One thing that happened on a page view.

| Field | Type | Notes |
| --- | --- | --- |
| `pageview` | FK to `PageView`, cascade | Related name `events` |
| `kind` | choice, indexed | See below |
| `t_ms` | int | Milliseconds since the page loaded |
| `x`, `y` | int | Position in document pixels, used by replay |
| `x_pct`, `y_pct` | float, 0 to 1 | Position as a fraction of the document, used by the heatmap |
| `scroll_y` | int | Scroll offset at that moment |
| `selector` | char(300) | Short CSS selector of the target |
| `label` | char(160) | Visible text of the target, the error message, or the custom event name |
| `meta` | JSON | Popup state, or the data passed to `sightline.mark()` |

`Event.Kind` has these values:

| Value | Label |
| --- | --- |
| `click` | Click |
| `move` | Pointer move |
| `scroll` | Scroll |
| `rage` | Rage click |
| `dead` | Dead click |
| `input` | Typing |
| `resize` | Resize |
| `overlay` | Overlay shown or hidden |
| `error` | Script error |
| `custom` | Custom |

## HeatCell

Events counted into the grid. One row per page, day, device, kind and cell.

| Field | Type | Notes |
| --- | --- | --- |
| `page` | FK to `Page`, cascade | Related name `cells` |
| `day` | date, indexed | In the current time zone |
| `device` | choice | |
| `kind` | choice | `click`, `rage`, `dead` or `move` |
| `col`, `row` | int | Cell in the `GRID_COLUMNS` by `GRID_ROWS` grid |
| `count` | int | |

Unique on (`page`, `day`, `device`, `kind`, `col`, `row`).

## ScrollBand

How many page views reached each five percent band of a page.

| Field | Type | Notes |
| --- | --- | --- |
| `page` | FK to `Page`, cascade | Related name `bands` |
| `day` | date, indexed | |
| `device` | choice | |
| `band` | int, 1 to 20 | Band 1 is the top five percent, band 20 the bottom |
| `reached` | int | Page views that reached this band |

Unique on (`page`, `day`, `device`, `band`).

## ElementStat

Clicks per element per page per day.

| Field | Type | Notes |
| --- | --- | --- |
| `page` | FK to `Page`, cascade | Related name `elements` |
| `day` | date, indexed | |
| `selector` | char(300) | |
| `label` | char(160) | Label of the first click of the day |
| `clicks` | int | Plain clicks |
| `rage_clicks` | int | |
| `dead_clicks` | int | |

Unique on (`page`, `day`, `selector`). Default ordering is by clicks, most first.

## Panel

A proxy of `Session` with no fields of its own. It exists only to put a **Sightline panel** link in the admin sidebar; its admin list page redirects to the panel.

## Device

`sightline.models.Device` is a `TextChoices` with `DESKTOP`, `TABLET` and `MOBILE`.

## Writing your own queries

The models are normal Django models and safe to query. A few examples:

```python
from datetime import timedelta

from django.db.models import Avg, Count, Sum
from django.utils import timezone

from sightline.models import Event, Page, PageView, Session

week = timezone.now() - timedelta(days=7)

Session.objects.filter(started_at__gte=week).values("device").annotate(n=Count("id"))

PageView.objects.filter(page__path="/pricing/", started_at__gte=week).aggregate(
    views=Count("id"), scroll=Avg("max_scroll_pct"), clicks=Sum("click_count"),
)

Event.objects.filter(kind="error", pageview__started_at__gte=week).values("label").annotate(
    n=Count("id"),
).order_by("-n")[:10]

Page.objects.order_by("-view_count")[:20]
```

Do not write to these tables yourself. The counters and rollups are kept consistent by the collector, and the admin shows them read only for the same reason.
