# Scroll map

The scroll map answers one question: what share of visitors ever saw this part of the page? The page is split into twenty horizontal bands of five percent each, and every band is labelled with a percentage.

```{image} ../_static/screenshots/heatmap-scroll.jpg
:alt: Scroll map of a long page; the top bands read 100 percent and the bottom ones fall to about 45 percent
```

## Opening it

Open the heatmap on a page and switch the first select on the bar to **Scroll depth**. The date range and device filters apply.

## How it is measured

While the visitor scrolls, the tracker computes how far down the document the bottom edge of the window is, as a percentage, and keeps the deepest value it has seen on this page view. Each batch sends that value as `maxScrollPct`.

On the server, the deepest value is turned into a band number (the percentage divided by five) and every band from the top down to that one is credited once in `ScrollBand`, for the page, the day and the device. Somebody who got to 80 percent also saw 40 percent, so both are counted.

Each page view credits each band at most once. The page view row remembers the deepest band it already credited, so a visit that sends ten batches does not count ten times, and scrolling further later on only credits the new bands.

## Reading the percentages

The overlay shows each band as a share of the most reached band, which is the top of the page in practice. A label of **52%** on a band means about half as many page views reached it as reached the top.

The colour gets stronger with the percentage, so the place where most people stop shows up as the point where the blue fades.

## A detail worth knowing

Depth is measured from `scroll` events. A visitor who never scrolls sends no scroll event, so that page view has a depth of 0 and credits no band, even when the whole page fits in their window. On short pages, such as a checkout form, the average scroll in the panel can look low for that reason. It is the long pages, where scrolling is needed to see the content, that the scroll map is made for.

## What to do with it

* **Move the important part above the drop.** If the bands fall from 100 to 50 percent before your call to action, half of the visitors never see it.
* **Check a long article.** A steady slope is normal. A cliff in the middle often marks a wall of text, a large image that looks like the end of the page, or an ad.
* **Compare devices.** Phones usually scroll further but read less. Switch the device filter and compare.
* **Combine it with the click map.** A few clicks at the bottom of the page can be a high share of the few people who got there.

## In the panel

The **Avg scroll** column of the **Pages** table in the panel is the average deepest scroll per page view, for the date range and device you picked. It is the quickest way to find pages where people leave early.
