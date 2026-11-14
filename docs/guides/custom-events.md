# Custom events

Clicks and scrolling tell you what people did with the page. Custom events let your own code mark the moments that matter to your business: a checkout started, a plan picked, a video played, a search with no results.

## Marking an event

When the tracker runs, it exposes a small object on `window`:

```javascript
sightline.mark("checkout-started");
sightline.mark("plan-picked", { plan: "pro", yearly: true });
```

`mark(name, meta)` adds a `custom` event to the queue with:

* `name` as its label, converted to a string and cut to 160 characters,
* `meta` as a JSON object stored in the event's `meta` field. It is optional.

Keep names short, lower case and stable, like `checkout-started`. They are what you will search and filter on later.

## Guard the call

The tracker is not on every page: staff, Do Not Track visitors, bots, unsampled visitors and excluded paths do not get it. Calling `sightline.mark()` there would throw. Always check first:

```javascript
if (window.sightline) {
  window.sightline.mark("checkout-started", { items: 3 });
}
```

or with optional chaining:

```javascript
window.sightline?.mark("checkout-started", { items: 3 });
```

## When it is sent

A marked event waits in the queue like any other event. It goes out with the next batch, at most five seconds later, or when the page is hidden or closed.

If you mark something right before a full page navigation, the unload batch normally carries it. When you want to be sure it leaves now, call `flush()`:

```javascript
document.querySelector("#pay").addEventListener("click", function () {
  if (window.sightline) {
    window.sightline.mark("payment-submitted", { total: 31 });
    window.sightline.flush();
  }
});
```

`flush()` sends whatever is queued immediately with `fetch`.

## Marking from a template

Server side decisions can be marked too. Render the call into the page with a small inline script:

```html
{% if order %}
<script>
  window.addEventListener("load", function () {
    if (window.sightline) {
      window.sightline.mark("order-confirmed", { total: {{ order.total }} });
    }
  });
</script>
{% endif %}
```

The tracker script is loaded with `defer`, so wait for `load` (or `DOMContentLoaded`) before calling it from an inline script.

```{warning}
Do not put personal data in `meta`. Email addresses, names and phone numbers do not belong there. Use ids or categories.
```

## Reading them

Custom events are stored as rows of `sightline.models.Event` with `kind="custom"`. They do not appear on the heatmap. You will find them:

* in the admin **Events** list, filtered by kind *Custom*, with the name in the **Label** column,
* in the replay data of the visit,
* through the ORM, which is where they are most useful.

### How many visits started a checkout

```python
from sightline.models import Event

started = (Event.objects
           .filter(kind="custom", label="checkout-started")
           .values("pageview__session")
           .distinct()
           .count())
```

### Which plan is picked most

```python
from django.db.models import Count

(Event.objects
 .filter(kind="custom", label="plan-picked")
 .values("meta__plan")
 .annotate(n=Count("id"))
 .order_by("-n"))
```

### Visits that started a checkout but never paid

```python
from sightline.models import Session

started = Session.objects.filter(
    pageviews__events__kind="custom",
    pageviews__events__label="checkout-started",
)
paid = Session.objects.filter(
    pageviews__events__kind="custom",
    pageviews__events__label="payment-submitted",
)
abandoned = started.exclude(pk__in=paid.values("pk")).distinct()
```

Open those visits in the replay to see where people gave up. The [checkout funnel recipe](../examples/checkout-funnel.md) builds this into a small report.

```{note}
Custom events are raw events, so the prune command removes them after `RETAIN_DAYS` like everything else. If you need the numbers for longer, copy them into your own table on a schedule.
```
