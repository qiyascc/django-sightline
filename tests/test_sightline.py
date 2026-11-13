###############
# Qiyas Sadıqov CC
###############

import json
import uuid
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from sightline.models import (Device, ElementStat, Event, HeatCell, Page,
                              PageView, ScrollBand, Session)
from sightline.utils import clean_path, device_of, is_bot, visitor_key

User = get_user_model()


def batch(**extra):
    payload = {
        "url": "/shop/",
        "title": "Shop",
        "viewportWidth": 1280,
        "viewportHeight": 800,
        "documentHeight": 4000,
        "maxScrollPct": 50,
        "durationMs": 4200,
        "first": True,
        "events": [
            {"k": "click", "t": 900, "x": 640, "y": 400, "xp": 0.5, "yp": 0.1,
             "s": 0, "sel": "#buy", "lbl": "Buy now"},
            {"k": "move", "t": 500, "x": 200, "y": 300, "xp": 0.15, "yp": 0.07},
        ],
    }
    payload.update(extra)
    return payload


class CollectTests(TestCase):
    url = "/sightline/collect/"

    def post(self, payload, **extra):
        return self.client.post(self.url, data=json.dumps(payload),
                                content_type="application/json", **extra)

    def test_a_batch_creates_a_session_a_page_and_a_view(self):
        answer = self.post(batch()).json()
        self.assertTrue(answer["ok"])
        self.assertEqual(Session.objects.count(), 1)
        self.assertEqual(Page.objects.get().path, "/shop/")
        self.assertEqual(PageView.objects.count(), 1)

    def test_the_events_are_stored(self):
        self.post(batch())
        self.assertEqual(Event.objects.count(), 2)

    def test_the_second_batch_joins_the_same_session(self):
        first = self.post(batch()).json()
        self.post(batch(session=first["session"], pageview=first["pageview"],
                        first=False))
        self.assertEqual(Session.objects.count(), 1)
        self.assertEqual(PageView.objects.count(), 1)

    def test_an_unknown_session_id_starts_a_new_visit(self):
        self.post(batch(session=str(uuid.uuid4())))
        self.assertEqual(Session.objects.count(), 1)

    def test_unknown_event_kinds_are_dropped(self):
        self.post(batch(events=[{"k": "mine", "t": 1}, {"k": "click", "t": 2}]))
        self.assertEqual(Event.objects.count(), 1)

    def test_a_broken_body_is_refused_without_a_traceback(self):
        answer = self.client.post(self.url, data="not json",
                                  content_type="application/json")
        self.assertEqual(answer.status_code, 400)

    def test_a_list_instead_of_an_object_is_refused(self):
        answer = self.client.post(self.url, data="[1,2,3]",
                                  content_type="application/json")
        self.assertEqual(answer.status_code, 400)

    def test_a_get_is_not_allowed(self):
        self.assertEqual(self.client.get(self.url).status_code, 405)

    @override_settings(SIGHTLINE={"EXCLUDE_PATHS": ["/shop/"]})
    def test_an_excluded_path_is_not_recorded(self):
        answer = self.post(batch()).json()
        self.assertFalse(answer["ok"])
        self.assertEqual(Session.objects.count(), 0)

    @override_settings(SIGHTLINE={"MAX_BATCH": 1})
    def test_an_oversized_batch_is_trimmed_not_rejected(self):
        self.post(batch())
        self.assertEqual(Event.objects.count(), 1)

    def test_the_query_string_is_dropped_by_default(self):
        self.post(batch(url="/shop/?utm_source=x&page=2"))
        self.assertEqual(Page.objects.get().path, "/shop/")

    @override_settings(SIGHTLINE={"KEEP_QUERY_STRING": True})
    def test_it_can_be_kept(self):
        self.post(batch(url="/shop/?page=2"))
        self.assertEqual(Page.objects.get().path, "/shop/?page=2")


