# Changelog

## 0.1.1

* The panel works on a phone. Wide tables become stacked cards below 720
  pixels, so the Open heatmap button can no longer be pushed off screen.
* Any page can be opened in the overlay, recorded or not, from a new box
  in the panel or by passing `sl_path`.
* The empty state says why it is empty. Staff being excluded is the usual
  reason and it now says so on the screen.
* Fixed a multi line `{# #}` comment in the dashboard template printing
  itself to the page.

## 0.1.0

First release.

* Click, attention and scroll heatmaps drawn from a pre aggregated grid.
* Rage click and dead click detection.
* Session replay of pointer, scroll, clicks and typing markers.
* Live overlay on the real site, staff only.
* Admin panel with pages, visits and signals.
* Element click list.
* Automatic script injection through middleware.
* Retention pruning and a stats command.
