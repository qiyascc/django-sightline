# Changelog

## 0.1.2

* Replay works behind `X-Frame-Options: DENY`, which Django sends by
  default. The page is fetched and written into the frame instead of
  being loaded by URL, and its scripts are stripped.
* Replay is sized to the viewport the visit was recorded at, so a phone
  visit no longer plays back over a desktop layout.
* The tracker refuses to run outside the top window. A page that embeds
  part of itself was recording the frame as a separate visit under paths
  like `srcdoc`, which crowded out the real pages.
* Seeking backwards in the player now restores the scroll position.

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
