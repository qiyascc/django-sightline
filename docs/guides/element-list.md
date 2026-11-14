# Element list

The heatmap shows where clicks land. The element list says on what. Every click, rage click and dead click with a selector is also counted per element, per page and per day, in the `ElementStat` table.

## Where to find it

### In the admin

The **Element stats** entry in the admin sidebar lists every row with its selector, label, page, day and the three counters. You can search by selector, label or page path and filter by day. It is ordered by clicks, so the most clicked elements come first.

### Through the heat data endpoint

The [heat data endpoint](../reference/endpoints.md) returns the 25 most clicked elements of a page for the chosen range, summed over the days:

```json
"elements": [
  {"selector": "[data-sightline=\"add-yirgacheffe\"]", "label": "Add to cart", "clicks": 20, "rage": 0, "dead": 0},
  {"selector": "#cart-link", "label": "Cart (2)", "clicks": 11, "rage": 0, "dead": 0}
]
```

The live overlay does not draw this list yet. Use the admin or the endpoint.

### With the ORM

```python
from datetime import timedelta

from django.db.models import Sum
from django.utils import timezone

from sightline.models import ElementStat

since = timezone.localdate() - timedelta(days=30)

top = (ElementStat.objects
       .filter(page__path="/pricing/", day__gte=since)
       .values("selector", "label")
       .annotate(clicks=Sum("clicks"), rage=Sum("rage_clicks"), dead=Sum("dead_clicks"))
       .order_by("-clicks")[:20])
```

## Giving elements stable names

The tracker names an element by its `id` first, then by its `data-sightline` attribute, then by its tag, up to two classes and its position among siblings. The first two are stable across redesigns; the last one is not.

For anything you want to follow over time, add an `id` or a `data-sightline` attribute:

```html
<button class="btn btn-primary" data-sightline="add-to-cart">Add to cart</button>
<a href="/pricing/" data-sightline="nav-pricing">Pricing</a>
```

The element then shows up as `[data-sightline="add-to-cart"]` no matter how the classes or the layout change. This is especially useful for repeated elements, like an **Add to cart** button on every product card: give each the same name and their clicks add up into one row, or give each a different name to compare them.

## Labels

The label is the element's visible text, trimmed and cut to 160 characters. It helps you recognise a selector at a glance. Form fields never get a label, and elements inside anything matching `MASK_SELECTORS` do not either. See [Masking](masking.md).

## Things to check

* **Rage clicks per element** point at the exact control that does not respond.
* **Dead clicks per element** list what people think is clickable. A product image with many dead clicks is a strong hint to make it a link.
* **Two buttons for one action**, for example a top and a bottom **Buy** button: the counts tell you whether the second one earns its place.
