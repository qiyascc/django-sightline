# FAQ and troubleshooting

## The panel is empty

Almost always one of these, in order of likelihood:

1. **You browsed as staff.** Staff are not recorded by default. Open the site in a private window, or set `SIGHTLINE = {"IGNORE_STAFF": False}` while testing.
2. **Not enough time passed.** The first batch leaves about 1.2 seconds after the page loads. Wait a few seconds, then reload the panel.
3. **The range is wrong.** The panel defaults to 30 days, but if you clicked **Today** and the visit was yesterday, nothing shows. Check the filters at the top.
4. **The page has no tracker.** View the source of a page in a private window and look for `sightline/js/tracker.js` near the end. If it is not there, see the next question.

## The tracker is not in my pages

Check, in this order:

* `sightline.middleware.SightlineMiddleware` is in `MIDDLEWARE`, at the end, below `AuthenticationMiddleware` and `GZipMiddleware`.
* The path is not covered by `EXCLUDE_PATHS`.
* You are not staff, or `IGNORE_STAFF` is off.
* Your browser does not send `DNT: 1`, or `RESPECT_DNT` is off.
* You are using a real browser. `curl`, `wget`, `python-requests` and headless Chrome are treated as bots.
* `AUTO_INJECT` is on.
* The response is HTML, has status 200, is not a `StreamingHttpResponse` and contains `</body>`.
* The view did not set `response.sightline_skip = True`.

A quick check from the shell:

```python
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory

from sightline.utils import should_record

request = RequestFactory().get("/pricing/", HTTP_USER_AGENT="Mozilla/5.0")
request.user = AnonymousUser()
should_record(request)
```

`True` means the request passes the request side rules; if the page still has no tracker, look at the response.

## The tracker is there but nothing arrives

Open the browser's developer tools on the page:

* **Console errors about Content Security Policy.** The inline configuration script is blocked. See [Proxies, CDNs and CSP](../guides/proxies-and-csp.md).
* **No requests to the collect URL.** Check `sessionStorage.getItem("sightline.sampled")`. `"0"` means this tab was not sampled; see [Sampling](../guides/sampling.md).
* **Requests fail with 403.** Something in front of Django, such as a firewall rule, blocks the `POST`. The view itself is CSRF exempt.
* **Requests fail with 404.** The URLs are not included, or under a different prefix than the configuration says.
* **Answers say `"reason": "excluded"`.** The page path is in `EXCLUDE_PATHS`.
* **Answers say `"reason": "error"`.** Storing failed. A common cause is missing migrations; run `python manage.py migrate sightline`.

## The heatmap spots do not line up with the page

* **Different layouts per screen size.** Switch the device filter to **Desktop** or **Mobile**. See [Click heatmap](../guides/click-heatmap.md).
* **The page changed.** Clicks recorded before a redesign land where the old elements were. Use a shorter date range.
* **Content that differs between you and your visitors.** The overlay draws over the page as you see it. A signed out visitor may have seen a different layout.
* **The grid was changed.** Changing `GRID_COLUMNS` or `GRID_ROWS` after collecting data misplaces old cells.

## Replay shows an empty page

The player fetches the page as you, the staff member. It shows *This page could not be loaded* when that request fails, for example for a page that was removed, or one that belongs to another user and answers 403 or 404 for you. The pointer track still plays. See [Session replay](../guides/session-replay.md).

## Replay looks different from what the visitor saw

Replay shows the page as it is now, without its JavaScript. Content rendered in the browser, content specific to the visitor and changes made since the visit are not reproduced. This is by design: page contents are never recorded.

## Popups do not reopen in replay

* The popup's selector must match `OVERLAY_SELECTORS`. Add your class name or a `data-overlay` attribute.
* If the popup only exists in the HTML for signed out visitors, it is not in the copy the player fetches for you. The player says so on screen.
* If the popup is created by JavaScript, it is not in the copy either, because scripts are removed.

## Clicks on my menu button count as dead clicks

The dead click check sees links, buttons, form fields, labels, `summary`, `role="button"` and inline `onclick` attributes. A `div` with a listener added from JavaScript is not recognised. Add `role="button"` to it, or use a `button`. See [Rage and dead clicks](../guides/rage-and-dead-clicks.md).

## Does it slow my site down?

The tracker is about 3 KB gzipped, loads with `defer` and uses passive listeners. On the server, each batch is one short transaction. See [Performance and sizing](../guides/performance.md) for numbers and for what to do on busy sites.

## Does it work with a single page application?

Partly. The tracker does not watch client side route changes. Events after a route change are still stored on the page view of the page that was loaded first, so the heatmaps of the other routes stay empty. Server rendered sites get the most out of Sightline.

## Can I use it without the Django admin?

No. The panel, the replay player and staff detection are built on `django.contrib.admin` and its login.

## Can I install both django-sightline and django-cc-sightline?

No. The PyPI package `django-sightline` is a different project that also provides a `sightline` module. Installing both makes one overwrite the other's files. This project is `django-cc-sightline`.

## Is the data shared with anybody?

No. Everything stays in your database. There is no external service, no call home and no third party script.
