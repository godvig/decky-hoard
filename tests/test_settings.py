"""Settings stored by the backend, with a stand-in for Decky's module."""

import asyncio
import json
import os
import sys
import types

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def plugin(tmp_path, monkeypatch):
    fake = types.SimpleNamespace(DECKY_PLUGIN_SETTINGS_DIR=str(tmp_path), DECKY_USER_HOME=str(tmp_path))
    monkeypatch.setitem(sys.modules, "decky", fake)
    sys.modules.pop("main", None)
    import main
    return main.Plugin()


def test_sort_override_defaults_to_on(plugin):
    assert asyncio.run(plugin.get_settings()) == {"sort_override": True}


def test_set_setting_is_saved(plugin, tmp_path):
    assert asyncio.run(plugin.set_setting("sort_override", False)) == {"sort_override": False}
    assert json.loads((tmp_path / "settings.json").read_text()) == {"sort_override": False}
    assert asyncio.run(plugin.get_settings()) == {"sort_override": False}


def test_cache_and_settings_live_in_decky_settings_dir(plugin, tmp_path):
    # Decky names that folder after the install folder, so nothing here may name one itself.
    asyncio.run(plugin.set_setting("sort_override", False))
    plugin._save_cache({"sizes": {}})
    assert sorted(os.listdir(tmp_path)) == ["settings.json", "sizes.json"]


def test_unknown_keys_and_broken_files_are_ignored(plugin, tmp_path):
    assert asyncio.run(plugin.set_setting("nope", True)) == {"sort_override": True}
    (tmp_path / "settings.json").write_text("[1, 2")
    assert asyncio.run(plugin.get_settings()) == {"sort_override": True}
