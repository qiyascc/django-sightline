# django-cc-sightline

Click heatmaps, scroll maps and session replay for Django, with a panel inside your admin and a live overlay you open on the real site.

There is no third party service, no external script and no account to sign up for. The tracker is a small JavaScript file served from your own static files, the numbers are stored in your own database, and every report is rendered by your own Django.

```{image} _static/screenshots/heatmap-clicks.jpg
:alt: The click heatmap drawn over the home page of a demo coffee shop, with the Sightline bar at the bottom
```

```{note}
On PyPI the package is called **django-cc-sightline**, because the name `django-sightline` there belongs to an unrelated project. Inside Django nothing changes: the app is `sightline`, you add `"sightline"` to `INSTALLED_APPS`, and the tables are named `sightline_*`.
```

## What you get

::::{grid} 1 2 2 3
:gutter: 3

:::{grid-item-card} Click heatmap
:link: guides/click-heatmap
:link-type: doc

Where people click, drawn as heat over the page itself.
:::

:::{grid-item-card} Attention map
:link: guides/attention-map
:link-type: doc

Where the pointer spends its time while people read.
:::

:::{grid-item-card} Scroll map
:link: guides/scroll-map
:link-type: doc

What share of visitors ever reached each part of the page.
:::

:::{grid-item-card} Rage and dead clicks
:link: guides/rage-and-dead-clicks
:link-type: doc

Repeated clicks on one spot, and clicks on things that do nothing.
:::

:::{grid-item-card} Session replay
:link: guides/session-replay
:link-type: doc

Pointer, scrolling, clicks, typing markers and popups played back.
:::

:::{grid-item-card} Admin panel
:link: guides/panel
:link-type: doc

Pages, visits and signals in one screen inside the Django admin.
:::
::::

## How it fits together

1. A middleware adds a small script to every HTML page it is allowed to record.
2. The script batches clicks, pointer movement, scrolling and a few other signals, and posts them to your site every five seconds and once more when the visitor leaves.
3. The server stores the raw events for replay and, at the same moment, counts them into a grid per page, day and device. Heatmaps read that grid, so they stay fast however much traffic you have.
4. Staff open the panel from the admin sidebar, or open any page of the site with `?sightline=overlay` to see the heatmap on top of it.

The [How recording works](guides/how-it-works.md) page walks through each step in detail.

## Where to start

::::{grid} 1 1 2 2
:gutter: 3

:::{grid-item-card} Installation
:link: getting-started/installation
:link-type: doc

Virtual environment, pip, settings, URLs, migrations and a check that it works.
:::

:::{grid-item-card} Quickstart
:link: getting-started/quickstart
:link-type: doc

From an empty project to your first heatmap in about fifteen minutes.
:::

:::{grid-item-card} Settings reference
:link: reference/settings
:link-type: doc

Every key of the `SIGHTLINE` dict with its default and what it changes.
:::

:::{grid-item-card} Recipes
:link: examples/checkout-funnel
:link-type: doc

Checkout funnels, landing pages, partial recording and scheduled pruning.
:::
::::

## Requirements

* Python 3.10 or newer.
* Django 4.2, 5.0, 5.1, 5.2, 6.0 or 6.1. Django 6.0 and 6.1 need Python 3.12 or newer.
* Any database Django supports. SQLite works for small sites and for trying it out.
* No JavaScript build step, no Node, no external CDN.

```{toctree}
:hidden:
:caption: Getting started

getting-started/installation
getting-started/quickstart
getting-started/upgrading
```

```{toctree}
:hidden:
:caption: Guides

guides/how-it-works
guides/click-heatmap
guides/attention-map
guides/scroll-map
guides/rage-and-dead-clicks
guides/popups
guides/session-replay
guides/element-list
guides/live-overlay
guides/panel
guides/user-attribution
guides/custom-events
guides/sampling
guides/excluding-pages
guides/masking
guides/privacy
guides/retention
guides/performance
guides/proxies-and-csp
```

```{toctree}
:hidden:
:caption: Examples

examples/checkout-funnel
examples/landing-page
examples/some-pages-only
examples/staff-testing
examples/scheduled-pruning
```

```{toctree}
:hidden:
:caption: Reference

reference/settings
reference/commands
reference/data-model
reference/endpoints
reference/javascript
reference/api
reference/faq
reference/changelog
```

```{toctree}
:hidden:
:caption: Project

project/development
project/about
```
