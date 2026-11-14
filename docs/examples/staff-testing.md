# Recipe: testing with staff accounts

Staff are not recorded by default. That is right for production, where your team's clicks would only distort the numbers, and confusing during development, where you are usually signed in as staff and the panel stays empty. This recipe sets up both sides properly.

## Local development: record yourself

In your development settings only:

```python
SIGHTLINE = {
    "IGNORE_STAFF": False,
}
```

Now your own pages carry the tracker. Browse the site in the same browser you use for the admin, then open the panel.

If you also want to see your clicks on a page where you use the overlay, use two windows: one to click around (normal pages record you), one with `?sightline=overlay` to look at the result. A page with the overlay never records, even with `IGNORE_STAFF` off.

If your base settings already define `SIGHTLINE`, extend that dict in the development file rather than replacing it:

```python
SIGHTLINE = {**SIGHTLINE, "IGNORE_STAFF": False}
```

## Staging: keep the defaults, test as a visitor

On a staging server, keep `IGNORE_STAFF` on and test like a visitor would:

1. Open the site in a private window, or a second browser profile, where you are not signed in.
2. Do the thing you want to check.
3. Open the panel in your normal window.

This is the setup closest to production, and it is the one that tells you whether the tracker actually reaches visitors.

## Automated tests of your project

### Asserting the tracker is there

The Django test client sends no user agent, so it is not mistaken for a bot, and anonymous requests get the tracker:

```python
from django.test import TestCase


class TrackerTests(TestCase):
    def test_home_page_carries_the_tracker(self):
        response = self.client.get("/")
        self.assertContains(response, "sightline/js/tracker.js")

    def test_account_pages_do_not(self):
        response = self.client.get("/account/")
        self.assertNotContains(response, "sightline/js/tracker.js")
```

### Turning it off in tests

If the extra markup gets in the way of your own HTML assertions, switch injection off for the test run:

```python
from django.test import TestCase, override_settings


@override_settings(SIGHTLINE={"AUTO_INJECT": False})
class CheckoutPageTests(TestCase):
    ...
```

or once, in the settings used by the test runner:

```python
SIGHTLINE = {"AUTO_INJECT": False}
```

Sightline reads its settings on every request, so `override_settings` works without restarting anything.

### Browser tests

Headless Chrome identifies itself as `HeadlessChrome`, which matches the bot pattern, so Playwright and Selenium tests in headless mode are not recorded. That is usually what you want. To record them, for example to produce demo data on a staging site, give the browser a normal user agent:

```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    context = browser.new_context(
        user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36",
    )
    page = context.new_page()
    page.goto("https://staging.example.com/")
```

The tracker sends its first batch about 1.2 seconds after load and then every five seconds. A test that leaves the page immediately may record nothing; call `window.sightline.flush()` and wait a moment before navigating away.

## Cleaning up test data

If you recorded yourself on a shared database, delete your own visits from the shell:

```python
from django.contrib.auth import get_user_model

me = get_user_model().objects.get(username="admin")
me.sightline_sessions.all().delete()
```

This removes the visits, their page views and their events. The heatmap rollups are not linked to visits, so clicks you made stay in the maps. On a staging database, the [delete everything](../guides/retention.md#deleting-everything) snippet starts clean.