class RollupTests(TestCase):
    url = "/sightline/collect/"

    def post(self, payload):
        return self.client.post(self.url, data=json.dumps(payload),
                                content_type="application/json")

    def test_clicks_land_in_a_grid_cell(self):
        self.post(batch())
        cell = HeatCell.objects.get(kind="click")
        self.assertEqual(cell.count, 1)

    def test_the_same_cell_adds_up(self):
        first = self.post(batch()).json()
        self.post(batch(session=first["session"], pageview=first["pageview"],
                        first=False))
        self.assertEqual(HeatCell.objects.get(kind="click").count, 2)

    def test_element_clicks_are_counted(self):
        self.post(batch())
        row = ElementStat.objects.get(selector="#buy")
        self.assertEqual(row.clicks, 1)
        self.assertEqual(row.label, "Buy now")

    def test_rage_clicks_are_counted_separately(self):
        self.post(batch(events=[{"k": "rage", "t": 1, "xp": 0.5, "yp": 0.5,
                                 "sel": "#buy"}]))
        row = ElementStat.objects.get(selector="#buy")
        self.assertEqual(row.rage_clicks, 1)
        self.assertEqual(row.clicks, 0)

    def test_scroll_depth_credits_every_band_below_it(self):
        self.post(batch(maxScrollPct=50))
        self.assertEqual(ScrollBand.objects.count(), 10)

    def test_a_second_batch_does_not_credit_the_same_bands_again(self):
        first = self.post(batch(maxScrollPct=50)).json()
        self.post(batch(session=first["session"], pageview=first["pageview"],
                        first=False, maxScrollPct=50))
        for band in ScrollBand.objects.all():
            self.assertEqual(band.reached, 1)

    def test_scrolling_further_credits_only_the_new_bands(self):
        first = self.post(batch(maxScrollPct=50)).json()
        self.post(batch(session=first["session"], pageview=first["pageview"],
                        first=False, maxScrollPct=100))
        self.assertEqual(ScrollBand.objects.count(), 20)
        self.assertEqual(ScrollBand.objects.get(band=1).reached, 1)

    def test_page_views_are_counted_once_per_page_not_per_batch(self):
        first = self.post(batch()).json()
        self.post(batch(session=first["session"], pageview=first["pageview"],
                        first=False))
        self.assertEqual(Page.objects.get().view_count, 1)

    def test_signals_are_raised_on_the_session(self):
        self.post(batch(events=[{"k": "rage", "t": 1}, {"k": "error", "t": 2}]))
        session = Session.objects.get()
        self.assertTrue(session.has_rage)
        self.assertTrue(session.has_error)


class MiddlewareTests(TestCase):
    def test_the_tracker_is_injected_into_html(self):
        html = self.client.get("/").content.decode()
        self.assertIn("sightline/js/tracker.js", html)

    def test_it_goes_in_before_the_closing_body_tag(self):
        html = self.client.get("/").content.decode()
        self.assertLess(html.index("tracker.js"), html.index("</body>"))

    def test_the_config_travels_with_it(self):
        html = self.client.get("/").content.decode()
        self.assertIn("__sightline", html)
        self.assertIn("/sightline/collect/", html)

    def test_excluded_paths_carry_nothing(self):
        html = self.client.get("/sightline/collect/").content.decode()
        self.assertNotIn("tracker.js", html)

    def test_staff_are_not_recorded(self):
        staff = User.objects.create_user("boss", password="x", is_staff=True)
        self.client.force_login(staff)
        html = self.client.get("/").content.decode()
        self.assertNotIn("tracker.js", html)

    @override_settings(SIGHTLINE={"IGNORE_STAFF": False})
    def test_unless_you_ask_for_it(self):
        staff = User.objects.create_user("boss2", password="x", is_staff=True)
        self.client.force_login(staff)
        self.assertIn("tracker.js", self.client.get("/").content.decode())

    @override_settings(SIGHTLINE={"AUTO_INJECT": False})
    def test_injection_can_be_switched_off(self):
        self.assertNotIn("tracker.js", self.client.get("/").content.decode())

    @override_settings(SIGHTLINE={"RESPECT_DNT": True})
    def test_do_not_track_is_honoured(self):
        html = self.client.get("/", HTTP_DNT="1").content.decode()
        self.assertNotIn("tracker.js", html)

    def test_bots_are_not_recorded(self):
        html = self.client.get("/", HTTP_USER_AGENT="Googlebot/2.1").content.decode()
        self.assertNotIn("tracker.js", html)


