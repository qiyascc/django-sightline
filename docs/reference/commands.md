# Management commands

## sightline_prune

Delete recorded events and, optionally, visits older than the retention window.

```bash
python manage.py sightline_prune [--days N] [--dry-run] [--sessions] [--rollup-days N]
```

| Option | Default | Meaning |
| --- | --- | --- |
| `--days N` | `RETAIN_DAYS` (90) | Age in days. Visits that **started** before now minus N days are affected. `0` falls back to the setting |
| `--dry-run` | off | Print what would be deleted and delete nothing |
| `--sessions` | `PRUNE_SESSIONS` (off) | Also delete the visits and their page views, not only their events |
| `--rollup-days N` | `ROLLUP_RETAIN_DAYS` (365) | Delete heatmap rollups older than N days and pages left empty. `0` keeps them |

What it does:

1. Finds the visits that started before the cutoff, their page views and their events.
2. With `--dry-run`, prints the counts and stops.
3. Deletes the events in chunks of 5000.
4. Without `--sessions` (and with `PRUNE_SESSIONS` off), stops here and keeps the visits and page views.
5. With `--sessions`, deletes the page views and the visits.

Heat cells, scroll bands, element counts and pages are never touched.

Output:

```console
$ python manage.py sightline_prune --dry-run
Would delete 48211 events older than 90 days. The 1312 visits themselves are kept.

$ python manage.py sightline_prune
Deleted 48211 events. Kept 1312 visits and 3920 page views.

$ python manage.py sightline_prune --days 30 --sessions --dry-run
Would delete 2410 sessions, 6630 page views, 151002 events older than 30 days.

$ python manage.py sightline_prune --days 30 --sessions
Deleted 2410 sessions, 6630 page views, 151002 events.
```

Scheduling examples are in [Scheduled pruning](../examples/scheduled-pruning.md).

## sightline_stats

Print a short summary of what Sightline recorded.

```bash
python manage.py sightline_stats [--days N]
```

| Option | Default | Meaning |
| --- | --- | --- |
| `--days N` | `7` | Length of the window, in days |

It prints the number of visits and page views that started in the window, the number of events on those page views, the total number of heat cells (all time), and the ten most viewed pages with their clicks:

```console
$ python manage.py sightline_stats --days 7
Last 7 days
  sessions   18
  page views 56
  events     1359
  heat cells 780

Top pages
      22      52 clicks  /shop/
      19      41 clicks  /
      11      44 clicks  /checkout/
       4      12 clicks  /accounts/login/
```

On an empty install the list of pages reads `nothing recorded yet`.

It is a quick way to check after a deploy that recording still works: run it, browse the site in a private window, run it again and compare.
