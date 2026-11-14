# Session replay

Replay plays one visit back: the pointer moving over the page, the scrolling, every click with a ripple, typing markers and popups, page after page, at the window size the visitor had.

```{image} ../_static/screenshots/replay.jpg
:alt: The replay player with the recorded page, a red cursor, the timeline and the list of pages in the visit
```

## Opening a replay

* In the panel, click **Replay** next to a visit under **Recent visits**.
* In the full [visit list](panel.md), click **Replay** on any row.
* In the admin **Sessions** list, click **Watch** in the **Replay** column.

With the usual `sightline/` prefix the player URL is `/sightline/panel/replay/<session id>/`, so a replay can be shared with another staff member as a link.

## The player

* **The stage** shows the page at the window size of the visit, scaled down to fit your screen. A phone visit plays at phone width.
* **The cursor** is a red dot. Clicks leave a ring; rage clicks are yellow and dead clicks grey.
* **Play / Pause** starts and stops playback.
* **Speed** plays at 0.5x, 1x, 2x or 4x.
* **The timeline** can be dragged to any moment. Seeking replays everything up to that point instantly, so the scroll position and any open popup are right where they were.
* **The page list** on the right lists every page of the visit with its duration. Click one to jump to it. When a page ends, playback moves on to the next by itself.

## How it works

Sightline records interactions, not the page. Playback loads the page as it exists **now** and moves a cursor over it.

1. The player asks the replay data endpoint for the visit: every page view with its path, window size and events in order.
2. For the current page, it fetches the HTML of that path with your browser, as the staff member watching.
3. It strips every `<script>` from the HTML, adds a `<base>` tag so relative links, stylesheets and images still resolve, and writes the result into a sandboxed iframe with `srcdoc`.
4. It sizes the iframe to the recorded window and scales it to fit.
5. Each event is applied when the clock reaches its time: `move` and `scroll` place the cursor and scroll the frame, clicks also draw a ring, `overlay` events open or close the popup.

Two details matter here:

* **Why the HTML is fetched and written in.** Django sends `X-Frame-Options: DENY` by default, and many sites add it again at the proxy. An iframe pointed at your own page would show a broken document icon. Writing the HTML in avoids navigation, so there is no header to refuse it.
* **Why scripts are removed.** The replay only needs the page to look right. Running your site's JavaScript inside it would start a second recording and could trigger real actions.

## Limits you should know about

This design keeps the recorder tiny, keeps the database small and avoids storing personal data that happened to be on screen. It also means:

* **A redesigned page replays against the new design.** If you moved a button since the visit, the cursor clicks where the button used to be.
* **Content specific to that visitor is not reproduced.** A cart with their items, their name in the header, search results for their query: the replay shows what the page returns for you right now.
* **Pages that only exist for the visitor fail to load.** An order confirmation page for an order that is not yours, or a page removed since, shows the note *This page could not be loaded* and the pointer track still plays over an empty stage.
* **Content built by JavaScript is missing.** Since scripts are stripped, parts of the page that are rendered in the browser do not appear. Server rendered pages replay best.
* **Typing is shown as a marker, not as text.** You see that somebody typed into a field, never what.

If you need pixel exact recordings of the DOM, use a tool built around that and accept its storage and privacy costs. For most sites, knowing where people clicked, how far they scrolled and where they got stuck is the part that matters.

## Who can watch

Every view of the player and its data endpoint requires an active staff account. Model permissions are not checked, so any staff member can watch any visit. Keep that in mind when you give staff access to people outside your team. See [Privacy](privacy.md).

## Finding visits worth watching

The visit list makes this quick:

* **Rage** and **Dead clicks** filters show visits where something did not respond.
* **Errors** shows visits with a JavaScript error.
* **Signed in** shows visits by known accounts, and the search box finds a visit by email address.
* A long visit is often more interesting than a short one. The `Session.is_interesting` property is true for visits with any signal or longer than two minutes, which is handy in your own queries and admin actions.
