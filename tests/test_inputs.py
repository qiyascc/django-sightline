###############
# Qiyas Sadıqov CC
###############

from pathlib import Path

from django.test import TestCase

from sightline.models import Event

from .test_security import post, settings_with

STATIC = Path(__file__).resolve().parent.parent / "src" / "sightline" / "static"


def typed_batch():
    return {
        "url": "/shop/", "title": "Shop", "viewportWidth": 1280,
        "viewportHeight": 800, "documentHeight": 4000, "maxScrollPct": 10,
        "durationMs": 3000, "first": True,
        "events": [{"k": "input", "t": 1200, "sel": "#player-id",
                    "lbl": "51234567", "m": {"field": "player_id"}}],
    }


class InputCaptureTests(TestCase):
    def send(self):
        return post(self.client, typed_batch())

    def test_values_are_dropped_when_capture_is_off(self):
        self.send()
        row = Event.objects.get(kind="input")
        self.assertEqual((row.selector, row.label, row.meta), ("#player-id", "", {}))

    @settings_with(CAPTURE_INPUTS=True)
    def test_values_are_kept_when_capture_is_on(self):
        self.send()
        row = Event.objects.get(kind="input")
        self.assertEqual((row.label, row.meta), ("51234567", {"field": "player_id"}))

    def test_tracker_hides_passwords_unless_asked(self):
        source = (STATIC / "sightline/js/tracker.js").read_text()
        self.assertIn('type === "password" && !config.capturePasswords', source)

    def test_replay_writes_typed_text_as_text(self):
        source = (STATIC / "sightline/js/replay.js").read_text()
        self.assertNotIn("innerHTML", source)
        self.assertIn("value.textContent", source)
