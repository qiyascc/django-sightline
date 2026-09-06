# django-sightline

Click heatmaps, scroll maps and session replay for Django, with an admin
panel and a live overlay you open on the real site.

No third party service, no external script, no account. Everything is
stored in your own database and rendered by your own server.

![status](https://img.shields.io/badge/status-beta-blue) ![python](https://img.shields.io/badge/python-3.10%2B-blue) ![django](https://img.shields.io/badge/django-4.2%2B-green) ![license](https://img.shields.io/badge/license-MIT-lightgrey)

## What you get

* **Click heatmap.** Where people click, drawn as heat over the page.
* **Attention map.** Where the pointer spends its time.
* **Scroll map.** How far down each page visitors actually get.
* **Rage clicks.** Several clicks in the same spot in a second, which
  usually means something is not responding.
* **Dead clicks.** Clicks on things that are not clickable.
* **Session replay.** Pointer, scrolling, clicks and typing markers played
  back over the page.
* **Element list.** Clicks per element, so you can see which button wins.
* **Live overlay.** Open any page of your site with the heatmap drawn on
  top of it. Staff only.
* **Admin panel.** Pages, visits and signals in one screen inside your
  existing Django admin.

## Install

```bash
pip install django-sightline
```

Or from a checkout:

```bash
pip install -e /path/to/django-sightline
```

Add the app, the middleware and the URLs:

```python
# settings.py
INSTALLED_APPS = [
    ...
    "sightline",
]

MIDDLEWARE = [
    ...
    # Last, so it sees the finished HTML.
    "sightline.middleware.SightlineMiddleware",
]
```

```python
# urls.py
from django.urls import include, path

urlpatterns = [
    ...
    path("sightline/", include("sightline.urls")),
]
```

Then:

```bash
python manage.py migrate
python manage.py collectstatic
```

That is the whole setup. The tracker is injected into HTML responses
automatically, so no template changes are needed.

## Using it

Open the admin. There is a **Sightline panel** entry in the sidebar.

* **Pages** lists everything recorded. "Open heatmap" opens that page on
  your live site with the overlay on top of it.
* **Recent visits** lists sessions. "Replay" plays one back.

In the overlay you can switch between clicks, attention and scroll depth,
change the date range, filter by device and change the opacity. Close puts
the page back to normal.

## Why is the panel empty

Staff visits are not recorded. That is deliberate, and it is the single
most common reason a fresh install looks broken: you browse your own site
while signed in to the admin, then open the panel and see nothing.

Open the site in a private window, or in a browser where you are signed
out, and the first visit appears within a few seconds.

To record staff as well, set `SIGHTLINE = {"IGNORE_STAFF": False}`. Useful
while testing, noisy in daily use.

The panel also has an **Open the heatmap on any page** box. Type a path and
it opens the overlay there, whether or not that page has been recorded yet.

## Settings

Everything lives in one dict and everything is optional:

```python
SIGHTLINE = {
    "SAMPLE_RATE": 1.0,             # 0.1 records one visitor in ten
    "RETAIN_DAYS": 90,              # raw events are pruned after this
    "SESSION_TIMEOUT_MINUTES": 30,
    "MOVE_SAMPLE_MS": 120,          # pointer sampling interval
    "GRID_COLUMNS": 60,             # heatmap grid
    "GRID_ROWS": 200,
    "RAGE_CLICK_COUNT": 3,
    "RAGE_CLICK_WINDOW_MS": 1000,
    "RAGE_CLICK_RADIUS_PX": 32,
    "EXCLUDE_PATHS": ["/admin/", "/static/", "/media/", "/sightline/"],
    "KEEP_QUERY_STRING": False,
    "IGNORE_STAFF": True,           # your own clicks are not data
    "RESPECT_DNT": True,
    "AUTO_INJECT": True,
    "MAX_BATCH": 500,
    "SALT": "",                     # defaults to SECRET_KEY
    "MASK_SELECTORS": [],           # never read text inside these
}
```

Keep the mount prefix in `EXCLUDE_PATHS` so the recorder does not record
itself.

## Custom events

```javascript
sightline.mark("checkout-started");
sightline.mark("plan-picked", { plan: "pro" });
```

## Housekeeping

```bash
python manage.py sightline_prune            # drop old raw events
python manage.py sightline_prune --dry-run  # count first
python manage.py sightline_stats --days 7   # quick summary
```

Run the prune from cron, weekly is enough. Heatmap numbers are aggregates
and survive pruning, so old maps still draw after their raw events are
gone.

## Privacy

The package is built so that a heatmap does not become a surveillance log.

* **No addresses are stored.** Visitors are identified by a salted hash
  that includes the date, so the same person looks like a new visitor
  tomorrow.
* **No text is recorded.** Typing is stored as "somebody typed in this
  field", never as what was typed. Input values never leave the browser.
* **No screen contents are recorded.** Replay is a pointer over your
  current page, not a recording of what the visitor saw.
* **Do Not Track is honoured** by default.
* **Staff are excluded** by default.

Add `MASK_SELECTORS` for regions whose element text should not be stored
either, for example a container showing a customer name.

## How replay works, exactly

Say it plainly, because the difference matters. Sightline records
interactions, not the DOM. Playback loads the page as it exists now in an
iframe and moves a cursor over it, scrolling as the visitor scrolled and
marking each click.

The page is fetched and written into the frame rather than loaded by URL.
Django sends `X-Frame-Options: DENY` on every response by default, and many
sites add it again at the proxy, so pointing an iframe at your own page
shows a broken document icon and nothing else. Writing the HTML in
sidesteps that: there is no navigation, so there is no header to refuse it.
Scripts are stripped on the way in, which also keeps the replayed page from
starting a recording of its own.

The frame is sized to the viewport the visitor had and scaled down to fit.
A phone visit replays at phone width, so the cursor lands on the elements
the visitor actually saw.

What that buys you: a tiny recorder, a small database, and no risk of
storing personal data that happened to be on screen.

What it costs you: a page redesigned since the visit replays against the
new design, and content rendered only for that visitor is not reproduced.

For most sites that trade is the right one. If you need pixel exact DOM
recording, use a tool built around that and accept its storage and privacy
cost.

## Performance

* The tracker is around 8 KB, has no dependencies and uses passive
  listeners only.
* Events are batched and sent every five seconds, plus once on unload
  through `sendBeacon`.
* Pointer positions are sampled, not streamed.
* Heatmaps read from a pre aggregated grid, so drawing a map is a query
  over a few hundred rows regardless of traffic.

## Requirements

Python 3.10+, Django 4.2+. Any database Django supports. No JavaScript
build step, no Node, no external CDN.

## Development

```bash
git clone https://github.com/qiyascc/django-sightline
cd django-sightline
pip install -e ".[dev]"
python -m pytest
```

## License

MIT
