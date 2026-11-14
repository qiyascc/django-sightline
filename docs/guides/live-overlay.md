# The live overlay

The overlay draws the heatmap on top of your real site, in your own browser, with a small control bar at the bottom. Since it runs on the live page, what you see is the page as it is today, with its real fonts, images and layout.

```{image} ../_static/screenshots/heatmap-clicks.jpg
:alt: The overlay bar with the mode, range and device selects, the opacity slider, the totals and the Panel and Close buttons
```

## Who can open it

Only active staff. The overlay is triggered by the query parameter `sightline=overlay`. When the middleware sees it on a request from a signed in user with `is_staff` and `is_active`, it injects the overlay **instead of** the tracker, so looking at the heatmap never records a visit. For anybody else the parameter is ignored and the page behaves as usual.

## Ways to open it

| From | How |
| --- | --- |
| The panel, Pages table | **Open heatmap** next to a page |
| The panel, top box | Type any path into **Open the heatmap on any page** and press **Open** |
| The admin **Pages** list | **Open** in the **Heatmap** column |
| Any page | Add `?sightline=overlay` to the address |

When the panel opens the overlay, it passes the page id as `sl_page`, or the typed path as `sl_path`, so the overlay asks for the right data even if the address has extra parts. When you add `?sightline=overlay` by hand, the overlay uses the path of the current page.

## The bar

| Control | What it does |
| --- | --- |
| **Sightline** and the path | Which page the data belongs to |
| Mode select | **Clicks**, **Attention** or **Scroll depth**. See [Click heatmap](click-heatmap.md), [Attention map](attention-map.md), [Scroll map](scroll-map.md) |
| Range select | Today, 7 days, 30 days or 90 days. It starts at 30 days |
| Device select | All devices, Desktop, Tablet or Mobile. It starts at all devices |
| Opacity slider | How strongly the heat covers the page |
| Totals | Page views and plain clicks for the range and device, or *nothing recorded for this page yet* |
| **Panel** | Back to the Sightline panel |
| **Close** | Removes the overlay and the `sightline` parameter from the address, without reloading |

Every change of mode, range or device fetches fresh numbers. Resizing the window redraws the map for the new size.

```{note}
The panel adds `sl_days` and `sl_device` to the overlay link, but in 0.2.0 the overlay always starts at 30 days and all devices. Pick the range and device on the bar.
```

## Checking a page before it has traffic

The overlay works on any page, recorded or not. A page with no data shows *nothing recorded for this page yet*, which is a useful answer in itself: it confirms the page is reachable, rendered for staff and ready to be measured. The panel's **Open the heatmap on any page** box exists for this.

## Pages behind a login

The overlay is drawn over the page as **you** see it. For pages that look different for visitors, for example a landing page that shows a sign up form only to signed out visitors, the clicks of those visitors were made on a layout you do not see while signed in. Keep that in mind when a hot spot seems to float over nothing.

## Pages it cannot open

The overlay is added by the same middleware as the tracker, so the same response rules apply: the page must be an HTML response with status 200, not streamed, with a `</body>` tag, and the view must not have set `sightline_skip`. A JSON endpoint or a redirect cannot carry an overlay.
