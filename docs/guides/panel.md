# The admin panel

The panel is one screen inside your Django admin with the pages, the visits and the signals Sightline has recorded. It uses the admin's own layout, colours and dark mode, so it looks like the rest of your admin.

## Getting there

Sign in to the admin as staff. The sidebar has a **Sightline** section; its **Sightline panel** entry opens the panel. The entry is a proxy model whose list page redirects to the panel, which is how an app can add a link to the admin index without changing your `AdminSite`.

With the usual URL prefix, the panel is at `/sightline/panel/`.

## The panel

```{image} ../_static/screenshots/panel.jpg
:alt: The Sightline panel
```

From top to bottom:

**Filters.** The date range (**Today**, **7 days**, **30 days**, **90 days**) and the device (**All devices**, **Desktop**, **Tablet**, **Mobile**). They apply to everything below. The range is a `days` query parameter and accepts any value from 1 to 365, so `?days=180` works too.

**Open the heatmap on any page.** Type a path and press **Open** to see the overlay on that page, recorded or not.

**Totals.** The number of visits in the range, and how many of them had rage clicks, dead clicks and script errors.

**Pages.** The 50 most viewed pages in the range, with:

* the path and the page title,
* **Views**: page views in the range,
* **Clicks**: plain clicks on those views,
* **Avg scroll**: the average deepest scroll per view,
* **Open heatmap**: the overlay for that page.

**Recent visits.** The 40 most recent visits in the range: who (the account, or *guest*), when, device, number of pages, length and signals, with a **Replay** button each. **See all** opens the full visit list.

If nothing is recorded yet, the tables say why. The most common reason is that staff are not recorded, so browsing your own site while signed in leaves the panel empty. See [Quickstart](../getting-started/quickstart.md), step 6.

## The visit list

**See all** opens every visit ever recorded, newest first, 50 per page.

```{image} ../_static/screenshots/visits.jpg
:alt: The visit list with the search box, the signal and device filters and a page of visits
```

It is not limited by a date range. The panel's own list is short because a dashboard is for glancing; this one is for looking things up.

### Filters

| Filter | Shows |
| --- | --- |
| **All** | Every visit |
| **Signed in** | Visits linked to an account |
| **Guests** | Visits with no account |
| **Rage** | Visits with at least one rage click |
| **Dead clicks** | Visits with at least one dead click |
| **Errors** | Visits with a JavaScript error |
| Device | **All devices**, **Desktop**, **Tablet**, **Mobile** |

The signal and the device combine: **Rage** and **Mobile** together show rage clicks on phones.

### Search

The search box matches, case insensitively, any part of:

* the email address of the linked account,
* the visitor key,
* the referrer.

So you can find a customer's visit by their email, all visits from one visitor on one day by the key shown next to *guest*, or the visits that came from a campaign by part of the referrer URL.

```{image} ../_static/screenshots/visits-known.jpg
:alt: The visit list filtered to signed in visitors
```

### Query parameters

The list is driven by the query string, so a filtered view can be bookmarked or linked:

| Parameter | Values |
| --- | --- |
| `signal` | `known`, `guest`, `rage`, `dead`, `error` |
| `device` | `desktop`, `tablet`, `mobile` |
| `q` | Search text |
| `page` | Page number |

For example `/sightline/panel/visits/?signal=rage&device=mobile`.

## The admin model pages

The **Sightline** section of the admin also lists the raw tables: **Element stats**, **Events**, **Heat cells**, **Page views**, **Pages**, **Scroll bands** and **Sessions**. They are read only: recorded data is evidence, not content, so it cannot be added or edited by hand. Rows can still be deleted through the admin if you need to remove something.

Useful pages there:

* **Pages**, ordered by views, with an **Open** button for the heatmap.
* **Sessions**, with filters for device, the three signals and the start date, a date drill down, a search over visitor key, user agent and email, and a **Watch** button for the replay.
* **Events**, filterable by kind. Filter by *Custom* to see your [custom events](custom-events.md).
* **Element stats**, see [Element list](element-list.md).

## Access

The panel, the visit list, the replay and the heat data are open to any **active staff** user. They do not check model permissions. The raw model pages in the admin follow Django's normal view permissions.

## On a phone

Below 720 pixels the wide tables of the panel and the visit list turn into stacked cards, one card per row.
