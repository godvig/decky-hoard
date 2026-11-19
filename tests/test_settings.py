"""Settings stored by the backend, with a stand-in for Decky's module."""

import asyncio
import json
import logging
import os
import sys
import time
import types

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def emitted():
    return []


@pytest.fixture
def plugin(tmp_path, monkeypatch, emitted):
    async def emit(event, *args):
        emitted.append(event)

    fake = types.SimpleNamespace(DECKY_PLUGIN_SETTINGS_DIR=str(tmp_path), DECKY_USER_HOME=str(tmp_path),
                                 DECKY_PLUGIN_VERSION="1.2.3",
                                 logger=logging.getLogger("hoard-test"), emit=emit)
    monkeypatch.setitem(sys.modules, "decky", fake)
    sys.modules.pop("main", None)
    import main
    return main.Plugin()


DEFAULTS = {"enabled": True, "sort_override": True, "size_label": True, "scan_shortcuts": True,
            "check_updates": False, "biggest_games": True, "not_played": True, "mods_overview": True, "stale_months": 6,
            "kind_overrides": {}}


def test_everything_but_the_update_check_defaults_to_on(plugin):
    assert asyncio.run(plugin.get_settings()) == DEFAULTS


def test_set_setting_is_saved(plugin, tmp_path):
    assert asyncio.run(plugin.set_setting("sort_override", False)) == {**DEFAULTS, "sort_override": False}
    assert json.loads((tmp_path / "settings.json").read_text())["sort_override"] is False
    assert asyncio.run(plugin.get_settings())["sort_override"] is False


def test_settings_saved_by_an_earlier_version_still_apply(plugin, tmp_path):
    (tmp_path / "settings.json").write_text('{"sort_override": false}')
    assert asyncio.run(plugin.get_settings()) == {**DEFAULTS, "sort_override": False}


def test_turned_off_hoard_neither_scans_nor_rescans(plugin, tmp_path):
    asyncio.run(plugin.set_setting("enabled", False))
    assert plugin._needs_scan(plugin._load_cache())
    assert not plugin._should_scan()
    assert asyncio.run(plugin.rescan()) is False


def test_turning_hoard_on_scans_when_due(plugin, tmp_path, monkeypatch):
    started = []

    async def scan():
        started.append(True)

    monkeypatch.setattr(plugin, "_scan", scan)

    async def toggle():
        await plugin.set_setting("enabled", False)
        await plugin.set_setting("enabled", True)
        await asyncio.sleep(0)

    asyncio.run(toggle())
    assert started == [True]


def test_scan_without_shortcuts_keeps_their_last_sizes(plugin, tmp_path):
    shortcut = {"name": "Shortcut", "bytes": 5, "base": 5, "mods": 0, "source": "folder", "kind": "game", "guessed": False, "paths": []}
    plugin._save_cache({"sizes": {"3000000001": shortcut}, "unsized": {}, "steam": {}, "total_bytes": 5,
                        "scanned_at": 0})
    asyncio.run(plugin.set_setting("scan_shortcuts", False))
    asyncio.run(plugin._scan())
    cache = plugin._load_cache()
    assert cache["sizes"] == {"3000000001": shortcut}
    assert cache["total_bytes"] == 5
    assert cache["shortcuts_scanned"] is False
    assert not plugin._needs_scan(cache)
    # Those sizes are stale once shortcut scanning is back on.
    asyncio.run(plugin.set_setting("scan_shortcuts", True))
    assert plugin._needs_scan(plugin._load_cache())


def test_version_comes_from_decky(plugin):
    assert asyncio.run(plugin.get_version()) == "1.2.3"


def test_cache_and_settings_live_in_decky_settings_dir(plugin, tmp_path):
    # Decky names that folder after the install folder, so nothing here may name one itself.
    asyncio.run(plugin.set_setting("sort_override", False))
    plugin._save_cache({"sizes": {}})
    assert sorted(os.listdir(tmp_path)) == ["settings.json", "sizes.json"]


def test_scan_after_unload_stops_without_saving(plugin, tmp_path, emitted):
    game = tmp_path / ".local/share/Steam/steamapps/common/Game"
    game.mkdir(parents=True)
    (tmp_path / ".local/share/Steam/steamapps/appmanifest_1.acf").write_text(
        '"AppState"\n{\n\t"appid"\t\t"1"\n\t"name"\t\t"Game"\n\t"installdir"\t\t"Game"\n\t"SizeOnDisk"\t\t"0"\n}\n'
    )
    asyncio.run(plugin._unload())
    asyncio.run(plugin._scan())
    assert not (tmp_path / "sizes.json").exists()
    assert emitted == []
    assert plugin._scanning is False


