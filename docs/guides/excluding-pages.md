# Excluding pages and visitors

By default Sightline records every HTML page except the admin, static and media files and its own panel, and every visitor except staff, Do Not Track browsers and bots. This page lists all the switches that narrow that down.

## Excluding paths

`EXCLUDE_PATHS` is a list of path prefixes. Any request whose path starts with one of them gets no tracker, and batches for those paths are refused by the collect view as well.

```python
SIGHTLINE = {
    "EXCLUDE_PATHS": [
        "/admin/",
        "/static/",
        "/media/",
        "/sightline/",
        "/account/",
        "/api/",
        "/checkout/payment/",
    ],
}
```

* The match is a plain `startswith` on the path. `/account/` excludes `/account/settings/` and `/account/orders/42/`, but not `/accounts/`.
* Setting the key replaces the default list. Keep the first four entries, or their equivalents if your admin, static, media or Sightline URLs live elsewhere.
* If you mounted Sightline under another prefix, put that prefix here. Otherwise the recorder records its own panel.
* With `i18n_patterns`, paths start with the language code. Add each version you want to exclude, for example `/en/account/` and `/de/account/`.

## Excluding one view

A view can opt out by setting an attribute on its response:

```python
from django.shortcuts import render

def invoice(request, number):
    response = render(request, "invoice.html", {"number": number})
    response.sightline_skip = True
    return response
```

The middleware checks for `sightline_skip` before anything else, so the page gets neither the tracker nor the overlay. This is the cleanest way to keep a page out when it shares a URL prefix with pages you do want.

For several views, a small decorator keeps it tidy:

```python
from functools import wraps

def no_sightline(view):
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        response = view(request, *args, **kwargs)
        response.sightline_skip = True
        return response
    return wrapper
```

For the opposite, recording only a few pages, see [Recording only some pages](../examples/some-pages-only.md).

## Query strings

By default the query string is dropped, so `/products/?sort=price` and `/products/?page=2` are both recorded as `/products/`. That keeps one heatmap per page instead of one per filter combination, and it keeps tokens and tracking parameters out of the database.

To keep query strings:

```python
SIGHTLINE = {"KEEP_QUERY_STRING": True}
```

Use it only when the query string really selects a different page, for example `?id=` on an old style site, and be aware that every distinct combination becomes its own page row.

## Staff

```python
SIGHTLINE = {"IGNORE_STAFF": True}
```

With the default `True`, requests from users with `is_staff` get no tracker. Your own team clicking around is not what you want to measure. Turn it off while testing; see [Testing with staff accounts](../examples/staff-testing.md).

## Do Not Track

```python
SIGHTLINE = {"RESPECT_DNT": True}
```

With the default `True`, a request with the header `DNT: 1` gets no tracker. Not every browser sends the header, but those that do are asking not to be tracked, and Sightline listens.

## Bots

Requests whose user agent matches the bot pattern are never recorded. There is no setting for it. The pattern matches `bot`, `crawl`, `spider`, `slurp`, `bingpreview`, `facebookexternalhit`, `headlesschrome`, `lighthouse`, `pingdom`, `uptime`, `monitor`, `curl`, `wget` and `python-requests`, in any case.

If you run browser tests against a staging site with headless Chrome, they are skipped for this reason. Give the test browser a normal user agent if you want them recorded.

## Switching injection off

```python
SIGHTLINE = {"AUTO_INJECT": False}
```

With `AUTO_INJECT` off, the middleware never adds the tracker. The overlay for staff keeps working, so you can still look at the data you have. This is useful to pause recording, for example during a migration, without removing the app.

```{note}
In 0.2.0 there is no template tag to add the tracker by hand. With `AUTO_INJECT` off nothing is recorded.
```

## Where each rule is checked

| Rule | Middleware (page served) | Collect view (batch received) |
| --- | --- | --- |
| `EXCLUDE_PATHS` | yes | yes |
| `sightline_skip` | yes | no |
| `IGNORE_STAFF` | yes | no |
| `RESPECT_DNT` | yes | no |
| Bot pattern | yes | no |
| `AUTO_INJECT` | yes | no |
| `SAMPLE_RATE` | no, decided in the browser | no |

The decision to record is made when the page is served. A page without the tracker sends nothing, so the collect view only needs to check paths.
