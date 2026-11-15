###############
# Qiyas Sadıqov CC
###############

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from sightline.conf import get_setting
from sightline.models import (ElementStat, Event, HeatCell, Page, PageView,
                              ScrollBand, Session)


class Command(BaseCommand):
    help = ("Delete recorded events and sessions older than the retention window, "
            "and heatmap rollups older than the rollup window.")

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=None,
                            help="Override SIGHTLINE['RETAIN_DAYS'].")
        parser.add_argument("--dry-run", action="store_true",
                            help="Count what would go, delete nothing.")
        parser.add_argument("--sessions", action="store_true", default=None,
                            help="Also delete the visits, not just their events. "
                                 "Overrides SIGHTLINE['PRUNE_SESSIONS'].")
        parser.add_argument("--rollup-days", type=int, default=None,
                            help="Override SIGHTLINE['ROLLUP_RETAIN_DAYS']. 0 keeps "
                                 "rollups forever.")

    def handle(self, *args, **options):
        days = options["days"] or get_setting("RETAIN_DAYS")
        cutoff = timezone.now() - timedelta(days=days)

        sessions = Session.objects.filter(started_at__lt=cutoff)
        views = PageView.objects.filter(session__in=sessions)
        events = Event.objects.filter(pageview__in=views)

        drop_sessions = options["sessions"]
        if drop_sessions is None:
            drop_sessions = bool(get_setting("PRUNE_SESSIONS"))

        counts = (sessions.count(), views.count(), events.count())
        if options["dry_run"]:
            tail = (f"{counts[0]} sessions, {counts[1]} page views, "
                    if drop_sessions else "")
            self.stdout.write(
                f"Would delete {tail}{counts[2]} events older than {days} days."
                + ("" if drop_sessions else
                   f" The {counts[0]} visits themselves are kept."))
            self._rollups(options, dry_run=True)
            return

        while True:
            ids = list(events.values_list("pk", flat=True)[:5000])
            if not ids:
                break
            Event.objects.filter(pk__in=ids).delete()

        if not drop_sessions:
            self.stdout.write(self.style.SUCCESS(
                f"Deleted {counts[2]} events. Kept {counts[0]} visits and "
                f"{counts[1]} page views."))
        else:
            views.delete()
            sessions.delete()
            self.stdout.write(self.style.SUCCESS(
                f"Deleted {counts[0]} sessions, {counts[1]} page views, "
                f"{counts[2]} events."))
        self._rollups(options, dry_run=False)

    def _rollups(self, options, *, dry_run: bool) -> None:
        days = options["rollup_days"]
        if days is None:
            days = get_setting("ROLLUP_RETAIN_DAYS")
        if not days:
            return
        cutoff = timezone.now() - timedelta(days=days)
        day = cutoff.date()

        cells = HeatCell.objects.filter(day__lt=day)
        bands = ScrollBand.objects.filter(day__lt=day)
        elements = ElementStat.objects.filter(day__lt=day)
        counts = (cells.count(), bands.count(), elements.count())

        if dry_run:
            pages = self._empty_pages(cutoff, day).count()
            self.stdout.write(
                f"Would delete {counts[0]} heat cells, {counts[1]} scroll bands, "
                f"{counts[2]} element stats older than {days} days and {pages} "
                f"pages with no visits left.")
            return

        cells.delete()
        bands.delete()
        elements.delete()
        pages = self._empty_pages(cutoff, day).delete()[1].get("sightline.Page", 0)
        self.stdout.write(self.style.SUCCESS(
            f"Deleted {counts[0]} heat cells, {counts[1]} scroll bands, "
            f"{counts[2]} element stats and {pages} empty pages older than "
            f"{days} days."))

    def _empty_pages(self, cutoff, day):
        """Pages not seen since the cutoff, with no page view and no recent rollup."""
        return (Page.objects.filter(last_seen_at__lt=cutoff)
                .exclude(pk__in=PageView.objects.values("page_id"))
                .exclude(pk__in=HeatCell.objects.filter(day__gte=day).values("page_id"))
                .exclude(pk__in=ScrollBand.objects.filter(day__gte=day).values("page_id"))
                .exclude(pk__in=ElementStat.objects.filter(day__gte=day)
                         .values("page_id")))
