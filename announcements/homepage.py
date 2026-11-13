from bdh_sdk import ALL_MODES, Shortcut

from . import buttons


def shortcuts():
    return [
        Shortcut(id=b["id"], title=b["title"], icon=f"fa-solid fa-{b['icon']}",
                 order=50 + n, modes=ALL_MODES)
        for n, b in enumerate(buttons.load())
    ]


def run_shortcut(shortcut_id):
    button = buttons.find(shortcut_id)
    if button is None:
        raise LookupError(f"no announcement button {shortcut_id!r}")
    return buttons.play(button)
