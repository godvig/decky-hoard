"""Which entries count as games. Shortcuts here are synthetic, modelled on common setups."""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import classify

LAUNCHERS = "/home/user/Emulation/tools/launchers"
FLATPAK = "/usr/bin/flatpak"


@pytest.mark.parametrize("program, options, source, kind", [
    # EmuDeck: the emulator on its own, and a ROM through it, even one whose file has gone.
    (f"{LAUNCHERS}/retroarch.sh", "", "unknown", "emulator"),
    (f"{LAUNCHERS}/pcsx2-qt.sh", '-batch "/home/user/Emulation/roms/ps2/Game.iso"', "unknown", "game"),
    (f"{LAUNCHERS}/dolphin-emu.sh", '"/home/user/Emulation/roms/gc/Game.rvz"', "rom", "game"),
    # Flatpaks: emulators, launchers and apps, unless they only run a game.
    (FLATPAK, "run --command=/app/bin/dolphin-emu org.DolphinEmu.dolphin-emu", "flatpak", "emulator"),
    (FLATPAK, "run com.heroicgameslauncher.hgl", "flatpak", "app"),
    (FLATPAK, "run org.prismlauncher.PrismLauncher", "flatpak", "app"),
    (FLATPAK, "run net.ankiweb.Anki", "flatpak", "app"),
    (FLATPAK, "run org.chessmd.chessmd", "flatpak", "app"),
    (FLATPAK, "run --command=bottles-cli com.usebottles.bottles run -b 'Game'", "folder", "game"),
    (FLATPAK, 'run com.heroicgameslauncher.hgl "heroic://launch/legendary/abc"', "heroic", "game"),
    (FLATPAK, "run org.example.SomeGame", "flatpak", "game"),
    # Browser pages, programs on the system, installers and launchers.
    (FLATPAK, "run org.mozilla.firefox --kiosk https://example.com", "web", "app"),
    ("claude-desktop", "", "unknown", "app"),
    ("/home/user/Downloads/Repack/setup.exe", "", "unknown", "app"),
    ("/home/user/Downloads/Game/Install.exe", "", "folder", "app"),
    ("/home/user/Applications/EmuDeck.AppImage", "", "file", "app"),
    ("/home/user/Games/PolyMC/polymc.exe", "", "file", "app"),
    # Games found on disk.
    ("/home/user/Games/Indie/indie.exe", "", "folder", "game"),
    ("/home/user/Games/ModOrganizer2/game/launch-mo2.sh", "", "mod-organizer", "game"),
])
def test_shortcut_kind(program, options, source, kind):
    assert classify.shortcut_kind(program, options, source) == (kind, False)


def test_shortcut_nothing_explains_is_a_flagged_game():
    assert classify.shortcut_kind("/opt/thing/run", "", "unknown") == ("game", True)


@pytest.mark.parametrize("name, app_type, result", [
    ("Proton 10.0", 4, ("tool", False)),
    ("Some Game", 1, ("game", False)),
    # Steam's type wins over the name.
    ("Proton Quest", 1, ("game", False)),
    # Before the frontend has reported Steam's types, names stand in for the known tools.
    ("Proton Experimental", None, ("tool", False)),
    ("Steam Linux Runtime 3.0 (sniper)", None, ("tool", False)),
    ("Steamworks Common Redistributables", None, ("tool", False)),
    ("Some Game", None, ("game", True)),
])
def test_steam_kind(name, app_type, result):
    assert classify.steam_kind(name, app_type) == result


CACHE = {
    "sizes": {
        "3000000001": {"name": "Indie", "bytes": 10, "kind": "game", "guessed": False},
        "3000000002": {"name": "Emulator", "bytes": 5, "kind": "emulator", "guessed": False},
        "3000000003": {"name": "Odd", "bytes": 1, "kind": "game", "guessed": True},
    },
    "unsized": {"3000000004": {"name": "Broken ROM", "kind": "game", "guessed": False}},
    "steam": {"10": {"name": "Game", "base": 100, "mods": 0}, "20": {"name": "Proton 9.0", "base": 50, "mods": 0}},
    "total_bytes": 16,
}


def test_counts_take_only_games():
    result = classify.apply_kinds(CACHE, {"10": 1, "20": 4}, {})
    assert result["counts"] == {"shortcut_games": 3, "sized_shortcut_games": 2, "guessed": 1}
    assert result["steam"]["20"]["kind"] == "tool"
    # Disk totals still take everything.
    assert result["total_bytes"] == 16


def test_override_wins_and_clears_the_flag():
    result = classify.apply_kinds(CACHE, {"10": 1}, {"3000000003": "app", "3000000002": "game", "10": "tool"})
    assert result["counts"] == {"shortcut_games": 3, "sized_shortcut_games": 2, "guessed": 0}
    assert (result["sizes"]["3000000003"]["kind"], result["sizes"]["3000000003"]["guessed"]) == ("app", False)
    assert result["steam"]["10"]["kind"] == "tool"


def test_unknown_override_is_ignored():
    result = classify.apply_kinds(CACHE, {}, {"3000000002": "toaster"})
    assert result["sizes"]["3000000002"]["kind"] == "emulator"


def test_apply_kinds_leaves_the_cache_alone():
    classify.apply_kinds(CACHE, {"20": 4}, {"3000000001": "app"})
    assert CACHE["sizes"]["3000000001"]["kind"] == "game"
    assert "kind" not in CACHE["steam"]["20"]


