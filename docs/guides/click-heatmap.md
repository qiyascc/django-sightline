# Click heatmap

The click heatmap shows where people click, drawn as heat over the page itself. Red spots got the most clicks, blue ones a few, and the rest of the page stays clear.

```{image} ../_static/screenshots/heatmap-shop.jpg
:alt: Click heatmap of a shop page, with the hottest spots on the Add to cart buttons
```

## Opening it

Any of these opens the page with the heatmap on top:

* **From the panel:** click **Open heatmap** next to a page in the **Pages** table.
* **For any path:** type the path into **Open the heatmap on any page** at the top of the panel and press **Open**. The page does not need to have any data yet; an empty map is a valid answer and lets you check a new page before it has traffic.
* **From the admin list of pages:** the **Pages** admin has an **Open** button in its **Heatmap** column.
* **By URL:** add `?sightline=overlay` to the address of any page while you are signed in as staff.

The heatmap opens in **Clicks** mode. See [The live overlay](live-overlay.md) for every control on the bar.

## What counts as a click

The **Clicks** mode adds up three event kinds: plain clicks, [rage clicks and dead clicks](rage-and-dead-clicks.md). All three are places where somebody pressed the mouse button, so they belong on the same map.

Clicks are counted at the moment they arrive, into a grid laid over the whole document. The grid has `GRID_COLUMNS` columns (60 by default) and `GRID_ROWS` rows (200 by default). A click lands in the cell under its position as a fraction of the page width and height.

## Why fractions and not pixels

Visitors have different screens. A click 300 pixels from the left on a phone and on a 27 inch monitor is not the same element. Storing the position as a fraction of the document lets clicks from different widths land on roughly the same spot of your layout when the map is drawn on your screen.

It works well for layouts that scale with the width. When the layout changes shape completely between widths, for example a three column grid that becomes one column on a phone, clicks from the two layouts do not line up. That is what the device filter is for: pick **Desktop** or **Mobile** on the bar and you see one layout at a time.

The vertical position has a similar catch on short pages. When a page is shorter than the window, the document is as tall as the window, and windows differ in height. A click on the same button is then a slightly different fraction of the document for each visitor, so the spots can sit a little above or below the button, as in the screenshot above. On pages longer than the window this effect disappears.

## Reading the colours

The overlay scales the colours to the busiest cell in the current view. The hottest cell is red whether it got ten clicks or ten thousand. Compare places on one map with each other, not the colour of one map with another.

The numbers behind the map are on the bar: **31 views, 68 clicks** means the page was loaded 31 times in the chosen range and device, and those views registered 68 plain clicks. Rage and dead clicks are drawn on the map but not included in that number.

## Things to look for

* **Clicks on things that are not links.** Pictures, headings and price tags people expect to open something. These show up as [dead clicks](rage-and-dead-clicks.md) too.
* **A primary button nobody clicks** while a secondary link right next to it is hot.
* **Navigation items that get all the clicks**, which often means the page itself did not answer the question.
* **Clicks low on the page** in the click map, compared with the [scroll map](scroll-map.md). If only a few people get that far, the few clicks there may still be a high share of them.

## Changing the grid

`GRID_COLUMNS` and `GRID_ROWS` decide how fine the map is. More cells make sharper spots and more rows in `sightline_heatcell`.

```python
SIGHTLINE = {
    "GRID_COLUMNS": 80,
    "GRID_ROWS": 300,
}
```

```{warning}
Change the grid before you collect data, or start over afterwards. Cells are stored by column and row number, and the overlay places them using the current setting. Cells written with a different grid would be drawn in the wrong places.
```

## The data behind it

The overlay reads the [heat data endpoint](../reference/endpoints.md), which sums `HeatCell` rows for the page, the date range, the device and the event kinds. It returns at most the 6000 busiest cells, along with the scroll bands, the view and click totals and the 25 most clicked elements. You can call it yourself as a staff user to build your own reports.
