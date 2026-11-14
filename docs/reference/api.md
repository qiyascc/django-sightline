# Python API reference

This page is generated from the code. Most projects never import anything from Sightline directly; the middleware, the URLs and the settings are the whole interface. The parts below are the ones that are useful in your own code, tests and reports.

## Middleware

`SightlineMiddleware` adds the tracker to recorded pages and the overlay for staff. Add it at the end of `MIDDLEWARE`. Its `_suitable(request, response)` method decides whether a response gets the tracker; overriding it is shown in [Recording only some pages](../examples/some-pages-only.md).

```{eval-rst}
.. autoclass:: sightline.middleware.SightlineMiddleware
   :members: __call__
   :undoc-members:
```

## Settings helpers

```{eval-rst}
.. autofunction:: sightline.conf.get_setting

.. autofunction:: sightline.conf.as_dict
```

`sightline.conf.DEFAULTS` is the dict with the default of every key. The values are listed in the [Settings reference](settings.md).

## Models

The fields of every model are described in the [Data model](data-model.md).

```{eval-rst}
.. autoclass:: sightline.models.Session
   :members: duration_seconds, is_interesting
   :no-undoc-members:

.. autoclass:: sightline.models.Page
   :no-members:

.. autoclass:: sightline.models.PageView
   :no-members:

.. autoclass:: sightline.models.Event
   :no-members:

.. autoclass:: sightline.models.HeatCell
   :no-members:

.. autoclass:: sightline.models.ScrollBand
   :no-members:

.. autoclass:: sightline.models.ElementStat
   :no-members:

.. autoclass:: sightline.models.Panel
   :no-members:

.. autoclass:: sightline.models.Device
   :no-members:
```

## Collector

`ingest()` is what the collect view calls with a parsed batch. It can be useful in tests that need recorded data without a browser:

```python
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory

from sightline.collector import ingest

request = RequestFactory().post("/sightline/collect/", HTTP_USER_AGENT="Mozilla/5.0")
request.user = AnonymousUser()

ingest({
    "url": "/pricing/",
    "title": "Pricing",
    "viewportWidth": 1440,
    "viewportHeight": 900,
    "documentHeight": 2000,
    "maxScrollPct": 60,
    "durationMs": 4000,
    "first": True,
    "events": [
        {"k": "click", "t": 1200, "x": 700, "y": 300, "xp": 0.5, "yp": 0.15, "s": 0,
         "sel": "#buy", "lbl": "Buy now"},
    ],
}, request=request)
```

```{eval-rst}
.. autofunction:: sightline.collector.ingest
```

## Utilities

```{eval-rst}
.. autofunction:: sightline.utils.should_record

.. autofunction:: sightline.utils.visitor_key

.. autofunction:: sightline.utils.device_of

.. autofunction:: sightline.utils.is_bot

.. autofunction:: sightline.utils.clean_path

.. autofunction:: sightline.utils.is_excluded

.. autofunction:: sightline.utils.client_ip

.. autofunction:: sightline.utils.bucket
```

| Function | Returns |
| --- | --- |
| `should_record(request)` | Whether a page served for this request would get the tracker, before the response checks |
| `visitor_key(request, day=None)` | The 40 character visitor key for the request on that day, today by default |
| `device_of(user_agent, width=0)` | `"desktop"`, `"tablet"` or `"mobile"` |
| `is_bot(user_agent)` | Whether the user agent matches the bot pattern |
| `clean_path(url)` | The path as it would be stored, honouring `KEEP_QUERY_STRING` |
| `is_excluded(path)` | Whether the path starts with an entry of `EXCLUDE_PATHS` |
| `client_ip(request)` | First entry of `X-Forwarded-For`, or `REMOTE_ADDR` |
| `bucket(x_pct, y_pct)` | The `(column, row)` grid cell for a position |
