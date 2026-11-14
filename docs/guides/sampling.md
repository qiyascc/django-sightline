# Sampling

On a busy site you do not need every visit to draw a good heatmap. `SAMPLE_RATE` records a share of visitors and leaves the rest alone, which cuts the number of requests to the collect URL and the number of rows in the database by the same share.

```python
SIGHTLINE = {
    "SAMPLE_RATE": 0.25,
}
```

The value is a number between 0 and 1. The default, `1.0`, records everybody. `0.25` records about one visitor in four, `0.1` one in ten.

## How the decision is made

Sampling happens in the browser, once per tab:

1. On the first page of a visit, the tracker draws a random number and compares it with `SAMPLE_RATE`.
2. It stores the result in `sessionStorage` under the key `sightline.sampled`, as `"1"` or `"0"`.
3. On every following page in that tab it reads the stored result instead of drawing again.

So a visitor is recorded for the **whole visit or not at all**. Sampling per page would give half a visit, which is worse than none: a replay with holes and a funnel that loses people for no reason.

`sessionStorage` belongs to one tab. A visitor who opens a new tab gets a new draw. When the browser blocks storage entirely, the tracker records the visitor.

## What still happens for unsampled visitors

The tracker script is still added to the page and downloaded, and it exits right after the draw. Nothing is sent to your server. If you want visitors to skip even the download, use the server side rules in [Excluding pages and visitors](excluding-pages.md) instead.

## Effect on the reports

* **Heatmaps** keep their shape. The colours are scaled to the busiest cell, so a sampled map looks the same as a full one with enough traffic.
* **Counts are a share of reality.** The panel's views, clicks and visit numbers count recorded visits only. With `SAMPLE_RATE` at 0.25, multiply by four for a rough total, or better, take totals from your regular analytics.
* **Replays** exist only for recorded visits.

## Choosing a value

| Daily visitors | A reasonable start |
| --- | --- |
| Up to a few thousand | `1.0` |
| Tens of thousands | `0.2` to `0.5` |
| Hundreds of thousands | `0.05` to `0.1` |

These are starting points, not rules. Lower the rate if the event table grows faster than you like, raise it if a page you care about has too few visits for a clear map. The [Performance](performance.md) page has more on sizing.

## Changing the rate later

The rate is read every time a page is served, so a new value applies right away to new visits. Visitors in the middle of a visit keep the decision stored in their tab.
