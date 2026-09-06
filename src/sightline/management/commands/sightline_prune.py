"""
Drop old raw events.

Grid cells, scroll bands and element counts are the durable part and are
never touched here. Events are the bulk, and their only reader is the
replay player, which nobody opens for a visit from three months ago.
"""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from sightline.conf import get_setting
from sightline.models import Event, PageView, Session


class Command(BaseCommand):
    help = "Delete recorded events and sessions older than the retention window."

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=None,
                            help="Override SIGHTLINE['RETAIN_DAYS'].")
        parser.add_argument("--dry-run", action="store_true",
                            help="Count what would go, delete nothing.")

    def handle(self, *args, **options):
        days = options["days"] or get_setting("RETAIN_DAYS")
        cutoff = timezone.now() - timedelta(days=days)

        sessions = Session.objects.filter(started_at__lt=cutoff)
        views = PageView.objects.filter(session__in=sessions)
        events = Event.objects.filter(pageview__in=views)

        counts = (sessions.count(), views.count(), events.count())
        if options["dry_run"]:
            self.stdout.write(
                f"Would delete {counts[0]} sessions, {counts[1]} page views, "
                f"{counts[2]} events older than {days} days.")
            return

        # Events go first and in batches: one delete of a few million rows
        # locks the table long enough to be noticed on a live site.
        while True:
            ids = list(events.values_list("pk", flat=True)[:5000])
            if not ids:
                break
            Event.objects.filter(pk__in=ids).delete()

        views.delete()
        sessions.delete()
        self.stdout.write(self.style.SUCCESS(
            f"Deleted {counts[0]} sessions, {counts[1]} page views, {counts[2]} events."))
