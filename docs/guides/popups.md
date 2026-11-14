# Popups and dialogs

A popup is a page in the only way that matters: while it is open, the visitor is looking at it. It has no URL, so nothing else in the recorder would notice it, and a replay without it would show somebody clicking on a page that was covered at the time. Sightline watches for popups, records when they open and close, and opens them again during replay.

```{image} ../_static/screenshots/replay-popup.jpg
:alt: Session replay with the sign in dialog open over the page and a note saying Popup open: Sign in
```

## What counts as a popup

Anything that matches one of the CSS selectors in `OVERLAY_SELECTORS`. The default list covers the common patterns:

```python
SIGHTLINE = {
    "OVERLAY_SELECTORS": [
        "dialog",
        "[role=dialog]",
        "[aria-modal=true]",
        "[data-overlay]",
        ".modal",
        ".popup",
    ],
}
```

If your site uses other class names, for example a cookie banner or a cart drawer, add them. Setting the key replaces the whole list, so copy the defaults you want to keep:

```python
SIGHTLINE = {
    "OVERLAY_SELECTORS": [
        "dialog",
        "[role=dialog]",
        "[aria-modal=true]",
        "[data-overlay]",
        ".modal",
        ".popup",
        ".cart-drawer",
        "#cookie-banner",
    ],
}
```

The simplest way to make your own component visible to Sightline is to give it a `data-overlay` attribute.

An empty list switches popup recording off.

## How opening and closing is detected

The tracker checks the matching elements every `OVERLAY_POLL_MS` milliseconds (400 by default) and compares each one's visibility with the previous check. An element counts as visible when:

* it is a `<dialog>` with the `open` attribute, or
* it is not `hidden`, takes up space on the page, is not `display: none` or `visibility: hidden`, and its opacity is above 0.05.

A timer is used instead of watching DOM mutations on purpose. A popup can be opened by a native `showModal()` call, an attribute, a class or an inline style, and one cheap loop catches all four.

When an element changes state, an `overlay` event is recorded with:

* its selector,
* a name: its `aria-label`, `data-title` or `title` attribute, otherwise its visible text, otherwise its id or class, cut to 60 characters,
* `{"state": "open"}` or `{"state": "close"}`.

An opening is sent to the server right away. A popup that is removed from the page while open is recorded as closed.

Popups that are closed when the page loads are not announced, because closed is the normal state. One that is already open when the page loads is recorded as opened.

## During replay

When the player reaches an `open` event, it looks for the same selector in its copy of the page and forces it visible: it removes `hidden`, adds `data-open`, and overrides `display`, `visibility`, `opacity` and `transform` only where they are hiding it, on the element and its ancestors. For a `<dialog>` it calls `showModal()`. A note in the corner of the stage says **Popup open:** followed by the popup's name.

On `close`, or when you seek backwards, everything it changed is put back exactly as it was.

### When the popup is not in the copy

The replayed page is fetched fresh, as the staff member watching. Markup that your templates only render for signed out visitors, a login prompt for example, is not in that copy. In that case the player does not pretend: it shows a note saying a popup opened, with its name, and that it is not in this copy of the page because it is only rendered for signed out visitors.

## Keeping popups out of the heatmap

`overlay` events are never counted into the heatmap grid. They are visible in replay, in the admin **Events** list and through the ORM:

```python
from sightline.models import Event

opened = (Event.objects
          .filter(kind="overlay", meta__state="open")
          .values("label")
          .order_by())
```

To see how many visits opened a newsletter popup, count distinct sessions:

```python
Event.objects.filter(
    kind="overlay", label="Newsletter", meta__state="open",
).values("pageview__session").distinct().count()
```
