# Recipe: a marketing landing page

A landing page has one job: get people to the call to action. This recipe sets up Sightline to show whether people see it, whether they click it, and what they click instead.

## 1. Name the elements that matter

Give each call to action and each section a stable name. The tracker prefers `id`, then `data-sightline`:

```html
<a href="/signup/" class="btn" data-sightline="cta-hero">Start free trial</a>
...
<section id="features">...</section>
<section id="pricing">
  <a href="/signup/?plan=pro" data-sightline="cta-pricing-pro">Choose Pro</a>
</section>
...
<a href="/signup/" class="btn" data-sightline="cta-footer">Start free trial</a>
```

Now the [element list](../guides/element-list.md) shows `[data-sightline="cta-hero"]`, `[data-sightline="cta-pricing-pro"]` and `[data-sightline="cta-footer"]` as separate rows, and the counts survive any redesign that keeps the attributes.

## 2. Record the signup popup

If the call to action opens a form in a modal, make sure Sightline sees it. A `<dialog>` element and anything with `role="dialog"` are covered by default. For a custom component, add `data-overlay`:

```html
<div class="signup-modal" data-overlay aria-label="Signup form" hidden>...</div>
```

The replay then shows the modal open while the visitor fills it in, and you can count openings:

```python
from sightline.models import Event

Event.objects.filter(kind="overlay", label="Signup form", meta__state="open").count()
```

## 3. Mark the result

On the page people land on after signing up:

```html
<script>
  window.addEventListener("load", function () {
    if (window.sightline) { window.sightline.mark("signup-done"); }
  });
</script>
```

## 4. Read the page

Open the heatmap on the landing page and go through the three modes:

1. **Scroll depth.** Find the band where the percentage drops below 50. Everything below that line is seen by fewer than half of the visitors. If your pricing section or your second call to action is there, it is working for a minority.
2. **Clicks.** Is the hero button the hottest spot? If the navigation, a logo or an image gets more clicks, people are looking for something the page does not give them. Dead clicks on feature screenshots usually mean people want to see them bigger.
3. **Attention**, with the device set to **Desktop**. Which sections hold the pointer? A section with no movement at all is a candidate for removal.

## 5. Compare two versions

Query strings are dropped by default, so `/landing/?v=b` is recorded as `/landing/`. For a simple A/B comparison, serve the variants on separate paths:

```python
urlpatterns = [
    path("landing/a/", views.landing, {"variant": "a"}),
    path("landing/b/", views.landing, {"variant": "b"}),
]
```

Each path gets its own heatmap, scroll map and element list. Compare the scroll band where each version drops below 50 percent and the share of views that clicked the hero button:

```python
from datetime import timedelta

from django.db.models import Sum
from django.utils import timezone

from sightline.models import ElementStat, PageView

since = timezone.localdate() - timedelta(days=14)

for path in ["/landing/a/", "/landing/b/"]:
    views = PageView.objects.filter(page__path=path, started_at__date__gte=since).count()
    clicks = (ElementStat.objects
              .filter(page__path=path, day__gte=since, selector='[data-sightline="cta-hero"]')
              .aggregate(n=Sum("clicks"))["n"] or 0)
    print(path, views, clicks, f"{clicks * 100 / views:.1f}%" if views else "-")
```

If the variant has to stay in the query string, set `KEEP_QUERY_STRING` to `True` instead. Every distinct query string then becomes its own page, so this is best on a site where query strings are rare.

## 6. Campaign traffic

The referrer of each visit is stored, and the visit list searches it. Typing part of a referrer, such as a newsletter domain, into the search box lists the visits that came from there, ready to replay.
