# django-cc-sightline

[![PyPI](https://img.shields.io/pypi/v/django-cc-sightline?color=3775A9&logo=pypi&logoColor=white)](https://pypi.org/project/django-cc-sightline/)
[![Downloads](https://img.shields.io/pypi/dm/django-cc-sightline?color=3775A9)](https://pypistats.org/packages/django-cc-sightline)
[![Python](https://img.shields.io/pypi/pyversions/django-cc-sightline?logo=python&logoColor=white)](https://pypi.org/project/django-cc-sightline/)
[![Django](https://img.shields.io/pypi/frameworkversions/django/django-cc-sightline?color=0C4B33&logo=django&logoColor=white&label=django)](https://pypi.org/project/django-cc-sightline/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Docs](https://readthedocs.org/projects/django-cc-sightline/badge/?version=latest)](https://django-cc-sightline.readthedocs.io/en/latest/)

Click heatmaps, scroll maps and session replay for Django, with an admin
panel and a live overlay you open on the real site.

No third party service, no external script, no account. Everything is
stored in your own database and rendered by your own server.

Works with Django 4.2, 5.0, 5.1, 5.2, 6.0 and 6.1, Python 3.10 and up.

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
* **Popups.** Dialogs and panels are recorded when they open and reopened
  during replay, so a visit spent inside a modal is not replayed as a
  visit spent staring at the page behind it.
* **Live overlay.** Open any page of your site with the heatmap drawn on
  top of it. Staff only.
* **Admin panel.** Pages, visits and signals in one screen inside your
  existing Django admin.

## Install

```bash
pip install django-cc-sightline
```

The package lives on PyPI: [pypi.org/project/django-cc-sightline](https://pypi.org/project/django-cc-sightline/). The wheel and the source archive are also attached to every [GitHub release](https://github.com/qiyascc/django-sightline/releases). The name `django-sightline` on PyPI belongs to an unrelated project, so this one is published as `django-cc-sightline`. Inside Django it is still the `sightline` app. The full documentation, with step by step guides, recipes and a settings reference, is at [django-cc-sightline.readthedocs.io](https://django-cc-sightline.readthedocs.io/). More about the project on [theqiyas.cc](https://theqiyas.cc/projects/django-sightline/).

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
* **Recent visits** lists the latest sessions. "Replay" plays one back.
  "See all" opens the full list: every visit ever recorded, paged and
  filterable by person, device or signal.

Visits are attributed to an account whenever somebody was signed in at
any point during them, including a guest who signs in halfway through.
Everyone else is listed as a guest with their salted visitor key.

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
    "CAPTURE_INPUTS": False,        # keep what people type into fields
    "CAPTURE_PASSWORDS": False,     # also keep password fields (not advised)
    "PRUNE_SESSIONS": False,        # the prune drops events, not visits
    "ROLLUP_RETAIN_DAYS": 365,      # heatmap rollups pruned after this, 0 keeps them
    "PERMISSION": "sightline.view_session",  # needed to see the panel, None for any staff
    "IP_SOURCE": "remote_addr",     # or "x-real-ip" / "xff-last" behind a proxy
    "THROTTLE_CACHE": "default",    # cache alias for the collect throttle
    "THROTTLE_BATCHES": 600,        # batches per address per window, 0 is off
    "THROTTLE_BATCHES_SECONDS": 600,
    "THROTTLE_SESSIONS": 60,        # new visits per address per window, 0 is off
    "THROTTLE_SESSIONS_SECONDS": 3600,
    "MAX_EVENTS_PER_SESSION": 5000, # 0 is unlimited
    "MAX_META_BYTES": 1024,         # bigger event meta is dropped
    "RESOLVE_PATHS": True,          # only record paths your URLconf serves
}
```

Keep the mount prefix in `EXCLUDE_PATHS` so the recorder does not record
itself.

## Access and security

**Who can watch.** The panel, the visit list, the replays, the heat data
and the live overlay need an active staff account **and** the permission
named by `PERMISSION`, `sightline.view_session` by default. Superusers
always have it. Grant it to the people who may watch recordings, for
example through a group:

```python
from django.contrib.auth.models import Group, Permission

group, _ = Group.objects.get_or_create(name="Sightline viewers")
group.permissions.add(Permission.objects.get(
    codename="view_session", content_type__app_label="sightline"))
```

Staff without it get a 403. Set `"PERMISSION": None` to let every active
staff user in, as before 0.3.0.

**Client address.** The address is used for the visitor key and for the
throttle. By default only `REMOTE_ADDR` is trusted. Behind a reverse proxy
every visitor would then share the proxy's address, so tell Sightline
which header your proxy sets:

* `"IP_SOURCE": "x-real-ip"` when the proxy sets `X-Real-IP`
  (nginx: `proxy_set_header X-Real-IP $remote_addr;`).
* `"IP_SOURCE": "xff-last"` when it appends to `X-Forwarded-For`; the
  last hop is the one your proxy wrote. The first entry is never used,
  because the client writes it.

**The collect endpoint is public**, so it is guarded:

* Per address, at most `THROTTLE_BATCHES` batches per
  `THROTTLE_BATCHES_SECONDS` and `THROTTLE_SESSIONS` new visits per
  `THROTTLE_SESSIONS_SECONDS`. Past that it answers 429. Counters live in
  the Django cache named by `THROTTLE_CACHE`; use a shared cache (Redis,
  Memcached, database) when you run several processes. If the cache fails,
  the request is let through.
* A visit stops taking events at `MAX_EVENTS_PER_SESSION`.
* Event `meta` larger than `MAX_META_BYTES` of JSON is dropped.
* Paths must be plain site paths (one leading slash, no backslash, no
  markup); anything else is refused with 400. With `RESOLVE_PATHS`, a
  path your URLconf does not serve is ignored, so made up URLs do not
  fill the page list. Turn it off if pages are served outside the
  URLconf, such as flatpages from a fallback middleware.
* A page title is stored when the page is first seen and never
  overwritten by a later batch.

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
and survive the event prune, so old maps still draw after their raw events
are gone.

Heatmap rollups (cells, scroll bands, element counts) older than
`ROLLUP_RETAIN_DAYS`, 365 by default, are deleted as well, together with
pages that have no visit and no rollup left. Set it to `0`, or pass
`--rollup-days 0`, to keep them forever.

The visits themselves are **not** deleted. Events are the bulk; a visit
row is a few hundred bytes and it is what the panel lists, so removing it
turns months of history into an empty screen. Set
`SIGHTLINE = {"PRUNE_SESSIONS": True}`, or pass `--sessions`, only if the
session table itself has become a storage problem.

## Privacy

The package is built so that a heatmap does not become a surveillance log.

* **No addresses are stored.** Visitors are identified by a salted hash
  that includes the date, so the same person looks like a new visitor
  tomorrow.
* **No typed text by default.** Typing is stored as "somebody typed in this
  field", never as what was typed. Turn on `CAPTURE_INPUTS` to keep the
  values for support (passwords stay hidden unless `CAPTURE_PASSWORDS`).
* **No screen contents are recorded.** Replay is a pointer over your
  current page, not a recording of what the visitor saw.
* **Do Not Track is honoured** by default.
* **Staff are excluded** by default.

Add `MASK_SELECTORS` for regions whose element text should not be stored
either, for example a container showing a customer name.

## How replay works, exactly

Sightline records
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

Python 3.10+, Django 4.2 to 6.1. Any database Django supports. No JavaScript
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
