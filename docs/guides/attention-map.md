# Attention map

The attention map shows where the pointer spends its time. On a desktop most people move the pointer roughly where they are looking, so a cluster of movement over a paragraph usually means people stopped to read it.

```{image} ../_static/screenshots/heatmap-attention.jpg
:alt: Attention map over a home page, spread across the hero and the plans section
```

## Opening it

Open the heatmap on a page (see [Click heatmap](click-heatmap.md)) and switch the first select on the bar from **Clicks** to **Attention**. The date range and device filters work the same way.

## How it is measured

The tracker records a `move` event whenever the pointer moves, but not more often than once every `MOVE_SAMPLE_MS` milliseconds (120 by default). Each sample is counted into the same grid as clicks, under the event kind `move`. The attention map is the sum of those cells.

Because the samples come at a steady pace while the pointer moves, a place where the pointer moved slowly or often collects more samples than a place it crossed once.

## What it is good for

* **Finding the part of the page people read.** A hot band over a paragraph next to a cold band over another tells you which one holds attention.
* **Spotting hesitation.** Heat around a form field or a price, without matching clicks, often means people stopped to think.
* **Checking that a section is noticed at all.** Combine it with the [scroll map](scroll-map.md): a section most people scroll past with no pointer activity is not doing its job.

## What it is not

* **It is not eye tracking.** Some people park the pointer at the side and read with the keyboard or the scroll wheel.
* **It says nothing about phones.** Touch screens have no pointer between taps, so mobile visits produce taps and scrolling but almost no `move` events. Use the device filter and read the attention map for **Desktop** traffic.

## Tuning the sampling

`MOVE_SAMPLE_MS` trades detail for rows:

```python
SIGHTLINE = {
    "MOVE_SAMPLE_MS": 200,
}
```

A higher value sends fewer events, which means smaller batches, fewer rows in `sightline_event` and a smoother replay cursor path with fewer points. A lower value gives a denser map and a more precise replay. The default of 120 milliseconds is about eight samples a second while the pointer moves.

Pointer samples are usually the largest share of all events. In a test run with 30 desktop and phone visits, `move` was about half of all stored events. If storage matters, this setting and [retention](retention.md) are the two levers that change it most.