def test_unknown_keys_and_broken_files_are_ignored(plugin, tmp_path):
    assert asyncio.run(plugin.set_setting("nope", True)) == DEFAULTS
    (tmp_path / "settings.json").write_text("[1, 2")
    assert asyncio.run(plugin.get_settings()) == DEFAULTS


@pytest.fixture
def github(plugin, monkeypatch):
    """Stands in for GitHub: append the version the next request returns, or None for offline."""
    answers = []
    requests = []

    def fetch_latest():
        requests.append(True)
        return answers.pop(0) if answers else None

    monkeypatch.setattr(sys.modules["updates"], "fetch_latest", fetch_latest)
    return types.SimpleNamespace(answers=answers, requests=requests)


def test_update_check_never_asks_until_turned_on(plugin, github):
    assert not plugin._update_check_due()
    info = asyncio.run(plugin.check_updates_now())
    assert github.requests == []
    assert info["available"] is False


def test_update_check_finds_a_newer_release(plugin, github):
    asyncio.run(plugin.set_setting("check_updates", True))
    github.answers.append("1.3.0")
    info = asyncio.run(plugin.check_updates_now())
    assert (info["current"], info["latest"], info["available"]) == ("1.2.3", "1.3.0", True)
    assert info["url"] == "https://github.com/godvig/decky-hoard/releases/tag/v1.3.0"


def test_update_check_on_the_latest_release(plugin, github):
    asyncio.run(plugin.set_setting("check_updates", True))
    github.answers.append("1.2.3")
    info = asyncio.run(plugin.check_updates_now())
    assert (info["available"], info["url"]) == (False, None)


def test_update_check_asks_at_most_once_a_day_even_offline(plugin, github, emitted):
    async def turn_on():
        await plugin.set_setting("check_updates", True)
        await asyncio.sleep(0)
        await asyncio.sleep(0)

    asyncio.run(turn_on())
    assert github.requests == [True]
    assert not plugin._update_check_due()
    info = asyncio.run(plugin.get_update())
    assert (info["latest"], info["checked_at"], info["available"]) == (None, 0, False)
    assert "updates_changed" in emitted


def test_turned_off_hoard_checks_no_updates(plugin, github):
    asyncio.run(plugin.set_setting("check_updates", True))
    asyncio.run(plugin.set_setting("enabled", False))
    plugin._write_json(plugin._updates_path(), {"attempted_at": 0})
    github.requests.clear()
    assert not plugin._update_check_due()
    asyncio.run(plugin.check_updates_now())
    assert github.requests == []


def test_a_cache_from_an_earlier_hoard_is_rescanned(plugin):
    plugin._save_cache({"sizes": {}, "unsized": {}, "steam": {}, "scanned_at": time.time()})
    assert plugin._needs_scan(plugin._load_cache())


def test_sizes_carry_kinds_counts_and_steam_app_types(plugin):
    plugin._save_cache({"sizes": {"3000000001": {"name": "Emulator", "bytes": 5, "kind": "emulator", "guessed": False}},
                        "unsized": {}, "steam": {"20": {"name": "Runtime", "base": 1, "mods": 0}}})
    asyncio.run(plugin.set_app_types({20: 4, "30": "not a type"}))
    sizes = asyncio.run(plugin.get_sizes())
    assert sizes["steam"]["20"]["kind"] == "tool"
    assert sizes["counts"]["shortcut_games"] == 0
    with open(plugin._app_types_path()) as f:
        assert json.load(f) == {"20": 4}


def test_set_kind_overrides_and_goes_back_to_the_rules(plugin):
    plugin._save_cache({"sizes": {"3000000001": {"name": "Emulator", "bytes": 5, "kind": "emulator", "guessed": False}},
                        "unsized": {}, "steam": {}})
    sizes = asyncio.run(plugin.set_kind("3000000001", "game"))
    assert (sizes["sizes"]["3000000001"]["kind"], sizes["counts"]["shortcut_games"]) == ("game", 1)
    assert asyncio.run(plugin.get_settings())["kind_overrides"] == {"3000000001": "game"}
    sizes = asyncio.run(plugin.set_kind("3000000001", None))
    assert sizes["sizes"]["3000000001"]["kind"] == "emulator"
    assert asyncio.run(plugin.get_settings())["kind_overrides"] == {}


