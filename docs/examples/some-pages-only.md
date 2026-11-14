# Recipe: recording only some pages

Sightline records every page that is not excluded. Sometimes you want the opposite: record a handful of pages and nothing else, or record only visitors who agreed to it. There are three ways, from the simplest to the most flexible.

## Option 1: exclude everything else by prefix

If the pages you care about share prefixes and the rest of the site does not, `EXCLUDE_PATHS` may be enough:

```python
SIGHTLINE = {
    "EXCLUDE_PATHS": [
        "/admin/", "/static/", "/media/", "/sightline/",
        "/account/", "/api/", "/blog/", "/help/",
    ],
}
```

This works well for a few large sections. It gets awkward when the list of things to skip is longer than the list of things to keep.

## Option 2: opt views out

Mark individual responses with `sightline_skip`:

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

```python
@no_sightline
def order_detail(request, pk):
    ...
```

For class based views, set the attribute in `dispatch`, or wrap the view in `urls.py`:

```python
path("orders/<int:pk>/", no_sightline(OrderDetailView.as_view())),
```

## Option 3: an allow list in a middleware subclass

For "only these pages" or "only these visitors", subclass the middleware and override `_suitable`, the method that decides whether a response gets the tracker. Call the parent at the end, so the normal rules (staff, Do Not Track, bots, `EXCLUDE_PATHS`) still apply.

`mysite/sightline_middleware.py`:

```python
from sightline.middleware import SightlineMiddleware

RECORDED = ("/pricing/", "/shop/", "/landing/")


class SelectiveSightlineMiddleware(SightlineMiddleware):
    def _suitable(self, request, response):
        path = request.path
        if path != "/" and not path.startswith(RECORDED):
            return False
        return super()._suitable(request, response)
```

Use it instead of the original, at the end of `MIDDLEWARE`:

```python
MIDDLEWARE = [
    ...
    "mysite.sightline_middleware.SelectiveSightlineMiddleware",
]
```

This records the home page and everything under `/pricing/`, `/shop/` and `/landing/`, and nothing else. The overlay for staff is not affected, because it does not go through `_suitable`.

### Recording only after consent

The same hook can check a consent cookie set by your banner:

```python
from sightline.middleware import SightlineMiddleware


class ConsentSightlineMiddleware(SightlineMiddleware):
    def _suitable(self, request, response):
        if request.COOKIES.get("analytics_consent") != "yes":
            return False
        return super()._suitable(request, response)
```

The first page a visitor sees, before they answer the banner, is not recorded. Every page after they agree is.

```{warning}
`_suitable` starts with an underscore: it is an internal method, not a documented API, and it may change in a future minor release. Pin the version (`django-cc-sightline>=0.2,<0.3`) and add a test like the one below, so an upgrade that breaks it fails loudly.
```

```python
from django.test import TestCase


class SightlineSelectionTests(TestCase):
    def test_pricing_is_recorded(self):
        response = self.client.get("/pricing/", HTTP_USER_AGENT="Mozilla/5.0")
        self.assertContains(response, "sightline/js/tracker.js")

    def test_blog_is_not(self):
        response = self.client.get("/blog/", HTTP_USER_AGENT="Mozilla/5.0")
        self.assertNotContains(response, "sightline/js/tracker.js")
```

## Which one to pick

| Situation | Use |
| --- | --- |
| A few sections to skip | `EXCLUDE_PATHS` |
| A few single views to skip | `sightline_skip` |
| A short list of pages to record | Middleware subclass |
| Recording depends on the visitor, such as consent | Middleware subclass |
