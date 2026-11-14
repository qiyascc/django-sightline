# JavaScript API

The tracker exposes one global object, `window.sightline`, once it has decided to record the current tab. On pages without the tracker, and in tabs that were not sampled, it does not exist, so always check before calling it.

## sightline.mark(name, meta)

Records a custom event.

| Argument | Type | Notes |
| --- | --- | --- |
| `name` | string | Converted with `String()` and cut to 160 characters. Stored as the event label |
| `meta` | object, optional | Stored as JSON in the event's `meta` field. Defaults to `{}` |

The event joins the queue and goes out with the next batch.

```javascript
if (window.sightline) {
  window.sightline.mark("video-played", { video: "intro", seconds: 42 });
}
```

See [Custom events](../guides/custom-events.md) for reading them back.

## sightline.flush()

Sends whatever is queued right now, without waiting for the five second timer. Use it after `mark()` when the page is about to change.

```javascript
window.sightline?.mark("download", { file: "pricing.pdf" });
window.sightline?.flush();
```

## Configuration object

`window.__sightline` is written by the middleware right before the tracker loads. It is meant for the tracker, not for your code, but it is useful when debugging:

```javascript
window.__sightline
```

```json
{
  "collect": "/sightline/collect/",
  "moveSampleMs": 120,
  "sampleRate": 1.0,
  "rageCount": 3,
  "rageWindowMs": 1000,
  "rageRadius": 32,
  "maskSelectors": [],
  "overlaySelectors": ["dialog", "[role=dialog]", "[aria-modal=true]", "[data-overlay]", ".modal", ".popup"],
  "overlayPollMs": 400
}
```

## Storage keys

The tracker sets no cookies. It uses two `sessionStorage` keys in your origin:

| Key | Value |
| --- | --- |
| `sightline.session` | The id of the current visit, as returned by the server |
| `sightline.sampled` | `"1"` if this tab is recorded, `"0"` if not |

Clearing them, or opening a new tab, starts a new visit and a new sampling draw.

## HTML attributes

| Attribute | Effect |
| --- | --- |
| `id` | Used as the element's selector, `#id` |
| `data-sightline="name"` | Used as the selector when the element has no `id`, `[data-sightline="name"]`. See [Element list](../guides/element-list.md) |
| `data-overlay` | Matches the default `OVERLAY_SELECTORS`, so the element is recorded as a popup |
| `role="button"` | Makes a click on the element count as a live click, not a dead one |
| `aria-label`, `data-title`, `title` | Used, in this order, as the name of a popup |

## Debugging in the browser

Open the developer tools on a page in a private window:

* **Is the tracker there?** `window.__sightline` should be an object and `window.sightline` should have `mark` and `flush`.
* **Are batches sent?** The network tab shows `POST` requests to the collect URL about a second after load and every five seconds while you interact. The answer contains `"ok": true` and the session id.
* **Which session am I?** `sessionStorage.getItem("sightline.session")` returns the id; the replay of your visit is at `/sightline/panel/replay/<id>/`.
* **Not sampled?** `sessionStorage.getItem("sightline.sampled")` returns `"0"`. Remove it and reload for a new draw.