def test_biggest_games_skip_non_games_and_shortcuts_into_steam_games():
    cache = {
        "sizes": {
            "3000000001": {"name": "Big ROM", "bytes": 300, "base": 300, "mods": 0, "source": "rom", "kind": "game"},
            "3000000002": {"name": "Launcher", "bytes": 900, "base": 900, "mods": 0, "source": "flatpak", "kind": "app"},
            "3000000003": {"name": "Alt launcher", "bytes": 500, "base": 400, "mods": 100, "source": "steam-game",
                           "kind": "game"},
        },
        "unsized": {},
        "steam": {"10": {"name": "Modded", "base": 400, "mods": 100}, "20": {"name": "Proton 9.0", "base": 999, "mods": 0}},
    }
    result = classify.apply_kinds(cache, {"10": 1, "20": 4}, {})
    assert [(g["name"], g["bytes"], g["source"]) for g in result["biggest"]] == [
        ("Modded", 500, "steam"), ("Big ROM", 300, "rom")]
    assert len(classify.biggest_games(result, limit=1)) == 1


def test_entries_put_what_needs_a_look_first():
    result = classify.apply_kinds(CACHE, {"10": 1, "20": 4}, {})
    assert [(e["name"], e["review"]) for e in result["entries"]] == [
        ("Emulator", True), ("Odd", True), ("Proton 9.0", True),
        ("Broken ROM", False), ("Game", False), ("Indie", False)]


def test_not_played_counts_only_games_on_disk_and_never_guesses():
    month = classify.SECONDS_PER_MONTH
    now = 100 * month
    cache = {
        "sizes": {
            "3000000001": {"name": "Old ROM", "bytes": 300, "base": 300, "mods": 0, "source": "rom", "kind": "game"},
            "3000000002": {"name": "Old app", "bytes": 900, "base": 900, "mods": 0, "source": "flatpak", "kind": "app"},
            "3000000003": {"name": "Other account", "bytes": 50, "base": 50, "mods": 0, "source": "heroic",
                           "kind": "game"},
        },
        "unsized": {"3000000004": {"name": "Broken", "kind": "game"}},
        "steam": {"10": {"name": "Modded", "base": 400, "mods": 100}},
    }
    times = {"3000000001": int(now - 7 * month), "3000000002": int(now - 7 * month), "10": int(now - 6.5 * month)}
    result = classify.apply_kinds(cache, {"10": 1}, {}, times, now, 6)
    found = result["not_played"]
    assert [(g["name"], g["bytes"]) for g in found["games"]] == [("Modded", 500), ("Old ROM", 300)]
    assert found["bytes"] == 800
    # No time at all, as for a shortcut from another Steam account: unknown, not old.
    assert [g["name"] for g in found["unknown"]] == ["Other account"]
    assert classify.apply_kinds(cache, {"10": 1}, {}, times, now, 8)["not_played"]["bytes"] == 0


def test_mods_overview_lists_games_with_mods_and_where_they_are():
    workshop = {"where": "workshop", "path": "/library/steamapps/workshop/content/10", "bytes": 100}
    mo2 = {"where": "mod-organizer", "path": "/home/user/Games/ModOrganizer2/game/mods", "bytes": 300}
    cache = {
        "sizes": {
            "3000000001": {"name": "Modded MO2", "bytes": 400, "base": 100, "mods": 300, "source": "mod-organizer",
                           "kind": "game", "mod_parts": [mo2]},
            "3000000002": {"name": "Plain ROM", "bytes": 50, "base": 50, "mods": 0, "source": "rom", "kind": "game"},
            "3000000003": {"name": "Modded app", "bytes": 90, "base": 10, "mods": 80, "source": "flatpak",
                           "kind": "app", "mod_parts": []},
        },
        "unsized": {},
        "steam": {"10": {"name": "Workshop game", "base": 300, "mods": 100, "mod_parts": [workshop]}},
    }
    found = classify.apply_kinds(cache, {"10": 1}, {})["mods"]
    assert [(g["name"], g["mods"], g["share"]) for g in found["games"]] == [
        ("Modded MO2", 300, 0.75), ("Workshop game", 100, 0.25)]
    assert found["games"][0]["mod_parts"] == [mo2]
    assert found["bytes"] == 400


def test_device_name_prefers_the_users_then_the_model():
    assert classify.device_name("Den", "Fremont", "steamdeck") == "Den"
    assert classify.device_name("", "Fremont\n", "steamdeck") == "Steam Machine"
    assert classify.device_name("", "Galileo", "steamdeck") == "Steam Deck"
    assert classify.device_name("", "Some PC", "desk") == "desk"


def test_piles_hold_games_only_by_their_rules():
    gib = classify.GIB
    cache = {
        "sizes": {"3000000001": {"name": "ROM", "bytes": 2 * gib, "base": 2 * gib, "mods": 0, "source": "rom", "kind": "game"},
                  "3000000002": {"name": "Big app", "bytes": 90 * gib, "base": 90 * gib, "mods": 0, "source": "flatpak",
                                 "kind": "app"}},
        "unsized": {},
        "steam": {"10": {"name": "Huge", "base": 60 * gib, "mods": 0},
                  "11": {"name": "Modded", "base": gib, "mods": gib, "mod_parts": []}},
    }
    result = classify.apply_kinds(cache, {"10": 1, "11": 1}, {}, {"10": 1}, 10 ** 9, 6)
    piles = classify.piles(result, 50, "Den")
    assert piles["big"] == {"name": "Over 50 GB · Den (Hoard)", "appids": ["10"]}
    assert piles["modded"]["appids"] == ["11"]
    assert piles["stale"] == {"name": "Not played in 6 months · Den (Hoard)", "appids": ["10"]}
    assert piles["on_disk"]["appids"] == ["10", "11", "3000000001"]
