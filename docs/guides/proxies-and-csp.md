# Proxies, CDNs and CSP

Most production sites sit behind a reverse proxy, many behind a CDN, and some send a Content Security Policy. This page covers what each of them means for Sightline.

## Reverse proxies

### Client IP and the visitor key

The visitor key is computed from the client IP, among other things. Sightline takes the IP from the **first** entry of the `X-Forwarded-For` header when it exists, and from `REMOTE_ADDR` otherwise.

* **Your proxy sets `X-Forwarded-For`** (nginx with `proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;`, most load balancers and CDNs): visitor keys work as intended.
* **Your proxy does not set it**: every request seems to come from the proxy's address. Keys are then based on the user agent and language alone, so different people with the same browser get the same key on the same day. Configure the header.

A visitor can send a fake `X-Forwarded-For`. The only effect is on their own visitor key, which is a grouping aid and not a security feature, so this does not matter for Sightline.

### Compression and other response middleware

Keep `SightlineMiddleware` last in `MIDDLEWARE`, below `GZipMiddleware` and `ConditionalGetMiddleware`. It then inserts the tracker before the response is compressed and before an ETag is computed over the body. Compression done by the proxy (nginx `gzip on;`, Brotli at the CDN) happens after Django and needs nothing special.

### The collect URL

The collect URL receives `POST` requests with a JSON body, sent with `fetch` or `sendBeacon`. Beacons are sent with the content type `text/plain`, which the view accepts. Make sure that:

* the proxy and any web application firewall let `POST /sightline/collect/` through,
* bodies of up to 512 KB are allowed (nginx `client_max_body_size` is 1 MB by default, which is enough),
* it is never cached.

The view is exempt from CSRF checks. The tracker fires during page unload, where a token round trip is not possible, and the endpoint reads and changes nothing that belongs to a signed in user. Its guards are the body size and the shape of the payload.

## CDNs and HTML caching

If your CDN or a cache like Varnish stores whole HTML pages, the tracker is decided when the page is rendered for the cache, not for each visitor:

* A page cached from a normal visitor's request contains the tracker, and every visitor who gets that copy is recorded. Staff who get a cached copy are recorded too, and `RESPECT_DNT` is not applied per visitor.
* A page cached from a staff request (if your cache stores pages for signed in users, which it usually should not) contains no tracker, and nobody is recorded until the copy expires.

Most setups bypass the cache for signed in users through a session cookie, which avoids the second case and also keeps staff out of the first. If the per visitor Do Not Track check matters to you, keep HTML pages out of the shared cache.

The overlay uses `?sightline=overlay`. Make sure the cache key includes the query string, or that requests with this parameter bypass the cache, so the overlay is never stored and served to visitors. It is only injected for staff, so a staff session cookie that bypasses the cache handles this too.

Static files (`tracker.js`, `overlay.js`, `replay.js`, `sightline.css`) are ordinary static files and are fine on a CDN. Run `collectstatic` after upgrades.

## Content Security Policy

The tracker snippet is two tags:

```html
<script>window.__sightline = {...};</script>
<script src="/static/sightline/js/tracker.js" defer></script>
```

The external file is covered by `script-src 'self'` (or your static host). The first tag is an **inline script without a nonce**. A policy that blocks inline scripts lets `tracker.js` load, but the tracker finds no configuration and does nothing.

### Option 1: allow it by hash

The inline script is the same on every page as long as the settings and the URL prefix do not change, so a hash works:

1. Open a page in a private window with the browser's developer tools open.
2. The console reports the blocked inline script and prints the hash it would accept, in the form `'sha256-...'`.
3. Add that value to `script-src` in your policy.

You can also compute it yourself from the exact text between `<script>` and `</script>`:

```bash
printf '%s' 'window.__sightline = {...};' | openssl dgst -sha256 -binary | openssl base64
```

Recompute the hash whenever you change a `SIGHTLINE` setting that the browser receives (the collect URL, `SAMPLE_RATE`, `MOVE_SAMPLE_MS`, the rage settings, `MASK_SELECTORS`, `OVERLAY_SELECTORS`, `OVERLAY_POLL_MS`) and after upgrading the package.

### Option 2: allow inline scripts

`script-src 'self' 'unsafe-inline'` works, but it weakens the policy for your whole site. Prefer the hash.

### Other directives

* `connect-src 'self'` covers the batches, which go to your own origin with `fetch` and `sendBeacon`.
* The overlay and the panel use your static CSS file, so `style-src 'self'` is enough for them. The JavaScript sets inline styles through the DOM, which CSP does not block.

### The overlay, the panel and replay

These are staff pages and carry their own inline scripts:

* the overlay's configuration includes the current path, so it changes from page to page and cannot be allowed by one hash,
* the panel has a short inline script for the **Open the heatmap on any page** box,
* the replay page has an inline configuration with the visit's data URL.

Under a strict policy, these parts do not start. If your policy is applied site wide, relax it for the Sightline URLs and for requests with `?sightline=overlay`, or allow `'unsafe-inline'` for staff only, using whatever produces your policy (a third party package, Django's own CSP support in recent versions, or your proxy).

The replay frame is filled with `srcdoc` and sandboxed without `allow-scripts`. Its document inherits the policy of the replay page, so images and stylesheets of your site must be allowed there too.

```{note}
Strict CSP setups vary a lot. The points above come from how Sightline injects and loads its code; they have not been tested against every policy. Check the browser console for violations after enabling Sightline.
```