class OverlayTests(TestCase):
    def setUp(self):
        self.page = Page.objects.create(path="/shop/")

    def test_a_visitor_cannot_open_the_overlay(self):
        html = self.client.get("/shop/?sightline=overlay").content.decode()
        self.assertNotIn("overlay.js", html)

    def test_staff_can(self):
        staff = User.objects.create_user("boss3", password="x", is_staff=True)
        self.client.force_login(staff)
        html = self.client.get(
            f"/shop/?sightline=overlay&sl_page={self.page.pk}").content.decode()
        self.assertIn("overlay.js", html)
        self.assertIn("__sightlineOverlay", html)

    def test_the_overlay_replaces_the_tracker_not_joins_it(self):
        staff = User.objects.create_user("boss4", password="x", is_staff=True)
        self.client.force_login(staff)
        html = self.client.get("/shop/?sightline=overlay").content.decode()
        self.assertNotIn("tracker.js", html)


class PanelTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user("boss5", password="x",
                                              is_staff=True, is_superuser=True)
        self.page = Page.objects.create(path="/shop/", view_count=3)
        self.session = Session.objects.create(visitor_key="abc",
                                              device=Device.DESKTOP)
        self.view = PageView.objects.create(session=self.session, page=self.page,
                                            viewport_width=1280,
                                            document_height=3000)

    def test_the_panel_is_closed_to_visitors(self):
        answer = self.client.get(reverse("sightline:dashboard"))
        self.assertEqual(answer.status_code, 302)

    def test_staff_see_it(self):
        self.client.force_login(self.staff)
        answer = self.client.get(reverse("sightline:dashboard"))
        self.assertEqual(answer.status_code, 200)
        self.assertContains(answer, "/shop/")

    def test_heat_data_is_closed_to_visitors(self):
        answer = self.client.get(reverse("sightline:heat_data"),
                                 {"page": self.page.pk})
        self.assertEqual(answer.status_code, 302)

    def test_heat_data_returns_cells(self):
        HeatCell.objects.create(page=self.page, day="2026-01-01",
                                device=Device.DESKTOP, kind="click",
                                col=10, row=20, count=5)
        self.client.force_login(self.staff)
        answer = self.client.get(reverse("sightline:heat_data"),
                                 {"page": self.page.pk, "days": 3650})
        data = answer.json()
        self.assertEqual(data["cells"], [[10, 20, 5]])
        self.assertEqual(data["peak"], 5)

    def test_heat_data_can_be_filtered_by_device(self):
        HeatCell.objects.create(page=self.page, day="2026-01-01",
                                device=Device.MOBILE, kind="click",
                                col=1, row=1, count=9)
        self.client.force_login(self.staff)
        answer = self.client.get(reverse("sightline:heat_data"),
                                 {"page": self.page.pk, "days": 3650,
                                  "device": "desktop"})
        self.assertEqual(answer.json()["cells"], [])

    def test_the_replay_page_needs_a_recorded_view(self):
        empty = Session.objects.create(visitor_key="none")
        self.client.force_login(self.staff)
        answer = self.client.get(reverse("sightline:replay", args=[empty.pk]))
        self.assertEqual(answer.status_code, 404)

    def test_replay_data_groups_events_by_page(self):
        Event.objects.create(pageview=self.view, kind="click", t_ms=100, x=5, y=6)
        self.client.force_login(self.staff)
        answer = self.client.get(reverse("sightline:replay_data",
                                         args=[self.session.pk]))
        data = answer.json()
        self.assertEqual(len(data["views"]), 1)
        self.assertEqual(data["views"][0]["events"][0][0], "click")

    def test_the_sidebar_entry_leads_to_the_panel(self):
        self.client.force_login(self.staff)
        answer = self.client.get("/admin/sightline/panel/")
        self.assertEqual(answer.status_code, 302)
        self.assertIn(reverse("sightline:dashboard"), answer["Location"])


