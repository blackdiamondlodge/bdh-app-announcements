import logging

from bdh_sdk.auth import is_admin
from django.http import Http404
from django.shortcuts import redirect, render

from . import buttons

log = logging.getLogger(__name__)
NOTE = "announcements_note"
OPEN = "announcements_open"


def _admin_only(view):
    def wrapped(request, *args, **kwargs):
        if not is_admin(request):
            raise Http404()
        return view(request, *args, **kwargs)
    wrapped.__name__ = view.__name__
    return wrapped


def _speakers():
    from bdh_sdk import speakers as sp

    try:
        return list(sp.list_speakers()), ""
    except Exception as exc:  # HA down or not configured
        log.warning("couldn't list speakers: %s", exc)
        return [], "Couldn't reach Home Assistant to list speakers."


def _fields(post):
    return buttons.clean(post.get("title"), post.get("icon"), post.get("message"),
                         post.get("play_on"), post.getlist("speakers"))


def _handle(request):
    """Run a POSTed action; returns (note, id of the button to keep open)."""
    action = request.POST.get("action")
    button_id = request.POST.get("id", "")
    if action == "add":
        b = buttons.add(_fields(request.POST))
        return ("ok", f"Added {b['title']}."), b["id"]
    button = buttons.find(button_id)
    if button is None:
        return ("bad", "That button no longer exists."), None
    if action == "save":
        b = buttons.update(button_id, _fields(request.POST))
        return ("ok", f"Saved {b['title']}."), b["id"]
    if action == "test":
        try:
            b = {**button, **_fields(request.POST)}
        except ValueError:
            b = button
        try:
            return ("ok", f"{b['title']}: {buttons.play(b)}."), button_id
        except Exception as exc:
            log.warning("test announce failed: %s", exc)
            return ("bad", f"Couldn't play {b['title']}: {exc}"), button_id
    if action == "delete":
        buttons.delete(button_id)
        return ("ok", f"Removed {button['title']}."), None
    if action in ("up", "down"):
        buttons.move(button_id, -1 if action == "up" else 1)
        return None, None
    return ("bad", "Unknown action."), None


@_admin_only
def buttons_page(request):
    add_open, form, open_id = False, None, None
    if request.method == "POST":
        try:
            note, open_id = _handle(request)
        except ValueError as exc:
            note, open_id = ("bad", str(exc)), request.POST.get("id") or None
            if request.POST.get("action") == "add":
                # Re-render so the half-filled form isn't lost.
                add_open = True
                p = request.POST
                form = {"title": p.get("title", ""), "icon": p.get("icon") or buttons.DEFAULT_ICON,
                        "message": p.get("message", ""), "play_on": p.get("play_on", "all"),
                        "chosen": p.getlist("speakers")}
        if not add_open:
            request.session[NOTE] = note
            request.session[OPEN] = open_id
            return redirect("announcements_buttons")
    else:
        open_id = request.session.pop(OPEN, None)
        note = request.session.pop(NOTE, None)

    speakers, speakers_error = _speakers()
    names = dict(speakers)
    rows = []
    for b in buttons.load():
        chosen = b.get("speakers") or []
        rows.append({
            **b,
            "chosen": chosen,
            "play_on": "pick" if chosen else "all",
            "where": ", ".join(names.get(s, s).split(" (")[0] for s in chosen) or "All speakers",
        })
    return render(request, "announcements/settings_buttons.html", {
        "buttons": rows,
        "speakers": speakers,
        "speakers_error": speakers_error,
        "icons": buttons.ICONS,
        "default_icon": buttons.DEFAULT_ICON,
        "note": note,
        "open_id": open_id,
        "add_open": add_open,
        "draft": form or {"icon": buttons.DEFAULT_ICON, "play_on": "all", "chosen": []},
        "chime": buttons.chime(),
        "can_add": len(rows) < buttons.MAX_BUTTONS,
        "all_count": len(buttons.all_speakers()),
    })
