# Recipe: a checkout funnel

This recipe marks the steps of a shop's checkout with custom events, counts how many visits reach each step, and lists the visits that gave up so you can watch them.

## 1. Name the steps

Pick a short, stable name for each step:

| Step | Event name | Where |
| --- | --- | --- |
| Cart opened | `cart-viewed` | Cart page |
| Checkout started | `checkout-started` | First checkout page |
| Payment submitted | `payment-submitted` | Click on the pay button |
| Order confirmed | `order-confirmed` | Confirmation page |

## 2. Mark them in the templates

Page level steps go in the template of each page. The tracker loads with `defer`, so wait for `load`:

```html
<script>
  window.addEventListener("load", function () {
    if (window.sightline) {
      window.sightline.mark("cart-viewed", { items: {{ cart.count }} });
    }
  });
</script>
```

Do the same with `checkout-started` on the first checkout page and `order-confirmed` on the confirmation page.

The payment step is a click. Mark it and flush, because the browser leaves the page right after:

```html
<button id="pay" class="btn" type="submit">Pay {{ order.total }} AZN</button>
<script>
  document.getElementById("pay").addEventListener("click", function () {
    if (window.sightline) {
      window.sightline.mark("payment-submitted", { total: {{ order.total }} });
      window.sightline.flush();
    }
  });
</script>
```

Give the important buttons a `data-sightline` name too, so the [element list](../guides/element-list.md) can follow them across redesigns:

```html
<button id="pay" data-sightline="checkout-pay">...</button>
```

## 3. Count the funnel

Put this in your app, for example `shop/funnel.py`:

```python
from datetime import timedelta

from django.utils import timezone

from sightline.models import Session

STEPS = ["cart-viewed", "checkout-started", "payment-submitted", "order-confirmed"]


def reached(step, since):
    return (Session.objects
            .filter(started_at__gte=since,
                    pageviews__events__kind="custom",
                    pageviews__events__label=step)
            .distinct())


def funnel(days=30):
    since = timezone.now() - timedelta(days=days)
    rows = []
    first = None
    for step in STEPS:
        count = reached(step, since).count()
        first = first or count
        rows.append((step, count, round(count * 100 / first) if first else 0))
    return rows


def abandoned(after_step, before_step, days=30):
    since = timezone.now() - timedelta(days=days)
    done = reached(before_step, since).values("pk")
    return reached(after_step, since).exclude(pk__in=done).order_by("-started_at")
```

`funnel()` counts the visits that reached each step, and the share relative to the first step. `abandoned()` returns the visits that reached one step and not the next.

## 4. A management command to print it

`shop/management/commands/funnel.py`:

```python
from django.core.management.base import BaseCommand

from shop.funnel import abandoned, funnel


class Command(BaseCommand):
    help = "Print the checkout funnel and the latest abandoned checkouts."

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=30)

    def handle(self, *args, **options):
        days = options["days"]
        for step, count, share in funnel(days):
            self.stdout.write(f"{step:<20} {count:>6}  {share:>3}%")

        self.stdout.write("")
        self.stdout.write("Started checkout, never paid:")
        for visit in abandoned("checkout-started", "payment-submitted", days)[:10]:
            who = visit.user or "guest"
            self.stdout.write(f"  {visit.started_at:%Y-%m-%d %H:%M}  {who}  /sightline/panel/replay/{visit.pk}/")
```

```console
$ python manage.py funnel --days 7
cart-viewed             412  100%
checkout-started        233   57%
payment-submitted       141   34%
order-confirmed         137   33%

Started checkout, never paid:
  2026-11-13 21:40  guest  /sightline/panel/replay/6f1c.../
  2026-11-13 19:02  leyla  /sightline/panel/replay/91aa.../
```

The numbers above are an example of the output format.

## 5. Watch the drop

Open the replay links. Things to look for between **checkout started** and **payment submitted**:

* rage clicks on the pay button, which point at a slow or failing payment form,
* dead clicks on text that looks like a link, such as "change address",
* a popup opening right before the visit ends, for example a sign in prompt,
* a long pause on one field, such as the phone number format.

Then open the heatmap on the checkout page with the device set to **Mobile**. Checkout problems are often phone problems.

## Notes

* The counts include only recorded visits. With [sampling](../guides/sampling.md) below 1, they are a share of the real numbers; the percentages between steps stay meaningful.
* Custom events are raw events and are [pruned](../guides/retention.md) after `RETAIN_DAYS`. Run the funnel over ranges shorter than that, or copy the daily numbers to your own table.
* Staff are not recorded by default, so test orders placed by your team do not distort the funnel.
