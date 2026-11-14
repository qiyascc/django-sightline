# Rage and dead clicks

Two kinds of clicks are worth special attention, because they usually mean something on the page is not doing what people expect.

## Rage clicks

A **rage click** is several clicks on the same spot in a short time. People do it when a button does not respond, when a page is slow, or when something looks like it should react and does not.

The tracker keeps the clicks of the last `RAGE_CLICK_WINDOW_MS` milliseconds. When a click arrives and at least `RAGE_CLICK_COUNT` of those clicks, counting the new one, are within `RAGE_CLICK_RADIUS_PX` pixels of it both horizontally and vertically, the new click is recorded as `rage` instead of `click`, and the list starts over.

With the defaults, three clicks within one second inside a 32 pixel box make a rage click:

```python
SIGHTLINE = {
    "RAGE_CLICK_COUNT": 3,
    "RAGE_CLICK_WINDOW_MS": 1000,
    "RAGE_CLICK_RADIUS_PX": 32,
}
```

Raise `RAGE_CLICK_COUNT` if your site has controls that people click quickly on purpose, such as a quantity stepper, and you get false alarms.

## Dead clicks

A **dead click** is a click on something that does nothing. The tracker checks whether the clicked element, or any of its ancestors, is one of:

* a link (`a`), a `button`, an `input`, a `select`, a `textarea`, a `label` or a `summary`,
* an element with `role="button"`,
* an element with an inline `onclick` attribute.

If none of them is found, the click is recorded as `dead`. Typical dead clicks are on product photos, headings, prices, icons and underlined text that is not a link.

```{note}
The check cannot see listeners added from JavaScript with `addEventListener`. A `div` that opens a menu through a listener is reported as a dead click. Give such elements `role="button"`, which is also better for keyboard and screen reader users, or make them real buttons.
```

## Where they show up

* **On the session.** A visit with at least one rage click gets the **rage** signal, one with a dead click gets **dead**. Both appear as tags in the panel's visit lists, and the totals at the top of the panel count visits with each signal.
* **In the visit list filters.** **Rage** and **Dead clicks** show only those visits, so you can go straight to the replays that matter.
* **On the heatmap.** The **Clicks** mode includes rage and dead clicks together with plain clicks.
* **In replay.** Each click is drawn as a ring. Rage clicks get a yellow ring and dead clicks a grey one.
* **Per element.** `ElementStat` counts clicks, rage clicks and dead clicks for every element selector. See [Element list](element-list.md).

## Script errors

The same idea applies to JavaScript errors. The tracker listens for errors that reach `window` and records them as `error` events with the message. A visit with an error gets the **error** signal, the panel counts them, and the visit list has an **Errors** filter.

## A workflow that works

1. Open the panel, set the range to 7 days and look at the totals.
2. Open the visit list and pick **Rage**.
3. Replay the first few visits. Watch what happened right before the rage click.
4. Open the heatmap on the same page and check whether the spot gets dead clicks from other visitors too.
5. Fix the element, then check the same filters a week later.
