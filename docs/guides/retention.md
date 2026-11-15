# Retention and pruning

Raw events are the bulk of what Sightline stores. They are needed for replay, and only for replay. Heatmaps, scroll maps and element counts are kept in rollup tables that are small and are never pruned. So the plan is simple: keep raw events for a while, then delete them, and the maps keep working.

## What is kept and what goes

| Table | Pruned | Why |
| --- | --- | --- |
| `Event` | Yes, after `RETAIN_DAYS` | The bulk of the data, needed only for replay and custom event queries |
| `Session` | Only with `PRUNE_SESSIONS` or `--sessions` | A few hundred bytes per visit, and what the visit list shows |
| `PageView` | Only with `PRUNE_SESSIONS` or `--sessions` | Small, and what the panel's page table counts |
| `HeatCell` | Never | The heatmap, already aggregated |
| `ScrollBand` | Never | The scroll map, already aggregated |
| `ElementStat` | Never | The element list, already aggregated |
| `Page` | Never | One row per path |

A heatmap from last year still draws after its raw events are gone. A replay older than `RETAIN_DAYS` does not: the visit is still listed, but it has no events to play.

## The prune command

```bash
python manage.py sightline_prune
```

It deletes the events of every visit that started more than `RETAIN_DAYS` days ago (90 by default). Events are deleted in chunks of 5000, so a large first prune does not hold one huge transaction.

It also deletes heatmap rollups (`HeatCell`, `ScrollBand`, `ElementStat`) for days older than `ROLLUP_RETAIN_DAYS`, 365 by default, and then pages that were not seen since then and have no page view and no rollup left. Set `ROLLUP_RETAIN_DAYS` to `0` to keep rollups forever.

### Options

| Option | Effect |
| --- | --- |
| `--days N` | Use N days instead of `RETAIN_DAYS` |
| `--dry-run` | Count what would be deleted and delete nothing |
| `--sessions` | Also delete the old visits and their page views. Overrides `PRUNE_SESSIONS` |
| `--rollup-days N` | Use N days instead of `ROLLUP_RETAIN_DAYS`; `0` keeps rollups |

Always start with a dry run:

```console
$ python manage.py sightline_prune --dry-run
Would delete 48211 events older than 90 days. The 1312 visits themselves are kept.
```

```console
$ python manage.py sightline_prune
Deleted 48211 events. Kept 1312 visits and 3920 page views.
```

With `--sessions`:

```console
$ python manage.py sightline_prune --days 180 --sessions --dry-run
Would delete 655 sessions, 1840 page views, 21022 events older than 180 days.
```

## Settings

```python
SIGHTLINE = {
    "RETAIN_DAYS": 90,
    "PRUNE_SESSIONS": False,
}
```

* `RETAIN_DAYS` is how long raw events are kept. Shorter means a smaller database and older replays disappearing sooner.
* `PRUNE_SESSIONS` makes the prune delete old visits and page views too. Leave it off unless the session table itself has become a storage problem. Removing visits turns months of history in the visit list into an empty screen, and the panel's page table counts page views, so old ranges would show zero views.

## Scheduling it

The prune does nothing until something runs it. Once a week is enough for most sites, once a day for busy ones. The [scheduled pruning recipe](../examples/scheduled-pruning.md) has complete examples for cron, a systemd timer, Celery beat and django-q.

The short version with cron:

```text
30 3 * * 0  cd /srv/mysite && /srv/mysite/.venv/bin/python manage.py sightline_prune >> /var/log/sightline-prune.log 2>&1
```

## Checking what you have

```bash
python manage.py sightline_stats --days 30
```

prints the visits, page views and events of the last 30 days, the total number of heat cells and the ten most viewed pages. See [Management commands](../reference/commands.md).

## Deleting everything

To start over, for example after changing the grid size, delete the rows from the shell:

```python
from sightline.models import ElementStat, HeatCell, Page, ScrollBand, Session

Session.objects.all().delete()
HeatCell.objects.all().delete()
ScrollBand.objects.all().delete()
ElementStat.objects.all().delete()
Page.objects.all().delete()
```

Deleting sessions also deletes their page views and events. On a large table this is slow; on PostgreSQL, `TRUNCATE` of the seven `sightline_*` tables is the fast way.
