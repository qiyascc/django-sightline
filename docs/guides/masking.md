# Masking

Sightline stores a short text label for clicked elements, so that a selector like `button.btn:nth-of-type(2)` comes with *Add to cart* next to it. On most pages that text is harmless. On some it is not: a greeting with the customer's name, an address on an order page, the text of a message.

`MASK_SELECTORS` names the parts of the page whose text must never be stored.

```python
SIGHTLINE = {
    "MASK_SELECTORS": [
        ".customer-name",
        "#shipping-address",
        "[data-private]",
    ],
}
```

## What masking does

When a clicked element is inside anything that matches one of the selectors, its label is stored as an empty string. The check uses `closest()`, so a click on a `span` inside a masked `div` is masked too.

The simplest way to mark private areas is an attribute you control, then mask that attribute once:

```html
<div class="account-box" data-private>
  Signed in as <b>Leyla Mammadova</b>
</div>
```

```python
SIGHTLINE = {"MASK_SELECTORS": ["[data-private]"]}
```

## What masking does not do

* **The click is still recorded.** Its position, its selector and its time are stored, so the heatmap and the replay still show it. Only the text is dropped.
* **Selectors are not masked.** If an element's `id` or `data-sightline` attribute contains personal data, it is stored as the selector. Do not put personal data in ids.
* **Popup names from attributes are not masked.** A popup's name comes from its `aria-label`, `data-title` or `title` attribute before its text. Those attributes are used as they are.
* **It does not affect replay.** Replay shows the page as it is when you watch it, fetched for your account. Masking has nothing to remove there, because the page content was never recorded.

## What is never stored, masked or not

* The value of form fields, unless `CAPTURE_INPUTS` is on. By default `input`, `textarea` and `select` elements never get a label, and typing is recorded as "somebody typed in this field" with the field's selector only. With `CAPTURE_INPUTS` on, fields inside `MASK_SELECTORS` still record no value.
* The page content.

## Masking text that is clicked a lot

A common case is a list of the customer's own items: saved addresses, order lines, contacts. Clicks on those rows are useful to see on the heatmap, but their text is personal. Mask the container:

```python
SIGHTLINE = {"MASK_SELECTORS": [".address-list", ".order-lines"]}
```

The element list then shows the selectors with empty labels, and you still see which rows are clicked.
