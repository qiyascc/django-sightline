# Recipe: scheduled pruning

`sightline_prune` deletes raw events older than `RETAIN_DAYS`. It only runs when something runs it. This page has ready to use setups for the common schedulers. Pick one.

All examples assume the project lives in `/srv/mysite` with its virtual environment in `/srv/mysite/.venv`. Adjust the paths, and make sure the scheduled command sees the same settings and environment variables as your web process.

## cron

`crontab -e` as the user that runs the site:

```text
30 3 * * 0  cd /srv/mysite && /srv/mysite/.venv/bin/python manage.py sightline_prune >> /var/log/mysite/sightline-prune.log 2>&1
```

This runs every Sunday at 03:30. For a busy site, run it daily:

```text
30 3 * * *  cd /srv/mysite && /srv/mysite/.venv/bin/python manage.py sightline_prune >> /var/log/mysite/sightline-prune.log 2>&1
```

If your settings come from environment variables, cron does not load them. Source them in the command, or put them in the crontab:

```text
DJANGO_SETTINGS_MODULE=mysite.settings.production
30 3 * * 0  cd /srv/mysite && . ./.env.sh && .venv/bin/python manage.py sightline_prune
```

## systemd timer

`/etc/systemd/system/sightline-prune.service`:

```ini
[Unit]
Description=Prune old Sightline events

[Service]
Type=oneshot
User=www-data
WorkingDirectory=/srv/mysite
EnvironmentFile=/srv/mysite/.env
ExecStart=/srv/mysite/.venv/bin/python manage.py sightline_prune
Nice=10
```

`/etc/systemd/system/sightline-prune.timer`:

```ini
[Unit]
Description=Weekly Sightline prune

[Timer]
OnCalendar=Sun *-*-* 03:30:00
Persistent=true

[Install]
WantedBy=timers.target
```

Enable it and check when it runs next:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now sightline-prune.timer
systemctl list-timers sightline-prune.timer
```

Run it once by hand and read the output:

```bash
sudo systemctl start sightline-prune.service
journalctl -u sightline-prune.service -n 20
```

`Persistent=true` runs a missed prune after the machine was off at the scheduled time.

## Celery beat

`mysite/tasks.py`:

```python
from celery import shared_task
from django.core.management import call_command


@shared_task
def prune_sightline():
    call_command("sightline_prune")
```

In your Celery configuration:

```python
from celery.schedules import crontab

app.conf.beat_schedule = {
    "prune-sightline": {
        "task": "mysite.tasks.prune_sightline",
        "schedule": crontab(hour=3, minute=30, day_of_week=0),
    },
}
```

## django-q2

Create the schedule once, from a data migration or the shell:

```python
from django_q.models import Schedule
from django_q.tasks import schedule

schedule(
    "django.core.management.call_command",
    "sightline_prune",
    name="sightline-prune",
    schedule_type=Schedule.WEEKLY,
)
```

It then shows up in the admin under **Scheduled tasks**, where you can change the time.

## Docker and Kubernetes

In a container setup, run the command as a one off job with the same image and environment as the web container.

Docker Compose, from the host's cron:

```text
30 3 * * 0  cd /srv/mysite && docker compose run --rm web python manage.py sightline_prune
```

Kubernetes `CronJob`:

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: sightline-prune
spec:
  schedule: "30 3 * * 0"
  jobTemplate:
    spec:
      template:
        spec:
          restartPolicy: OnFailure
          containers:
            - name: prune
              image: registry.example.com/mysite:latest
              command: ["python", "manage.py", "sightline_prune"]
              envFrom:
                - secretRef:
                    name: mysite-env
```

## Before the first run

The first prune on a site that has been recording for months can delete millions of rows. Check first:

```bash
python manage.py sightline_prune --dry-run
```

Events are deleted in chunks of 5000, so the command does not hold one giant transaction, but it still loads the database. Run the first prune by hand at a quiet hour. Later runs only delete one interval's worth.

On PostgreSQL, a large first prune leaves dead rows behind. Autovacuum reclaims the space for reuse; the files on disk only shrink after a `VACUUM FULL`, which locks the table, so it is rarely worth it.
