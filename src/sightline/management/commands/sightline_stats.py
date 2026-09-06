"""A quick look from the command line, for when the panel is not to hand."""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db.models import Count, Sum
from django.utils import timezone

from sightline.models import Event, HeatCell, Page, PageView, Session


class Command(BaseCommand):
    help = "Print what Sightline has recorded."

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=7)

    def handle(self, *args, **options):
        since = timezone.now() - timedelta(days=options["days"])
        sessions = Session.objects.filter(started_at__gte=since)
        views = PageView.objects.filter(started_at__gte=since)

        self.stdout.write(f"Last {options['days']} days")
        self.stdout.write(f"  sessions   {sessions.count()}")
        self.stdout.write(f"  page views {views.count()}")
        self.stdout.write(f"  events     {Event.objects.filter(pageview__in=views).count()}")
        self.stdout.write(f"  heat cells {HeatCell.objects.count()}")
        self.stdout.write("")

        rows = (views.values("page__path")
                .annotate(n=Count("id"), clicks=Sum("click_count"))
                .order_by("-n")[:10])
        self.stdout.write("Top pages")
        for row in rows:
            self.stdout.write(
                f"  {row['n']:>6}  {row['clicks'] or 0:>6} clicks  {row['page__path']}")
        if not rows:
            self.stdout.write("  nothing recorded yet")
