# Changelog

## 0.4.0

* New opt-in `CAPTURE_INPUTS` (default `False`). When on, the tracker
  records what was typed into `input`, `textarea` and `select` fields,
  once the field settles (about 0.8 s after the last key, on change, on
  blur, on submit and when the page is left), cut to 160 characters, with
  the field's `name`, id, label or placeholder. Fields inside
  `MASK_SELECTORS` still record nothing. Password fields record only their
  length as `*` unless `CAPTURE_PASSWORDS` is also on. File inputs never
  record a value.
* The replay lists every typed value under its page, and fills the fields
  in as playback passes them.
* With `CAPTURE_INPUTS` off the collect endpoint drops any value or
  metadata sent with an input event, so the default stays "typing only".

## 0.3.0

Security release. Upgrading changes two defaults; read the last two points.

* Fixed stored XSS in the replay player. A path sent to the public collect
  endpoint was written into the step list as HTML. The list is now built
  with DOM nodes and text.
* Paths are validated at ingest. Only plain site paths are accepted (one
  leading slash, no backslash, no markup); anything else gets a 400. The
  player only fetches same site paths, and the heatmap links in the panel
  and the admin are only rendered for safe paths.
* The overlay and tracker config is escaped for inline scripts, so a
  crafted `sl_path` link can no longer break out of the script tag.
* The collect endpoint is throttled per address: `THROTTLE_BATCHES`
  (600 per `THROTTLE_BATCHES_SECONDS`, 600) and `THROTTLE_SESSIONS`
  (60 new visits per `THROTTLE_SESSIONS_SECONDS`, 3600), answering 429,
  counted in the cache named by `THROTTLE_CACHE`.
* `MAX_EVENTS_PER_SESSION` (5000) caps a visit, `MAX_META_BYTES` (1024)
  caps the event `meta` JSON, and with `RESOLVE_PATHS` (on) only paths
  that the URLconf serves create pages.
* A stored page title is no longer overwritten by later batches.
* `sightline_prune` also deletes heatmap rollups older than
  `ROLLUP_RETAIN_DAYS` (365, `0` keeps them) and pages left with no visit
  and no rollup. New `--rollup-days` option.
* **Default changed:** the panel, replays, heat data and overlay need the
  permission in `PERMISSION`, `sightline.view_session` by default, on top
  of staff status. Superusers pass. Grant it to your viewers or set
  `"PERMISSION": None` for the old behaviour.
* **Default changed:** the client address no longer trusts the first
  `X-Forwarded-For` entry, which the client controls. `IP_SOURCE` defaults
  to `"remote_addr"`; behind a proxy set `"x-real-ip"` or `"xff-last"`,
  or every visitor shares one throttle bucket and visitor keys collapse.
* No migration.

## 0.2.0

* Published on PyPI as `django-cc-sightline`. The app label, the import
  name and the tables are unchanged.
* Every visit is kept and listed. The panel links to a full visit list,
  paged and filterable by person, device or signal, with a search over
  email, visitor key and referrer.
* A guest who signs in halfway through a visit is attributed to that
  account from then on, so the visit is no longer anonymous.
* The prune deletes events only. Visits stay unless `PRUNE_SESSIONS` is
  set or `--sessions` is passed.
* Tested on Django 4.2 to 6.1.

## 0.1.3

* Popups are recorded and replayed. Anything matching a dialog selector is
  watched for opening and closing, and the player opens it again at the
  right moment. A replay that skipped them showed somebody clicking on a
  page that was covered at the time.
* When the popup is not in the fetched copy of the page, because it is
  only rendered for signed out visitors, the player says so on screen
  rather than replaying a page that looks untouched.
* The player forces visibility directly instead of guessing how the site
  opens the thing, and puts every change back when it closes.

## 0.1.2

* Replay works behind `X-Frame-Options: DENY`, which Django sends by
  default. The page is fetched and written into the frame instead of
  being loaded by URL, and its scripts are stripped.
* Replay is sized to the viewport the visit was recorded at, so a phone
  visit no longer plays back over a desktop layout.
* The tracker refuses to run outside the top window. A page that embeds
  part of itself was recording the frame as a separate visit under paths
  like `srcdoc`, which crowded out the real pages.
* Seeking backwards in the player now restores the scroll position.

## 0.1.1

* The panel works on a phone. Wide tables become stacked cards below 720
  pixels, so the Open heatmap button can no longer be pushed off screen.
* Any page can be opened in the overlay, recorded or not, from a new box
  in the panel or by passing `sl_path`.
* The empty state says why it is empty. Staff being excluded is the usual
  reason and it now says so on the screen.
* Fixed a multi line `{# #}` comment in the dashboard template printing
  itself to the page.

## 0.1.0

First release.

* Click, attention and scroll heatmaps drawn from a pre aggregated grid.
* Rage click and dead click detection.
* Session replay of pointer, scroll, clicks and typing markers.
* Live overlay on the real site, staff only.
* Admin panel with pages, visits and signals.
* Element click list.
* Automatic script injection through middleware.
* Retention pruning and a stats command.
