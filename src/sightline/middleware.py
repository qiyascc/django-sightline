###############
# Qiyas Sadıqov CC
###############

from __future__ import annotations

from django.template.loader import render_to_string
from django.urls import NoReverseMatch, reverse

from .conf import get_setting
from .utils import can_view_panel, script_json, should_record

BODY_CLOSE = b"</body>"


class SightlineMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if not self._html(response):
            return response

        overlay = self._overlay_wanted(request)
        if not overlay:
            if not get_setting("AUTO_INJECT"):
                return response
            if not self._suitable(request, response):
                return response

        try:
            snippet = (self._overlay(request) if overlay
                       else self._snippet(request)).encode("utf-8")
        except NoReverseMatch:
            return response

        body = response.content
        index = body.rfind(BODY_CLOSE)
        if index == -1:
            return response
        response.content = body[:index] + snippet + body[index:]
        if response.has_header("Content-Length"):
            response["Content-Length"] = str(len(response.content))
        return response

    def _html(self, response) -> bool:
        if getattr(response, "streaming", False):
            return False
        if response.status_code != 200:
            return False
        if "text/html" not in response.get("Content-Type", ""):
            return False
        return not getattr(response, "sightline_skip", False)

    def _suitable(self, request, response) -> bool:
        return should_record(request)

    def _overlay_wanted(self, request) -> bool:
        if request.GET.get("sightline") != "overlay":
            return False
        return can_view_panel(getattr(request, "user", None))

    def _overlay(self, request) -> str:
        config = {
            "dataUrl": reverse("sightline:heat_data"),
            "panelUrl": reverse("sightline:dashboard"),
            "pageId": request.GET.get("sl_page", ""),
            "path": request.GET.get("sl_path", "") or request.path,
            "days": request.GET.get("sl_days", "30"),
            "device": request.GET.get("sl_device", ""),
        }
        return render_to_string("sightline/_overlay.html", {
            "config": script_json(config),
        })

    def _snippet(self, request) -> str:
        config = {
            "collect": reverse("sightline:collect"),
            "moveSampleMs": get_setting("MOVE_SAMPLE_MS"),
            "sampleRate": get_setting("SAMPLE_RATE"),
            "rageCount": get_setting("RAGE_CLICK_COUNT"),
            "rageWindowMs": get_setting("RAGE_CLICK_WINDOW_MS"),
            "rageRadius": get_setting("RAGE_CLICK_RADIUS_PX"),
            "maskSelectors": get_setting("MASK_SELECTORS"),
            "captureInputs": bool(get_setting("CAPTURE_INPUTS")),
            "capturePasswords": bool(get_setting("CAPTURE_PASSWORDS")),
            "overlaySelectors": get_setting("OVERLAY_SELECTORS"),
            "overlayPollMs": get_setting("OVERLAY_POLL_MS"),
        }
        return render_to_string("sightline/_tracker.html", {
            "config": script_json(config),
        })
