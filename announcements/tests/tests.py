import os
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from announcements import buttons, homepage
from bdh_sdk.speakers import AnnounceError

SPEAKERS = [("media_player.kitchen", "Kitchen (Sonos)"), ("media_player.echo_up", "Upstairs (Alexa)")]
ENV = {"BDH_ANNOUNCEMENTS_SPEAKERS": "media_player.kitchen,media_player.echo_up",
       "BDH_ANNOUNCEMENTS_VOLUME": "35", "BDH_ANNOUNCEMENTS_CHIME": "kalimba"}


def _fields(title="Dinner", message="Dinner's ready!", **kw):
    return buttons.clean(title, kw.get("icon", "utensils"), message,
                         kw.get("mode", "all"), kw.get("picked", []))


class ButtonStoreTests(TestCase):
    def test_add_update_move_delete(self):
        a = buttons.add(_fields())
        b = buttons.add(_fields("Car", "Time to go!", icon="car"))
        self.assertEqual([x["title"] for x in buttons.load()], ["Dinner", "Car"])
        buttons.move(b["id"], -1)
        self.assertEqual([x["title"] for x in buttons.load()], ["Car", "Dinner"])
        buttons.move(b["id"], -1)  # already first
        self.assertEqual(buttons.load()[0]["id"], b["id"])
        buttons.update(a["id"], _fields("Supper", "Supper time", mode="pick", picked=["media_player.kitchen"]))
        self.assertEqual(buttons.find(a["id"])["speakers"], ["media_player.kitchen"])
        buttons.delete(b["id"])
        self.assertEqual([x["title"] for x in buttons.load()], ["Supper"])

    def test_clean_rejects_bad_input(self):
        with self.assertRaises(ValueError):
            buttons.clean("", "car", "hi", "all", [])
        with self.assertRaises(ValueError):
            buttons.clean("x", "car", "   ", "all", [])
        with self.assertRaises(ValueError):
            buttons.clean("x", "car", "hi", "pick", [])
        self.assertEqual(buttons.clean("x", "<script>", "hi", "all", [])["icon"], buttons.DEFAULT_ICON)

    def test_button_limit(self):
        for n in range(buttons.MAX_BUTTONS):
            buttons.add(_fields(f"B{n}"))
        with self.assertRaises(ValueError):
            buttons.add(_fields("one too many"))


@patch.dict(os.environ, ENV)
class ShortcutTests(TestCase):
    def test_every_button_is_a_shortcut_in_order(self):
        a = buttons.add(_fields())
        b = buttons.add(_fields("Car", "Time to go!", icon="car"))
        sc = homepage.shortcuts()
        self.assertEqual([s.id for s in sc], [a["id"], b["id"]])
        self.assertEqual(sc[1].icon, "fa-solid fa-car")
        self.assertLess(sc[0].order, sc[1].order)
        self.assertIn("guest", sc[0].modes)

    @patch("bdh_sdk.speakers.announce", return_value=[])
    def test_run_plays_on_all_speakers(self, announce):
        a = buttons.add(_fields())
        self.assertEqual(homepage.run_shortcut(a["id"]), "Announced on 2 speakers")
        announce.assert_called_once_with("Dinner's ready!", ["media_player.kitchen", "media_player.echo_up"],
                                         volume=35, chime="kalimba", voice=buttons.VOICE)

    @patch("bdh_sdk.speakers.announce", return_value=["media_player.echo_up"])
    def test_run_reports_failures_and_uses_own_speakers(self, announce):
        a = buttons.add(_fields(mode="pick", picked=["media_player.kitchen", "media_player.echo_up"]))
        self.assertEqual(homepage.run_shortcut(a["id"]), "Announced on 1 speaker, 1 didn't respond")

    @patch("bdh_sdk.speakers.announce")
    def test_run_without_speakers_fails_clearly(self, announce):
        a = buttons.add(_fields())
        with patch.dict(os.environ, {"BDH_ANNOUNCEMENTS_SPEAKERS": ""}):
            with self.assertRaises(AnnounceError):
                homepage.run_shortcut(a["id"])
        announce.assert_not_called()

    @patch("bdh_sdk.speakers.announce", return_value=[])
    def test_no_chime(self, announce):
        a = buttons.add(_fields())
        with patch.dict(os.environ, {"BDH_ANNOUNCEMENTS_CHIME": "none"}):
            homepage.run_shortcut(a["id"])
        self.assertIsNone(announce.call_args.kwargs["chime"])

    def test_unknown_shortcut(self):
        with self.assertRaises(LookupError):
            homepage.run_shortcut("nope")


