"""Settings stored by the backend, with a stand-in for Decky's module."""

import asyncio
import json
import logging
import os
import sys
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


ALL_ON = {"enabled": True, "sort_override": True, "size_label": True, "scan_shortcuts": True}


def test_everything_defaults_to_on(plugin):
    assert asyncio.run(plugin.get_settings()) == ALL_ON


def test_set_setting_is_saved(plugin, tmp_path):
    assert asyncio.run(plugin.set_setting("sort_override", False)) == {**ALL_ON, "sort_override": False}
    assert json.loads((tmp_path / "settings.json").read_text())["sort_override"] is False
    assert asyncio.run(plugin.get_settings())["sort_override"] is False


def test_settings_saved_by_an_earlier_version_still_apply(plugin, tmp_path):
    (tmp_path / "settings.json").write_text('{"sort_override": false}')
    assert asyncio.run(plugin.get_settings()) == {**ALL_ON, "sort_override": False}


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
    shortcut = {"name": "Shortcut", "bytes": 5, "base": 5, "mods": 0, "kind": "folder", "paths": []}
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
    assert asyncio.run(plugin.set_setting("nope", True)) == ALL_ON
    (tmp_path / "settings.json").write_text("[1, 2")
    assert asyncio.run(plugin.get_settings()) == ALL_ON
