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


def test_unknown_keys_and_broken_files_are_ignored(plugin, tmp_path):
    assert asyncio.run(plugin.set_setting("nope", True)) == {"sort_override": True}
    (tmp_path / "settings.json").write_text("[1, 2")
    assert asyncio.run(plugin.get_settings()) == {"sort_override": True}
