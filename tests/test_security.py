###############
# Qiyas Sadıqov CC
###############

import json
import re
from datetime import timedelta
from io import StringIO
from pathlib import Path

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.management import call_command
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from sightline.models import (Device, ElementStat, Event, HeatCell, Page,
                              PageView, ScrollBand, Session)
from sightline.utils import client_ip, is_safe_path, overlay_link

User = get_user_model()
STATIC = Path(__file__).resolve().parent.parent / "src" / "sightline" / "static"
COLLECT = "/sightline/collect/"


def batch(**extra):
    payload = {
        "url": "/shop/", "title": "Shop", "viewportWidth": 1280,
        "viewportHeight": 800, "documentHeight": 4000, "maxScrollPct": 50,
        "durationMs": 4200, "first": True,
        "events": [{"k": "click", "t": 900, "x": 1, "y": 1, "xp": 0.5,
                    "yp": 0.1, "sel": "#buy", "lbl": "Buy"}],
    }
    payload.update(extra)
    return payload


def post(client, payload, **extra):
    return client.post(COLLECT, data=json.dumps(payload),
                       content_type="application/json", **extra)


def settings_with(**values):
    from django.conf import settings
    return override_settings(SIGHTLINE={**settings.SIGHTLINE, **values})


class ReplayScriptTests(TestCase):
    source = (STATIC / "sightline" / "js" / "replay.js").read_text()

    def test_the_step_list_is_built_without_html(self):
        self.assertNotIn("innerHTML", self.source)
        self.assertIn("label.textContent = String(row.path)", self.source)

    def test_no_script_writes_recorded_text_as_html(self):
        for name in ("replay.js", "overlay.js", "tracker.js"):
            text = (STATIC / "sightline" / "js" / name).read_text()
            for line in text.splitlines():
                if "innerHTML" in line:
                    self.assertRegex(line, r'innerHTML = (""|\[)', name)
            self.assertNotIn("insertAdjacentHTML", text)
            self.assertNotIn("outerHTML", text)

    def test_the_player_only_fetches_this_site(self):
        self.assertIn("function sameSite(path)", self.source)
        self.assertIn("var path = sameSite(given);", self.source)

    def test_templates_mark_nothing_safe_but_escaped_json(self):
        root = STATIC.parent / "templates" / "sightline"
        for template in root.glob("*.html"):
            for hit in re.findall(r"\{\{[^}]*\|safe[^}]*\}\}", template.read_text()):
                self.assertEqual(hit, "{{ config|safe }}", template.name)


class PathValidationTests(TestCase):
    def test_safe_paths(self):
        for path in ("/", "/shop/", "/a-b_c.d~e/%20/x:y@z", "/p/1,2;3=4&5"):
            self.assertTrue(is_safe_path(path), path)

    def test_unsafe_paths(self):
        for path in ("", "shop/", "//evil.com/", "/\\evil.com/",
                     '/<img src=x onerror=alert(1)>', '/"onmouseover=x', "/a b",
                     "/\nx", "javascript:alert(1)"):
            self.assertFalse(is_safe_path(path), path)

    def test_a_script_path_is_refused_at_ingest(self):
        answer = post(self.client, batch(url="/<img src=x onerror=alert(1)>"))
        self.assertEqual(answer.status_code, 400)
        self.assertEqual(answer.json()["reason"], "bad_path")
        self.assertFalse(Page.objects.exists())
        self.assertFalse(Session.objects.exists())

    def test_a_backslash_path_is_refused(self):
        answer = post(self.client, batch(url="/\\evil.com/"))
        self.assertEqual(answer.status_code, 400)
        self.assertFalse(Page.objects.exists())

    def test_a_full_url_keeps_only_its_path(self):
        post(self.client, batch(url="//evil.com/shop/"))
        self.assertEqual(list(Page.objects.values_list("path", flat=True)), ["/shop/"])

    def test_paths_with_no_view_make_no_page(self):
        answer = post(self.client, batch(url="/made-up-by-a-bot/"))
        self.assertEqual(answer.json()["reason"], "unknown_path")
        self.assertFalse(Page.objects.exists())

    def test_the_check_can_be_switched_off(self):
        with settings_with(RESOLVE_PATHS=False):
            post(self.client, batch(url="/made-up-by-a-bot/"))
        self.assertTrue(Page.objects.filter(path="/made-up-by-a-bot/").exists())

    def test_an_existing_title_is_not_overwritten(self):
        Page.objects.create(path="/shop/", title="Shop")
        post(self.client, batch(title="Hacked"))
        self.assertEqual(Page.objects.get(path="/shop/").title, "Shop")

    def test_an_empty_title_is_filled(self):
        Page.objects.create(path="/shop/", title="")
        post(self.client, batch(title="Shop"))
        self.assertEqual(Page.objects.get(path="/shop/").title, "Shop")

    def test_overlay_links_stay_on_the_site(self):
        self.assertEqual(overlay_link("//evil.com/"), "")
        self.assertEqual(overlay_link("/\\evil.com/"), "")
        self.assertTrue(overlay_link("/shop/", sl_page=1).startswith("/shop/?"))

    def test_the_panel_does_not_link_a_stored_bad_path(self):
        staff = User.objects.create_superuser("root", "r@x.io", "x")
        self.client.force_login(staff)
        page = Page.objects.create(path="//evil.com/")
        session = Session.objects.create(visitor_key="k")
        PageView.objects.create(session=session, page=page)
        html = self.client.get(reverse("sightline:dashboard")).content.decode()
        self.assertNotIn('href="//evil.com/', html)
        admin_html = self.client.get("/admin/sightline/page/").content.decode()
        self.assertNotIn('href="//evil.com/', admin_html)