def test_overrides_cant_be_set_as_a_switch(plugin):
    asyncio.run(plugin.set_setting("kind_overrides", True))
    assert asyncio.run(plugin.get_settings())["kind_overrides"] == {}


def test_counts_as_game_stores_only_what_differs_from_the_rules(plugin):
    plugin._save_cache({"sizes": {"3000000001": {"name": "Emulator", "bytes": 5, "kind": "emulator", "guessed": False},
                                  "3000000002": {"name": "Game", "bytes": 5, "kind": "game", "guessed": False}},
                        "unsized": {}, "steam": {}})
    asyncio.run(plugin.set_counts_as_game("3000000001", True))
    asyncio.run(plugin.set_counts_as_game("3000000002", False))
    assert asyncio.run(plugin.get_settings())["kind_overrides"] == {"3000000001": "game", "3000000002": "app"}
    sizes = asyncio.run(plugin.set_counts_as_game("3000000001", False))
    asyncio.run(plugin.set_counts_as_game("3000000002", True))
    assert asyncio.run(plugin.get_settings())["kind_overrides"] == {}
    assert sizes["entries"][0]["name"] == "Emulator"


def test_rescan_now_measures_everything_and_the_watcher_reuses(plugin, monkeypatch):
    calls = []

    def scan(home, should_stop, include_shortcuts, previous):
        calls.append(previous)
        return {"format": 2, "sizes": {}, "unsized": {}, "steam": {"1": {"name": "Game", "base": 1, "mods": 0}}}

    monkeypatch.setattr(sys.modules["scanner"], "scan", scan)
    asyncio.run(plugin._scan())
    asyncio.run(plugin._scan())
    asyncio.run(plugin._scan(full=True))
    # The first scan has nothing to reuse yet.
    assert calls == [{}, {"1": {"name": "Game", "base": 1, "mods": 0}}, None]


def test_stale_months_is_kept_in_range(plugin):
    assert asyncio.run(plugin.set_setting("stale_months", 12))["stale_months"] == 12
    assert asyncio.run(plugin.set_setting("stale_months", 0))["stale_months"] == 1
    assert asyncio.run(plugin.set_setting("stale_months", 99))["stale_months"] == 36


def test_not_played_uses_steams_times_and_the_months_setting(plugin):
    month = 30.44 * 24 * 60 * 60
    plugin._save_cache({"format": 2, "sizes": {}, "unsized": {}, "steam": {
        "10": {"name": "Old", "base": 100, "mods": 0},
        "11": {"name": "Recent", "base": 50, "mods": 0},
        "12": {"name": "Never", "base": 30, "mods": 0}}})
    asyncio.run(plugin.set_app_types({"10": 1, "11": 1, "12": 1}))
    asyncio.run(plugin.set_last_played({"10": int(time.time() - 8 * month), "11": int(time.time() - 2 * month),
                                        "12": 0, "13": True}))
    found = asyncio.run(plugin.get_sizes())["not_played"]
    assert ([g["name"] for g in found["games"]], found["bytes"]) == (["Old"], 100)
    assert ([g["name"] for g in found["unknown"]], found["unknown_bytes"]) == (["Never"], 30)
    asyncio.run(plugin.set_setting("stale_months", 1))
    found = asyncio.run(plugin.get_sizes())["not_played"]
    assert [g["name"] for g in found["games"]] == ["Old", "Recent"]
    with open(plugin._last_played_path()) as f:
        assert "13" not in json.load(f)


def test_shortcuts_drop_out_of_counts_and_lists_while_not_scanned(plugin):
    plugin._save_cache({"format": 2, "sizes": {"3000000001": {"name": "ROM", "bytes": 5, "base": 5, "mods": 0,
                                                              "source": "rom", "kind": "game", "guessed": False}},
                        "unsized": {}, "steam": {}, "total_bytes": 5})
    asyncio.run(plugin.set_setting("scan_shortcuts", False))
    sizes = asyncio.run(plugin.get_sizes())
    assert (sizes["biggest"], sizes["not_played"]["unknown"], sizes["counts"]["shortcut_games"]) == ([], [], 0)
    assert "3000000001" in plugin._load_cache()["sizes"]
