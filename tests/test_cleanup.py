"""What clean-up may remove, and above all what it may not. Synthetic libraries only."""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cleanup
from test_scanner import MB, write, write_shortcuts


@pytest.fixture
def home(tmp_path):
    return str(tmp_path / "home")


@pytest.fixture
def steam(home):
    path = os.path.join(home, ".local/share/Steam")
    os.makedirs(os.path.join(path, "steamapps"))
    return path


def library_file(steam, libraries):
    """libraryfolders.vdf for {path: [installed appids]}."""
    body = "".join(
        f'\t"{i}"\n\t{{\n\t\t"path"\t\t"{path}"\n\t\t"apps"\n\t\t{{\n'
        + "".join(f'\t\t\t"{appid}"\t\t"1"\n' for appid in apps)
        + "\t\t}\n\t}\n"
        for i, (path, apps) in enumerate(libraries.items()))
    with open(os.path.join(steam, "steamapps/libraryfolders.vdf"), "w") as f:
        f.write(f'"libraryfolders"\n{{\n{body}}}\n')


def cache(library, kind, appid, size=1 * MB):
    path = os.path.join(library, "steamapps", kind, str(appid))
    write(os.path.join(path, "data.bin"), size)
    return path


def test_parse_vdf_reads_nested_keys():
    assert cleanup.parse_vdf('"a"\n{\n\t"b"\t"1"\n\t"c"\n\t{\n\t\t"d"\t"2"\n\t}\n}\n') == {"a": {"b": "1", "c": {"d": "2"}}}


def test_finds_caches_and_prefixes_of_apps_not_installed(home, steam):
    library_file(steam, {steam: [10]})
    cache(steam, "shadercache", 10)
    old = cache(steam, "shadercache", 20, 3 * MB)
    prefix = cache(steam, "compatdata", 30, 2 * MB)
    found = cleanup.find(home)
    assert found["ok"]
    assert [(e["path"], e["bytes"]) for e in found["shader"]] == [(old, 3 * MB)]
    assert [e["path"] for e in found["prefixes"]] == [prefix]
    assert found["shader"][0]["shown"] == "~/.local/share/Steam/steamapps/shadercache/20"


def test_shortcuts_on_any_account_keep_their_caches(home, steam):
    library_file(steam, {steam: []})
    write_shortcuts(home, {"appid": 3000000001, "AppName": "Shortcut", "Exe": '"/x"'})
    cache(steam, "shadercache", 3000000001)
    cache(steam, "compatdata", 3000000001)
    found = cleanup.find(home)
    assert (found["shader"], found["prefixes"]) == ([], [])


def test_a_missing_library_stops_everything(home, steam, tmp_path):
    card = str(tmp_path / "sdcard")
    library_file(steam, {steam: [], card: [40]})
    cache(steam, "shadercache", 50)
    found = cleanup.find(home)
    assert not found["ok"]
    assert found["shader"] == []
    assert found["missing"] == [card]


def test_a_game_listed_only_in_libraryfolders_counts_as_installed(home, steam, tmp_path):
    card = str(tmp_path / "sdcard")
    os.makedirs(os.path.join(card, "steamapps"))
    library_file(steam, {steam: [], card: [60]})
    cache(steam, "shadercache", 60)
    assert cleanup.find(home)["shader"] == []


def test_symlinks_and_odd_names_are_never_listed(home, steam, tmp_path):
    library_file(steam, {steam: []})
    target = str(tmp_path / "elsewhere")
    write(os.path.join(target, "precious.bin"), 1 * MB)
    os.makedirs(os.path.join(steam, "steamapps/shadercache"))
    os.symlink(target, os.path.join(steam, "steamapps/shadercache/70"))
    cache(steam, "shadercache", "notanappid")
    assert cleanup.find(home)["shader"] == []


def test_remove_takes_only_what_a_fresh_look_still_allows(home, steam, tmp_path):
    library_file(steam, {steam: []})
    old = cache(steam, "shadercache", 80, 2 * MB)
    now_installed = cache(steam, "shadercache", 81)
    prefix = cache(steam, "compatdata", 82)
    game = os.path.join(steam, "steamapps/common/Game")
    write(os.path.join(game, "game.bin"), 1 * MB)
    # Installed after the user looked at the list.
    library_file(steam, {steam: [81]})
    log = str(tmp_path / "cleanup.log")
    result = cleanup.remove_shader_caches(home, [old, now_installed, prefix, game], log)
    assert not os.path.exists(old)
    assert all(os.path.exists(path) for path in (now_installed, prefix, game))
    assert result["bytes"] == 2 * MB
    assert result["removed"] == ["~/.local/share/Steam/steamapps/shadercache/80"]
    assert len(result["skipped"]) == 3
    with open(log) as f:
        assert f.read().split("\t")[1:] == ["removed", str(2 * MB), old + "\n"]


def test_remove_does_nothing_while_a_library_is_missing(home, steam, tmp_path):
    library_file(steam, {steam: [], str(tmp_path / "sdcard"): []})
    old = cache(steam, "shadercache", 90)
    result = cleanup.remove_shader_caches(home, [old], str(tmp_path / "cleanup.log"))
    assert os.path.exists(old)
    assert result["removed"] == []