@patch.dict(os.environ, ENV)
@patch("bdh_sdk.speakers.list_speakers", return_value=SPEAKERS)
class ButtonsPageTests(TestCase):
    def setUp(self):
        self.url = reverse("announcements_buttons")
        self.admin = get_user_model().objects.create_user("owner", password="x", is_staff=True)

    def test_admin_only(self, _ls):
        self.assertEqual(self.client.get(self.url).status_code, 404)
        get_user_model().objects.create_user("kid", password="x")
        self.client.login(username="kid", password="x")
        self.assertEqual(self.client.get(self.url).status_code, 404)

    def test_add_edit_reorder_delete(self, _ls):
        self.client.force_login(self.admin)
        r = self.client.post(self.url, {"action": "add", "title": "Dinner", "icon": "utensils",
                                        "message": "Dinner's ready!", "play_on": "all"}, follow=True)
        self.assertContains(r, "Added Dinner.")
        self.assertContains(r, "Kitchen (Sonos)")
        self.client.post(self.url, {"action": "add", "title": "Car", "icon": "car",
                                    "message": "Car's leaving", "play_on": "pick",
                                    "speakers": ["media_player.echo_up"]})
        dinner, car = buttons.load()
        self.assertEqual(car["speakers"], ["media_player.echo_up"])
        r = self.client.get(self.url)
        self.assertContains(r, "Upstairs")  # "where" summary for the Car button

        self.client.post(self.url, {"action": "save", "id": dinner["id"], "title": "Supper",
                                    "icon": "bell", "message": "Supper!", "play_on": "all"})
        self.assertEqual(buttons.find(dinner["id"])["title"], "Supper")
        self.client.post(self.url, {"action": "down", "id": dinner["id"]})
        self.assertEqual([b["id"] for b in buttons.load()], [car["id"], dinner["id"]])
        r = self.client.post(self.url, {"action": "delete", "id": car["id"]}, follow=True)
        self.assertContains(r, "Removed Car.")
        self.assertEqual(len(buttons.load()), 1)

    def test_bad_add_keeps_the_form(self, _ls):
        self.client.force_login(self.admin)
        r = self.client.post(self.url, {"action": "add", "title": "Dinner", "icon": "utensils",
                                        "message": "", "play_on": "all"})
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "needs something to say")
        self.assertContains(r, 'value="Dinner"')
        self.assertEqual(buttons.load(), [])

    @patch("bdh_sdk.speakers.announce", return_value=[])
    def test_test_button_plays_the_form(self, announce, _ls):
        self.client.force_login(self.admin)
        b = buttons.add(_fields())
        r = self.client.post(self.url, {"action": "test", "id": b["id"], "title": "Dinner", "icon": "utensils",
                                        "message": "Edited text", "play_on": "all"}, follow=True)
        self.assertContains(r, "Dinner: Announced on 2 speakers.")
        self.assertEqual(announce.call_args.args[0], "Edited text")
        self.assertEqual(buttons.find(b["id"])["message"], "Dinner's ready!")

    @patch("bdh_sdk.speakers.announce", side_effect=AnnounceError("Home Assistant is unreachable"))
    def test_test_failure_is_shown(self, _announce, _ls):
        self.client.force_login(self.admin)
        b = buttons.add(_fields())
        r = self.client.post(self.url, {"action": "test", "id": b["id"]}, follow=True)
        self.assertContains(r, "Couldn&#x27;t play Dinner: Home Assistant is unreachable")

    def test_page_survives_ha_down(self, ls):
        ls.side_effect = RuntimeError("down")
        self.client.force_login(self.admin)
        buttons.add(_fields(mode="pick", picked=["media_player.kitchen"]))
        r = self.client.get(self.url)
        self.assertContains(r, "Couldn&#x27;t reach Home Assistant")
