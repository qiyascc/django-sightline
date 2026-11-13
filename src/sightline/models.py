###############
# Qiyas Sadıqov CC
###############

from __future__ import annotations

import uuid

from django.conf import settings as django_settings
from django.db import models
from django.utils import timezone


class Device(models.TextChoices):
    DESKTOP = "desktop", "Desktop"
    TABLET = "tablet", "Tablet"
    MOBILE = "mobile", "Mobile"


class Session(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    visitor_key = models.CharField(max_length=64, db_index=True)
    user = models.ForeignKey(
        django_settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="sightline_sessions",
    )

    device = models.CharField(max_length=10, choices=Device.choices,
                              default=Device.DESKTOP, db_index=True)
    viewport_width = models.PositiveIntegerField(default=0)
    viewport_height = models.PositiveIntegerField(default=0)
    user_agent = models.CharField(max_length=300, blank=True)
    language = models.CharField(max_length=12, blank=True)
    referrer = models.CharField(max_length=500, blank=True)

    started_at = models.DateTimeField(default=timezone.now, db_index=True)
    last_seen_at = models.DateTimeField(default=timezone.now)
    duration_ms = models.PositiveIntegerField(default=0)
    page_count = models.PositiveIntegerField(default=0)
    event_count = models.PositiveIntegerField(default=0)

    has_rage = models.BooleanField(default=False, db_index=True)
    has_dead_click = models.BooleanField(default=False)
    has_error = models.BooleanField(default=False)

    class Meta:
        ordering = ["-started_at"]
        indexes = [
            models.Index(fields=["-started_at", "device"]),
            models.Index(fields=["has_rage", "-started_at"]),
        ]

    def __str__(self):
        return f"{self.device} {self.started_at:%Y-%m-%d %H:%M}"

    @property
    def duration_seconds(self) -> int:
        return round(self.duration_ms / 1000)

    @property
    def is_interesting(self) -> bool:
        return self.has_rage or self.has_dead_click or self.has_error \
            or self.duration_ms > 120_000


class Page(models.Model):
    path = models.CharField(max_length=500, unique=True)
    title = models.CharField(max_length=300, blank=True)
    first_seen_at = models.DateTimeField(default=timezone.now)
    last_seen_at = models.DateTimeField(default=timezone.now, db_index=True)
    view_count = models.PositiveIntegerField(default=0, db_index=True)

    class Meta:
        ordering = ["-view_count", "path"]

    def __str__(self):
        return self.path


class PageView(models.Model):
    session = models.ForeignKey(Session, on_delete=models.CASCADE,
                                related_name="pageviews")
    page = models.ForeignKey(Page, on_delete=models.CASCADE, related_name="views")

    started_at = models.DateTimeField(default=timezone.now, db_index=True)
    duration_ms = models.PositiveIntegerField(default=0)

    viewport_width = models.PositiveIntegerField(default=0)
    viewport_height = models.PositiveIntegerField(default=0)
    document_height = models.PositiveIntegerField(default=0)

    max_scroll_pct = models.PositiveSmallIntegerField(default=0)
    click_count = models.PositiveIntegerField(default=0)

    scroll_band = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["started_at"]
        indexes = [models.Index(fields=["page", "-started_at"])]

    def __str__(self):
        return f"{self.page.path} @ {self.started_at:%H:%M:%S}"


class Event(models.Model):
    class Kind(models.TextChoices):
        CLICK = "click", "Click"
        MOVE = "move", "Pointer move"
        SCROLL = "scroll", "Scroll"
        RAGE = "rage", "Rage click"
        DEAD = "dead", "Dead click"
        INPUT = "input", "Typing"
        RESIZE = "resize", "Resize"
        OVERLAY = "overlay", "Overlay shown or hidden"
        ERROR = "error", "Script error"
        CUSTOM = "custom", "Custom"

    pageview = models.ForeignKey(PageView, on_delete=models.CASCADE,
                                 related_name="events")
    kind = models.CharField(max_length=10, choices=Kind.choices, db_index=True)

    t_ms = models.PositiveIntegerField(default=0)
    x = models.IntegerField(default=0)
    y = models.IntegerField(default=0)
    x_pct = models.FloatField(default=0.0)
    y_pct = models.FloatField(default=0.0)
    scroll_y = models.IntegerField(default=0)

    selector = models.CharField(max_length=300, blank=True)
    label = models.CharField(max_length=160, blank=True)
    meta = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["t_ms", "id"]
        indexes = [
            models.Index(fields=["pageview", "t_ms"]),
            models.Index(fields=["kind"]),
        ]

    def __str__(self):
        return f"{self.kind} {self.t_ms}ms"


class HeatCell(models.Model):
    page = models.ForeignKey(Page, on_delete=models.CASCADE, related_name="cells")
    day = models.DateField(db_index=True)
    device = models.CharField(max_length=10, choices=Device.choices)
    kind = models.CharField(max_length=10, choices=Event.Kind.choices)

    col = models.PositiveSmallIntegerField()
    row = models.PositiveSmallIntegerField()
    count = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["page", "day", "device", "kind", "col", "row"],
                name="sightline_cell_once",
            ),
        ]
        indexes = [models.Index(fields=["page", "device", "kind", "day"])]

    def __str__(self):
        return f"{self.page.path} {self.kind} [{self.col},{self.row}] {self.count}"


class ScrollBand(models.Model):
    page = models.ForeignKey(Page, on_delete=models.CASCADE, related_name="bands")
    day = models.DateField(db_index=True)
    device = models.CharField(max_length=10, choices=Device.choices)
    band = models.PositiveSmallIntegerField()
    reached = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["page", "day", "device", "band"],
                                    name="sightline_band_once"),
        ]

    def __str__(self):
        return f"{self.page.path} {self.band * 5}% {self.reached}"


class ElementStat(models.Model):
    page = models.ForeignKey(Page, on_delete=models.CASCADE, related_name="elements")
    day = models.DateField(db_index=True)
    selector = models.CharField(max_length=300)
    label = models.CharField(max_length=160, blank=True)
    clicks = models.PositiveIntegerField(default=0)
    rage_clicks = models.PositiveIntegerField(default=0)
    dead_clicks = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-clicks"]
        constraints = [
            models.UniqueConstraint(fields=["page", "day", "selector"],
                                    name="sightline_element_once"),
        ]

    def __str__(self):
        return f"{self.selector} ({self.clicks})"


class Panel(Session):
    class Meta:
        proxy = True
        verbose_name = "Sightline panel"
        verbose_name_plural = "Sightline panel"
