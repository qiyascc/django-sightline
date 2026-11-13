###############
# Qiyas Sadıqov CC
###############

from __future__ import annotations

from django.contrib import admin
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.html import format_html

from .models import (ElementStat, Event, HeatCell, Page, PageView, Panel,
                     ScrollBand, Session)


class ReadOnly(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(Panel)
class PanelAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_view_permission(self, request, obj=None):
        return request.user.is_active and request.user.is_staff

    def changelist_view(self, request, extra_context=None):
        return redirect("sightline:dashboard")


@admin.register(Page)
class PageAdmin(ReadOnly):
    list_display = ("path", "title", "view_count", "last_seen_at", "heatmap")
    search_fields = ("path", "title")
    ordering = ("-view_count",)

    @admin.display(description="Heatmap")
    def heatmap(self, obj):
        return format_html(
            '<a class="button" target="_blank" rel="noopener" '
            'href="{}?sightline=overlay&sl_page={}">Open</a>', obj.path, obj.pk)


@admin.register(Session)
class SessionAdmin(ReadOnly):
    list_display = ("started_at", "device", "page_count", "event_count",
                    "duration_seconds", "signals", "replay")
    list_filter = ("device", "has_rage", "has_dead_click", "has_error", "started_at")
    search_fields = ("visitor_key", "user_agent", "user__email")
    date_hierarchy = "started_at"

    @admin.display(description="Signals")
    def signals(self, obj):
        marks = []
        if obj.has_rage:
            marks.append("rage")
        if obj.has_dead_click:
            marks.append("dead")
        if obj.has_error:
            marks.append("error")
        return ", ".join(marks) or "quiet"

    @admin.display(description="Replay")
    def replay(self, obj):
        return format_html('<a class="button" href="{}">Watch</a>',
                           reverse("sightline:replay", args=[obj.pk]))


@admin.register(PageView)
class PageViewAdmin(ReadOnly):
    list_display = ("started_at", "page", "duration_ms", "max_scroll_pct",
                    "click_count")
    list_filter = ("started_at",)
    search_fields = ("page__path",)
    autocomplete_fields = ("page",)


@admin.register(Event)
class EventAdmin(ReadOnly):
    list_display = ("kind", "t_ms", "selector", "label", "pageview")
    list_filter = ("kind",)
    search_fields = ("selector", "label")


@admin.register(HeatCell)
class HeatCellAdmin(ReadOnly):
    list_display = ("page", "day", "device", "kind", "col", "row", "count")
    list_filter = ("device", "kind", "day")
    search_fields = ("page__path",)


@admin.register(ScrollBand)
class ScrollBandAdmin(ReadOnly):
    list_display = ("page", "day", "device", "band", "reached")
    list_filter = ("device", "day")
    search_fields = ("page__path",)


@admin.register(ElementStat)
class ElementStatAdmin(ReadOnly):
    list_display = ("selector", "label", "page", "day", "clicks",
                    "rage_clicks", "dead_clicks")
    list_filter = ("day",)
    search_fields = ("selector", "label", "page__path")