class UtilTests(TestCase):
    def test_a_visitor_key_is_not_an_address(self):
        request = self.client.request().wsgi_request
        request.META["REMOTE_ADDR"] = "203.0.113.9"
        key = visitor_key(request)
        self.assertNotIn("203.0.113", key)
        self.assertEqual(len(key), 40)

    def test_the_same_visitor_gets_the_same_key_within_a_day(self):
        request = self.client.request().wsgi_request
        request.META["REMOTE_ADDR"] = "203.0.113.9"
        self.assertEqual(visitor_key(request), visitor_key(request))

    def test_the_key_changes_with_the_day(self):
        from datetime import date
        request = self.client.request().wsgi_request
        request.META["REMOTE_ADDR"] = "203.0.113.9"
        self.assertNotEqual(visitor_key(request, date(2026, 1, 1)),
                            visitor_key(request, date(2026, 1, 2)))

    def test_width_decides_the_device(self):
        self.assertEqual(device_of("", 390), Device.MOBILE)
        self.assertEqual(device_of("", 820), Device.TABLET)
        self.assertEqual(device_of("", 1440), Device.DESKTOP)

    def test_the_user_agent_decides_when_width_is_unknown(self):
        self.assertEqual(device_of("iPhone", 0), Device.MOBILE)
        self.assertEqual(device_of("iPad", 0), Device.TABLET)

    def test_known_crawlers_are_recognised(self):
        self.assertTrue(is_bot("Mozilla/5.0 (compatible; Googlebot/2.1)"))
        self.assertFalse(is_bot("Mozilla/5.0 (iPhone)"))

    def test_paths_are_capped(self):
        self.assertLessEqual(len(clean_path("/" + "a" * 900)), 500)


class OpenAnyPageTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user("boss6", password="x",
                                              is_staff=True, is_superuser=True)
        self.client.force_login(self.staff)

    def test_an_unknown_path_answers_with_an_empty_map(self):
        answer = self.client.get(reverse("sightline:heat_data"),
                                 {"path": "/never-visited/"})
        self.assertEqual(answer.status_code, 200)
        data = answer.json()
        self.assertEqual(data["cells"], [])
        self.assertEqual(data["views"], 0)

    def test_a_known_path_answers_with_its_numbers(self):
        page = Page.objects.create(path="/shop/")
        HeatCell.objects.create(page=page, day="2026-01-01",
                                device=Device.DESKTOP, kind="click",
                                col=3, row=4, count=2)
        answer = self.client.get(reverse("sightline:heat_data"),
                                 {"path": "/shop/", "days": 3650})
        self.assertEqual(answer.json()["cells"], [[3, 4, 2]])

    def test_no_page_and_no_path_is_still_not_an_error(self):
        answer = self.client.get(reverse("sightline:heat_data"))
        self.assertEqual(answer.status_code, 200)
        self.assertEqual(answer.json()["cells"], [])

    def test_the_overlay_carries_the_path_when_there_is_no_id(self):
        html = self.client.get("/shop/?sightline=overlay").content.decode()
        self.assertIn('"path": "/shop/"', html)

    def test_the_panel_offers_a_way_to_open_any_page(self):
        html = self.client.get(reverse("sightline:dashboard")).content.decode()
        self.assertIn('id="sl-open-path"', html)

    def test_the_empty_state_explains_why_it_is_empty(self):
        html = self.client.get(reverse("sightline:dashboard")).content.decode()
        self.assertIn("Your own visits are not recorded", html)
        self.assertIn("IGNORE_STAFF", html)

    def test_the_template_has_no_leaking_comments(self):
        html = self.client.get(reverse("sightline:dashboard")).content.decode()
        self.assertNotIn("{#", html)

    def test_the_tables_stack_on_a_phone(self):
        html = self.client.get(reverse("sightline:dashboard")).content.decode()
        self.assertIn("sl-table--stack", html)


class ReplayFrameTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user("boss7", password="x",
                                              is_staff=True, is_superuser=True)
        self.client.force_login(self.staff)
        self.page = Page.objects.create(path="/shop/")
        self.session = Session.objects.create(visitor_key="k", device=Device.MOBILE)
        self.view = PageView.objects.create(session=self.session, page=self.page,
                                            viewport_width=390, viewport_height=844,
                                            document_height=3000, duration_ms=8000)
        Event.objects.create(pageview=self.view, kind="click", t_ms=500,
                             x=100, y=400, scroll_y=0)

    def test_the_frame_is_not_pointed_at_a_url(self):
        html = self.client.get(reverse("sightline:replay",
                                       args=[self.session.pk])).content.decode()
        self.assertIn('id="sl-frame"', html)
        self.assertNotIn('id="sl-frame" src=', html)

    def test_the_recorded_viewport_travels_with_the_data(self):
        data = self.client.get(reverse("sightline:replay_data",
                                       args=[self.session.pk])).json()
        self.assertEqual(data["views"][0]["viewport"], [390, 844])

    def test_a_visit_with_no_pages_does_not_open(self):
        empty = Session.objects.create(visitor_key="none")
        answer = self.client.get(reverse("sightline:replay", args=[empty.pk]))
        self.assertEqual(answer.status_code, 404)

    def test_the_player_is_staff_only(self):
        self.client.logout()
        answer = self.client.get(reverse("sightline:replay", args=[self.session.pk]))
        self.assertEqual(answer.status_code, 302)


class IframeTests(TestCase):
    def test_the_tracker_refuses_to_run_outside_the_top_window(self):
        from django.contrib.staticfiles import finders
        path = finders.find("sightline/js/tracker.js")
        source = open(path, encoding="utf-8").read()
        self.assertIn("window.top !== window.self", source)

    def test_the_guard_comes_before_anything_is_recorded(self):
        from django.contrib.staticfiles import finders
        source = open(finders.find("sightline/js/tracker.js"), encoding="utf-8").read()
        self.assertLess(source.index("window.top !== window.self"),
                        source.index("addEventListener"))


class OverlayRecordingTests(TestCase):
    url = "/sightline/collect/"

    def post(self, payload):
        return self.client.post(self.url, data=json.dumps(payload),
                                content_type="application/json")

    def test_an_overlay_event_is_stored_with_its_state(self):
        self.post(batch(events=[
            {"k": "overlay", "t": 1200, "sel": "#gateBox", "lbl": "Sign in",
             "m": {"state": "open"}},
        ]))
        row = Event.objects.get(kind="overlay")
        self.assertEqual(row.selector, "#gateBox")
        self.assertEqual(row.meta, {"state": "open"})

    def test_closing_is_recorded_too(self):
        self.post(batch(events=[
            {"k": "overlay", "t": 1, "sel": "#x", "m": {"state": "open"}},
            {"k": "overlay", "t": 2, "sel": "#x", "m": {"state": "close"}},
        ]))
        states = [e.meta.get("state") for e in Event.objects.order_by("t_ms")]
        self.assertEqual(states, ["open", "close"])

    def test_overlays_stay_out_of_the_heatmap(self):
        self.post(batch(events=[
            {"k": "overlay", "t": 1, "sel": "#x", "m": {"state": "open"}},
        ]))
        self.assertFalse(HeatCell.objects.filter(kind="overlay").exists())

    def test_the_meta_travels_to_the_player(self):
        staff = User.objects.create_user("boss8", password="x",
                                         is_staff=True, is_superuser=True)
        answer = self.post(batch(events=[
            {"k": "overlay", "t": 900, "sel": "#gateBox", "lbl": "Sign in",
             "m": {"state": "open"}},
        ])).json()
        self.client.force_login(staff)
        data = self.client.get(reverse("sightline:replay_data",
                                       args=[answer["session"]])).json()
        row = data["views"][0]["events"][0]
        self.assertEqual(row[0], "overlay")
        self.assertEqual(row[5], "#gateBox")
        self.assertEqual(row[7], {"state": "open"})

    def test_the_tracker_watches_the_configured_selectors(self):
        from django.contrib.staticfiles import finders
        source = open(finders.find("sightline/js/tracker.js"), encoding="utf-8").read()
        self.assertIn("overlaySelectors", source)
        self.assertIn("scanOverlays", source)

    def test_the_selectors_reach_the_page(self):
        html = self.client.get("/").content.decode()
        self.assertIn("overlaySelectors", html)
        self.assertIn("dialog", html)

    def test_the_player_reopens_them(self):
        from django.contrib.staticfiles import finders
        source = open(finders.find("sightline/js/replay.js"), encoding="utf-8").read()
        self.assertIn("showModal", source)

    def test_the_player_says_so_when_a_popup_is_missing(self):
        from django.contrib.staticfiles import finders
        source = open(finders.find("sightline/js/replay.js"), encoding="utf-8").read()
        self.assertIn("Popup opened: ", source)


