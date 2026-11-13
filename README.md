# bdh-app-announcements

Black Diamond Hub app: one-tap spoken announcements ("Dinner's ready!") on the
house's Sonos and Alexa speakers. Installed into the hub through the
`blackdiamondhub.plugins` entry point (see
[bdh-sdk](https://github.com/blackdiamondlodge/bdh-sdk)).

The app has no tile. Each button set up under **Settings › Announcements ›
Buttons** becomes a homepage quick action. Tapping it plays the chosen chime,
then speaks the button's message on its speakers through `bdh_sdk.speakers`.
Sonos plays the chime and uses the set volume. Alexa uses its own announcement
tone and volume.

Settings:

- **Volume**: the Sonos announcement volume. Speakers return to their own
  volume afterwards.
- **Chime**: one of `bdh_sdk.alerts.CHIMES`, or none.
- **Speakers used for "All speakers"**: Sonos and Alexa players found in Home
  Assistant.

## Development

CI (`.github/workflows/ci.yml`) uses the reusable `app-ci.yml` from
bdh-sdk. It builds the wheel, installs it next to the hub, then runs
`hub_smoke`, the app tests and the selenium tests.

To release, bump `version` in `pyproject.toml`. When that lands on
`main`, `release.yml` tags it and publishes the wheel, and the release
notes include the hashed line for the hub's `sites/<site>/apps.txt`.
