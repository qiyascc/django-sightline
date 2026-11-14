# Privacy

Sightline is built so that a heatmap does not turn into a surveillance log. This page lists what is stored, what is not, and what is still your responsibility.

## What is stored

| Data | Where | Notes |
| --- | --- | --- |
| Visitor key | `Session.visitor_key` | A salted hash, see below |
| Account | `Session.user` | Only when the visitor was signed in at some point |
| Device type, window size | `Session`, `PageView` | Desktop, tablet or mobile, and pixel sizes |
| User agent | `Session.user_agent` | First 300 characters |
| Language | `Session.language` | First 12 characters of `Accept-Language` |
| Referrer | `Session.referrer` | The page the visitor came from, first 500 characters |
| Paths and titles | `Page` | Query strings are dropped by default |
| Pointer positions, scrolling, clicks | `Event` | Positions in pixels and as fractions of the page |
| Element selectors and labels | `Event`, `ElementStat` | Labels are the visible text of clicked elements, unless [masked](masking.md) |
| Typing markers | `Event` | The field's selector, never the value |
| JavaScript error messages | `Event` | First 160 characters |
| Custom events | `Event` | Whatever your code passes to `sightline.mark()` |
| Counts | `HeatCell`, `ScrollBand`, `ElementStat` | Aggregates per page, day and device, with no link to a visit |

## What is not stored

* **IP addresses.** The IP is used to compute the visitor key and then discarded.
* **What people type.** Input values never leave the browser.
* **Screen contents.** No screenshots, no DOM snapshots. Replay draws a pointer over the current page.
* **Cookies or identifiers set by Sightline.** The tracker sets no cookies. It uses `sessionStorage`, which is cleared when the tab closes, for two values: the session id the server returned and the sampling decision.

## The visitor key

Guests are identified by a key computed on the server:

```text
sha256( client IP | user agent (200 chars) | Accept-Language (60 chars) | date | salt )
```

The first 40 hex characters are stored. Because the date is part of the input, the same person gets a new key every day. The key can group the visits of one browser within one day, but it cannot follow anybody across days, and it cannot be turned back into an IP address without the salt.

The salt is `SALT` from the settings, or your `SECRET_KEY` when `SALT` is empty. Set a separate salt if you rotate `SECRET_KEY`, so the keys of one day stay consistent:

```python
SIGHTLINE = {"SALT": env("SIGHTLINE_SALT")}
```

The client IP is taken from the first entry of `X-Forwarded-For` when that header exists, otherwise from `REMOTE_ADDR`. See [Proxies, CDNs and CSP](proxies-and-csp.md).

## Defaults that protect people

* **Do Not Track is honoured.** `RESPECT_DNT` is on by default.
* **Staff are excluded.** `IGNORE_STAFF` is on by default.
* **Query strings are dropped.** They often carry tokens, emails or campaign ids. `KEEP_QUERY_STRING` is off by default.
* **Bots are skipped**, which keeps their requests out of your data.
* **Raw events expire.** The prune command deletes them after `RETAIN_DAYS`, 90 by default, once you schedule it. See [Retention](retention.md).

## Who can see the data

The panel, the visit list, the replays and the heat data are open to every active staff user. Model permissions are not checked for these views. If some staff accounts should not watch replays, keep them out of `is_staff`, or put the Sightline URLs behind your own access check.

The admin pages for the raw tables follow Django's normal view permissions.

## Your part

Sightline cannot decide for you whether you need consent. That depends on where you and your visitors are, and on what else your site does. Some practical points:

* **Tell people.** Mention in your privacy policy that you record clicks, pointer movement and scrolling for usability analysis, on your own servers, and for how long you keep them.
* **Consent banners.** If your policy requires consent before recording, record only after it is given. One way is to exclude visitors who have not consented in a middleware subclass; see [Recording only some pages](../examples/some-pages-only.md) for the pattern.
* **Sensitive pages.** Exclude pages with health, payment or other sensitive content entirely, with `EXCLUDE_PATHS` or `sightline_skip`.
* **Personal text.** Mask containers that show personal data with `MASK_SELECTORS`, and keep personal data out of element ids and custom event metadata.
* **Requests for deletion.** A signed in user's visits are linked to their account. `user.sightline_sessions.all().delete()` removes them together with their page views and events. Guest visits cannot be linked to a person without extra data, which is the point of the daily key.
* **Retention.** Schedule `sightline_prune`, and choose `RETAIN_DAYS` to match your policy.
