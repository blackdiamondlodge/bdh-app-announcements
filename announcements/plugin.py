from bdh_sdk import PluginSpec, Setting, SettingsPage
from bdh_sdk.alerts import CHIMES
from bdh_sdk.plugins import CHOICE, INT, MULTI

CHIME_CHOICES = (("none", "No chime"),) + tuple(
    (c, c.replace("-", " ").capitalize()) for c in CHIMES)

spec = PluginSpec(
    id="announcements",
    app="announcements",
    urls="announcements.urls",
    shortcuts="announcements.homepage.shortcuts",
    run_shortcut="announcements.homepage.run_shortcut",
    settings=(
        Setting("speakers", 'Speakers used for "All speakers"', type=MULTI, default=None,
                choices_from="bdh_sdk.speakers.list_speakers",
                help="Sonos and Alexa speakers found in Home Assistant."),
        Setting("volume", "Volume", type=INT, default=50, minimum=0, maximum=100, unit="%",
                help="Sonos only. Speakers return to their own volume afterwards."),
        Setting("chime", "Chime", type=CHOICE, default="westminster", choices=CHIME_CHOICES,
                help="Played before the voice on Sonos. Alexa always uses its own tone."),
    ),
    settings_pages=(
        SettingsPage("Buttons", "announcements_buttons",
                     subtitle="The messages shown as quick actions",
                     icon="fas fa-bullhorn"),
    ),
)