class OverlayConfigTests(TestCase):
    def test_the_overlay_config_cannot_close_its_script(self):
        staff = User.objects.create_superuser("root", "r@x.io", "x")
        self.client.force_login(staff)
        html = self.client.get(
            "/shop/", {"sightline": "overlay",
                       "sl_path": "</script><script>alert(1)</script>"}).content.decode()
        self.assertNotIn("<script>alert(1)", html)
        self.assertIn("\\u003C/script\\u003E", html)


class ThrottleTests(TestCase):
    def test_too_many_batches_from_one_address_get_429(self):
        with settings_with(THROTTLE_BATCHES=3):
            codes = [post(self.client, batch()).status_code for _ in range(5)]
        self.assertEqual(codes, [200, 200, 200, 429, 429])

    def test_other_addresses_are_not_affected(self):
        with settings_with(THROTTLE_BATCHES=1):
            post(self.client, batch(), REMOTE_ADDR="10.0.0.1")
            self.assertEqual(post(self.client, batch(),
                                  REMOTE_ADDR="10.0.0.1").status_code, 429)
            self.assertEqual(post(self.client, batch(),
                                  REMOTE_ADDR="10.0.0.2").status_code, 200)

    def test_new_visits_per_address_are_capped(self):
        with settings_with(THROTTLE_SESSIONS=2):
            codes = [post(self.client, batch()).status_code for _ in range(3)]
        self.assertEqual(codes, [200, 200, 429])
        self.assertEqual(Session.objects.count(), 2)

    def test_a_running_visit_is_not_a_new_one(self):
        with settings_with(THROTTLE_SESSIONS=1):
            first = post(self.client, batch()).json()
            again = post(self.client, batch(session=first["session"],
                                            pageview=first["pageview"], first=False))
        self.assertEqual(again.status_code, 200)

    def test_throttling_can_be_switched_off(self):
        with settings_with(THROTTLE_BATCHES=0, THROTTLE_SESSIONS=0):
            codes = {post(self.client, batch()).status_code for _ in range(5)}
        self.assertEqual(codes, {200})

    def test_events_per_visit_are_capped(self):
        events = [{"k": "move", "t": i, "xp": 0.1, "yp": 0.1} for i in range(8)]
        with settings_with(MAX_EVENTS_PER_SESSION=10):
            first = post(self.client, batch(events=events)).json()
            post(self.client, batch(session=first["session"], events=events, first=False))
            full = post(self.client, batch(session=first["session"], events=events,
                                           first=False)).json()
        self.assertEqual(Event.objects.count(), 10)
        self.assertEqual(full["reason"], "session_full")

    def test_large_meta_is_dropped(self):
        events = [{"k": "custom", "t": 1, "m": {"blob": "x" * 5000}},
                  {"k": "custom", "t": 2, "m": {"plan": "pro"}}]
        post(self.client, batch(events=events))
        metas = list(Event.objects.order_by("t_ms").values_list("meta", flat=True))
        self.assertEqual(metas, [{}, {"plan": "pro"}])


class PermissionTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user("plain", password="x", is_staff=True)
        page = Page.objects.create(path="/shop/")
        self.session = Session.objects.create(visitor_key="k")
        PageView.objects.create(session=self.session, page=page)

    def urls(self):
        return [reverse("sightline:dashboard"), reverse("sightline:sessions"),
                reverse("sightline:heat_data"),
                reverse("sightline:replay", args=[self.session.pk]),
                reverse("sightline:replay_data", args=[self.session.pk])]

    def test_staff_without_the_permission_get_403(self):
        self.client.force_login(self.staff)
        for url in self.urls():
            self.assertEqual(self.client.get(url).status_code, 403, url)

    def test_visitors_are_sent_to_the_login(self):
        for url in self.urls():
            self.assertEqual(self.client.get(url).status_code, 302, url)

    def test_staff_with_the_permission_get_in(self):
        self.staff.user_permissions.add(Permission.objects.get(
            codename="view_session", content_type__app_label="sightline"))
        self.client.force_login(self.staff)
        for url in self.urls():
            self.assertEqual(self.client.get(url).status_code, 200, url)

    def test_staff_without_the_permission_get_no_overlay(self):
        self.client.force_login(self.staff)
        html = self.client.get("/shop/?sightline=overlay").content.decode()
        self.assertNotIn("overlay.js", html)

    def test_the_permission_is_configurable(self):
        self.client.force_login(self.staff)
        with settings_with(PERMISSION=None):
            answer = self.client.get(reverse("sightline:dashboard"))
        self.assertEqual(answer.status_code, 200)


class PruneRollupTests(TestCase):
    def setUp(self):
        self.old_day = timezone.localdate() - timedelta(days=400)
        self.new_day = timezone.localdate()
        self.page = Page.objects.create(path="/shop/")
        self.gone = Page.objects.create(
            path="/gone/", last_seen_at=timezone.now() - timedelta(days=400))
        for page, day in ((self.page, self.old_day), (self.page, self.new_day),
                          (self.gone, self.old_day)):
            HeatCell.objects.create(page=page, day=day, device=Device.DESKTOP,
                                    kind="click", col=1, row=1, count=1)
            ScrollBand.objects.create(page=page, day=day, device=Device.DESKTOP,
                                      band=1, reached=1)
            ElementStat.objects.create(page=page, day=day, selector="#x", clicks=1)

    def test_old_rollups_and_empty_pages_go(self):
        call_command("sightline_prune", stdout=StringIO())
        self.assertEqual(HeatCell.objects.count(), 1)
        self.assertEqual(ScrollBand.objects.count(), 1)
        self.assertEqual(ElementStat.objects.count(), 1)
        self.assertEqual(list(Page.objects.values_list("path", flat=True)), ["/shop/"])

    def test_a_page_with_a_visit_stays(self):
        PageView.objects.create(session=Session.objects.create(visitor_key="k"),
                                page=self.gone)
        call_command("sightline_prune", stdout=StringIO())
        self.assertTrue(Page.objects.filter(path="/gone/").exists())

    def test_dry_run_deletes_nothing(self):
        out = StringIO()
        call_command("sightline_prune", "--dry-run", stdout=out)
        self.assertEqual(HeatCell.objects.count(), 3)
        self.assertIn("2 heat cells", out.getvalue())
        self.assertIn("1 pages", out.getvalue())

    def test_rollups_can_be_kept_forever(self):
        with settings_with(ROLLUP_RETAIN_DAYS=0):
            call_command("sightline_prune", stdout=StringIO())
        self.assertEqual(HeatCell.objects.count(), 3)
        self.assertEqual(Page.objects.count(), 2)


class ClientIpTests(TestCase):
    def request(self, **meta):
        return RequestFactory().get("/", REMOTE_ADDR="10.0.0.9", **meta)

    def test_forwarded_headers_are_ignored_by_default(self):
        req = self.request(HTTP_X_FORWARDED_FOR="1.2.3.4", HTTP_X_REAL_IP="5.6.7.8")
        self.assertEqual(client_ip(req), "10.0.0.9")

    def test_x_real_ip_when_trusted(self):
        req = self.request(HTTP_X_REAL_IP="5.6.7.8")
        with settings_with(IP_SOURCE="x-real-ip"):
            self.assertEqual(client_ip(req), "5.6.7.8")

    def test_last_forwarded_hop_when_trusted(self):
        req = self.request(HTTP_X_FORWARDED_FOR="1.1.1.1, 2.2.2.2")
        with settings_with(IP_SOURCE="xff-last"):
            self.assertEqual(client_ip(req), "2.2.2.2")

    def test_a_garbage_header_falls_back_to_the_socket(self):
        req = self.request(HTTP_X_REAL_IP="not-an-ip")
        with settings_with(IP_SOURCE="x-real-ip"):
            self.assertEqual(client_ip(req), "10.0.0.9")