class OverlayNoiseTests(TestCase):
    def test_a_closed_overlay_is_not_announced_on_first_sight(self):
        from django.contrib.staticfiles import finders
        source = open(finders.find("sightline/js/tracker.js"), encoding="utf-8").read()
        self.assertIn("if (!now) { continue; }", source)


class VisitListTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(
            username="boss", password="x", is_staff=True, is_superuser=True)
        self.client.force_login(self.staff)
        self.shopper = User.objects.create_user(username="shopper", password="x")

    def _visit(self, **kw):
        return Session.objects.create(visitor_key="k" * 10, **kw)

    def test_it_lists_more_than_the_dashboard_does(self):
        for _ in range(60):
            self._visit()
        response = self.client.get(reverse("sightline:sessions"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["page"].object_list), 50)
        self.assertEqual(response.context["total"], 60)

    def test_an_old_visit_is_still_there(self):
        old = self._visit(started_at=timezone.now() - timedelta(days=400))
        response = self.client.get(reverse("sightline:sessions"))
        self.assertIn(old, response.context["page"].object_list)

    def test_it_can_show_only_people_it_knows(self):
        known = self._visit(user=self.shopper)
        self._visit()
        response = self.client.get(reverse("sightline:sessions"), {"signal": "known"})
        self.assertEqual(list(response.context["page"].object_list), [known])

    def test_it_can_be_searched_by_email(self):
        self.shopper.email = "aysel@example.com"
        self.shopper.save()
        mine = self._visit(user=self.shopper)
        self._visit()
        response = self.client.get(reverse("sightline:sessions"), {"q": "aysel"})
        self.assertEqual(list(response.context["page"].object_list), [mine])

    def test_it_is_staff_only(self):
        self.client.logout()
        response = self.client.get(reverse("sightline:sessions"))
        self.assertNotEqual(response.status_code, 200)


class SignInDuringAVisitTests(TestCase):
    def test_the_session_picks_up_the_account(self):
        person = User.objects.create_user(username="late", password="x")
        first = self.client.post(
            reverse("sightline:collect"),
            data=json.dumps({"path": "/", "events": []}),
            content_type="application/json")
        self.assertEqual(first.status_code, 200)
        session = Session.objects.get()
        self.assertIsNone(session.user_id)

        self.client.force_login(person)
        self.client.post(
            reverse("sightline:collect"),
            data=json.dumps({"session": str(session.pk),
                             "path": "/next/", "events": []}),
            content_type="application/json")
        session.refresh_from_db()
        self.assertEqual(session.user_id, person.pk)
        self.assertEqual(Session.objects.count(), 1)


class PruneKeepsVisitsTests(TestCase):
    def test_visits_survive_the_default_prune(self):
        old = timezone.now() - timedelta(days=400)
        session = Session.objects.create(visitor_key="k", started_at=old)
        page = Page.objects.create(path="/x/")
        view = PageView.objects.create(session=session, page=page, started_at=old)
        Event.objects.create(pageview=view, kind="click", x_pct=10, y_pct=10)

        call_command("sightline_prune", "--days", "1")
        self.assertTrue(Session.objects.filter(pk=session.pk).exists())
        self.assertEqual(Event.objects.count(), 0)

    def test_the_flag_removes_them(self):
        old = timezone.now() - timedelta(days=400)
        session = Session.objects.create(visitor_key="k", started_at=old)
        call_command("sightline_prune", "--days", "1", "--sessions")
        self.assertFalse(Session.objects.filter(pk=session.pk).exists())
