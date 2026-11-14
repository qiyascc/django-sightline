# Performance and sizing

Sightline runs inside your own Django and your own database, so its cost is your cost. This page lists what it adds to the browser, the server and the database, with measured numbers where there are any, and the settings that change them.

## In the browser

* **The tracker** is one file, about 10 KB, about 3 KB gzipped. It has no dependencies and is loaded with `defer`, so it never blocks rendering.
* **Listeners are passive** where the browser allows it (`mousemove`, `scroll`, `resize`), so they never delay scrolling.
* **Pointer moves are sampled**, at most one every `MOVE_SAMPLE_MS` (120 ms).
* **The popup check** runs every `OVERLAY_POLL_MS` (400 ms) and queries the page once per run with the selectors from `OVERLAY_SELECTORS`. On very large pages with many matching elements, a longer interval or a shorter selector list lowers the cost.
* **Every listener is wrapped** so that an error inside the tracker can never break your page.

## Requests

A recorded page sends:

* one batch about 1.2 seconds after load,
* one batch every 5 seconds while there are new events,
* one batch right after a rage click, a dead click or a popup opening,
* one final batch through `sendBeacon` when the page is hidden or closed.

An idle visitor who reads without moving the pointer sends nothing between the first and the last batch. A batch carries at most 400 events from the browser; the server cuts anything beyond `MAX_BATCH` (500). Bodies larger than 512 KB are refused.

On a site with 1000 visitors browsing at the same moment, expect roughly 100 to 200 collect requests per second at peak. Use [sampling](sampling.md) to scale that down.

## On the server

Each batch is handled in one database transaction:

* a few queries to find or create the session, the page and the page view,
* one bulk insert for all the events,
* a few counter updates using `F()` expressions, so concurrent batches never overwrite each other,
* one lookup and one insert or update per **distinct** heat cell, element and new scroll band in the batch.

The last item is the variable part. A batch with a lot of pointer movement can touch a few dozen grid cells, each costing one to three small queries. On PostgreSQL or MySQL this is quick, but it is not free: the collect view is the hottest code path Sightline has, and it runs on your normal web workers.

If collect requests start to compete with your page requests:

1. Lower `SAMPLE_RATE`. This is the most effective lever.
2. Raise `MOVE_SAMPLE_MS`, which reduces both events and distinct cells per batch.
3. Give your application server more workers, or route `/sightline/collect/` to a separate pool of workers at the proxy.

## In the database

### Measured sizes

In a test run with SQLite, 30 visits with heavy pointer use produced 91 page views and 2179 events. The event table with its indexes took about 230 KB, a little over 100 bytes per event. The shares of event kinds were:

| Kind | Share |
| --- | --- |
| `move` | 52% |
| `input` | 28% |
| `click`, `rage`, `dead` | 13% |
| `scroll` | 5% |
| `custom`, `overlay` | 2% |

Typing produces one `input` event per keystroke, which is why forms weigh so much. Real visits move the pointer less than a test script, so treat these numbers as an upper bound, and measure your own site with `sightline_stats` after a week.

### What grows with what

| Table | Grows with |
| --- | --- |
| `Event` | Traffic times activity. Pruned after `RETAIN_DAYS` |
| `Session`, `PageView` | Visits and page loads. Small rows |
| `HeatCell` | Distinct cells per page, day, device and kind. Bounded by the grid size, so it grows with the number of pages and days, not with traffic |
| `ScrollBand` | At most 20 rows per page, day and device |
| `ElementStat` | Distinct clicked elements per page and day |
| `Page` | Distinct paths. Keep `KEEP_QUERY_STRING` off unless you need it |

### Rough planning

For a site with 10,000 recorded page views a day and about 60 events per page view, raw events add around 600,000 rows a day. At a little over 100 bytes each, 90 days of retention is in the range of 5 to 6 GB on SQLite, often more on PostgreSQL with its row overhead. Halving `RETAIN_DAYS`, sampling at 0.5 or raising `MOVE_SAMPLE_MS` each cut that roughly in half.

### Database choice

SQLite is fine for trying Sightline and for small sites. Every batch is a write, and SQLite allows one writer at a time, so a busy site should use PostgreSQL or MySQL.

### Indexes

The models come with the indexes their queries need: events by page view and time, events by kind, heat cells by page, device, kind and day, sessions by start time and by the rage flag, page views by page and time. You do not need to add any for the panel.

## Reports

* **Heatmaps** sum heat cells for one page and a date range. At most 6000 cells come back, whatever the traffic.
* **The panel** aggregates page views and sessions for the chosen range. With very long ranges on a big site, this is the query to watch; the 1, 7, 30 and 90 day buttons keep it reasonable.
* **Replay** reads the events of one visit.
