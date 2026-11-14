# User attribution

A visit belongs to a person when one was signed in at any point during it. Everybody else is a guest, identified only by a salted visitor key.

## How a visit gets an account

Every batch the tracker sends is a normal same origin request, so it carries the visitor's cookies and Django knows who they are.

* **Signed in from the start.** When the first batch of a visit comes from a signed in user, the new `Session` row is created with that user.
* **Signed in halfway.** When a later batch of an existing visit comes from a signed in user and the visit has no user yet, the visit is linked to that user from then on. The pages viewed before signing in stay part of the same visit.
* **Never signed in.** The visit stays a guest visit.

The middle case matters more than it looks. The visits worth watching are often the ones that end in a sign up or a purchase, and those are exactly the visits where somebody signs in on the way. Without this, they would stay anonymous for their whole length.

A visit keeps the first account it was linked to. Signing out, or signing in as somebody else in the same tab, does not change it.

## Where you see it

* The **Who** column of the panel and the visit list shows the account, or a *guest* tag. In the visit list the guest tag is followed by the first characters of the visitor key.
* The **Signed in** and **Guests** filters of the visit list split the two.
* The search box finds visits by the email address of the account.

```{image} ../_static/screenshots/visits-known.jpg
:alt: The visit list filtered to signed in visitors
```

## Querying by user

The `Session.user` foreign key has the related name `sightline_sessions`:

```python
from django.contrib.auth import get_user_model

User = get_user_model()
leyla = User.objects.get(email="leyla@example.com")

visits = leyla.sightline_sessions.order_by("-started_at")
for visit in visits[:5]:
    print(visit.started_at, visit.device, visit.page_count, visit.duration_seconds)
```

Linking a support ticket to the customer's last visit is then one query:

```python
last = leyla.sightline_sessions.order_by("-started_at").first()
replay_path = f"/sightline/panel/replay/{last.pk}/"
```

If a user is deleted, their visits are kept and become guest visits (`on_delete=SET_NULL`).

## Staff

With `IGNORE_STAFF` on, pages served to staff carry no tracker, so staff do not start visits. A visitor who signs in **as staff** halfway through a visit is a special case: the tracker is already running in that tab, so the rest of the visit is still sent and the visit is linked to the staff account. This only happens when a staff member starts browsing signed out, which is rare outside of testing.

## Guests and the visitor key

Guests are identified by `visitor_key`, a hash of the IP address, the user agent, the language header, the date and a secret salt. It is the same for the same browser during one day and changes the next day, so it can group the visits of one person on one day but not follow them over weeks. See [Privacy](privacy.md).
