# Upgrading

## From a git install of django-sightline 0.1.x

Before 0.2.0 the package was installed from GitHub, under the distribution name `django-sightline`. From 0.2.0 on it is published on PyPI as `django-cc-sightline`. Only the distribution name changed. The import name, the app label, the migrations and the tables are the same, so your recorded data stays where it is.

1. Remove the old distribution, so pip does not keep two copies of the `sightline` module:

   ```bash
   pip uninstall django-sightline
   ```

2. Install the new one:

   ```bash
   pip install django-cc-sightline
   ```

3. Update your requirements file. Replace a line like

   ```text
   django-sightline @ git+https://github.com/qiyascc/django-sightline
   ```

   with

   ```text
   django-cc-sightline>=0.3,<0.4
   ```

4. Run the migrations and collect static files, as with any upgrade:

   ```bash
   python manage.py migrate sightline
   python manage.py collectstatic
   ```

Nothing else in your settings, middleware or URLs needs to change.

```{warning}
`pip install django-sightline` from PyPI installs an unrelated project that also uses the module name `sightline`. If you ran it by mistake, uninstall it and reinstall `django-cc-sightline`.
```

## What changed in 0.3.0

0.3.0 is a security release. There is no migration. Two defaults changed and may need action:

### Viewers need a permission

The panel, visit list, replays, heat data and live overlay now require the permission named in `PERMISSION`, `sightline.view_session` by default, on top of `is_staff`. Superusers are unaffected. Other staff get a 403 until you grant it, for example to a group:

```python
from django.contrib.auth.models import Group, Permission

group, _ = Group.objects.get_or_create(name="Sightline viewers")
group.permissions.add(Permission.objects.get(
    codename="view_session", content_type__app_label="sightline"))
```

Or keep the old behaviour with `SIGHTLINE = {"PERMISSION": None}`.

### The client IP no longer trusts X-Forwarded-For

Before 0.3.0 the first `X-Forwarded-For` entry was used, which the visitor controls. Now `REMOTE_ADDR` is used unless `IP_SOURCE` says otherwise. Behind a reverse proxy, set `"IP_SOURCE": "x-real-ip"` or `"xff-last"` (see [Proxies, CDNs and CSP](../guides/proxies-and-csp.md)); otherwise all visitors share the proxy's address and the new collect throttle limits them together.

### Other changes

* The collect endpoint is throttled per address and answers 429 past the limit. See `THROTTLE_*` in the [settings reference](../reference/settings.md).
* Paths that are not plain site paths are refused with 400, and with `RESOLVE_PATHS` paths your URLconf does not serve are ignored.
* A stored page title is no longer overwritten by later visits.
* `sightline_prune` also deletes heatmap rollups older than `ROLLUP_RETAIN_DAYS` (365 days).

## What changed in 0.2.0

These are the behaviour changes worth knowing about when you upgrade. The full list is in the [Changelog](../reference/changelog.md).

### The prune keeps visits by default

In 0.1.x, `sightline_prune` deleted old visits together with their events. From 0.2.0 it deletes only the events. The visit rows and their page views stay, so the visit list still shows them and they still count in the totals. A visit row is small; the events are what take the space.

If you relied on the old behaviour, either set

```python
SIGHTLINE = {"PRUNE_SESSIONS": True}
```

or pass `--sessions` to the command. See [Retention and pruning](../guides/retention.md).

### Visitors who sign in mid-visit are attributed

A visit used to be linked to an account only if the visitor was signed in when the visit started. Now the account is attached as soon as a batch arrives from a signed in user. See [User attribution](../guides/user-attribution.md).

### A full visit list

The panel links to a paged list of every visit ever recorded, with filters and a search. See [The admin panel](../guides/panel.md).

## Between 0.1.x releases

If you are still on an early 0.1 release, upgrade straight to the latest version. The second migration, `0002_alter_event_kind_alter_heatcell_kind`, adds the `overlay` event kind that popup recording needs; `migrate` applies it.
