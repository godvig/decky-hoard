"""Scanner tests against fake Steam, Mod Organizer and game folders in tmp_path."""

import os
import struct
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import scanner

MB = 1024 ** 2


def write(path, size=0):
    """Create a file of the given size without spending disk on it."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.truncate(size)
    return path


def vdf_object(fields: dict) -> bytes:
    out = b""
    for key, value in fields.items():
        name = key.encode() + b"\0"
        if isinstance(value, dict):
            out += b"\x00" + name + vdf_object(value)
        elif isinstance(value, int):
            out += b"\x02" + name + struct.pack("<I", value)
        else:
            out += b"\x01" + name + value.encode() + b"\0"
    return out + b"\x08"


def write_shortcuts(home, *entries):
    path = os.path.join(home, ".local/share/Steam/userdata/123/config/shortcuts.vdf")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    shortcuts = {str(i): entry for i, entry in enumerate(entries)}
    with open(path, "wb") as f:
        f.write(vdf_object({"shortcuts": shortcuts}) + b"\x08")


def write_manifest(library, appid, name, installdir, size_on_disk):
    path = os.path.join(library, "steamapps", f"appmanifest_{appid}.acf")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(
            '"AppState"\n{\n'
            f'\t"appid"\t\t"{appid}"\n\t"name"\t\t"{name}"\n'
            f'\t"installdir"\t\t"{installdir}"\n\t"SizeOnDisk"\t\t"{size_on_disk}"\n}}\n'
        )


def install_steam_game(library, appid, name, size):
    folder = os.path.join(library, "steamapps/common", name)
    write(os.path.join(folder, "game.bin"), size)
    write_manifest(library, appid, name, name, size)
    return folder


@pytest.fixture
def home(tmp_path):
    home = str(tmp_path / "home")
    os.makedirs(os.path.join(home, ".local/share/Steam/steamapps"))
    return home


@pytest.fixture
def steam(home):
    return os.path.join(home, ".local/share/Steam")


def scan_steam(home):
    return scanner.scan_steam(home, scanner.mo2_instances(home), lambda paths: sum(map(scanner.measure, paths)))


def test_parse_shortcuts_keeps_strings_and_ints():
    data = vdf_object({"shortcuts": {"0": {"appid": 3000000000, "AppName": "Game", "Exe": '"/bin/x"'}}}) + b"\x08"
    assert scanner.parse_shortcuts(data) == [{"appid": 3000000000, "AppName": "Game", "Exe": '"/bin/x"'}]


def test_steam_game_in_primary_library_uses_manifest_size(home, steam):
    install_steam_game(steam, 10, "Primary", 50 * MB)
    games = scan_steam(home)
    assert [(g["appid"], g["base"], g["mods"]) for g in games.values()] == [("10", 50 * MB, 0)]


def test_steam_game_in_second_library(home, steam, tmp_path):
    sd = str(tmp_path / "sdcard")
    with open(os.path.join(steam, "steamapps/libraryfolders.vdf"), "w") as f:
        f.write(f'"libraryfolders"\n{{\n\t"0"\n\t{{\n\t\t"path"\t\t"{steam}"\n\t}}\n'
                f'\t"1"\n\t{{\n\t\t"path"\t\t"{sd}"\n\t}}\n}}\n')
    install_steam_game(sd, 20, "OnSd", 30 * MB)
    games = scan_steam(home)
    assert {g["appid"] for g in games.values()} == {"20"}


def test_workshop_content_counts_as_mods(home, steam):
    install_steam_game(steam, 30, "Workshop", 40 * MB)
    write(os.path.join(steam, "steamapps/workshop/content/30/111/mod.pak"), 5 * MB)
    (game,) = scan_steam(home).values()
    assert (game["base"], game["mods"]) == (40 * MB, 5 * MB)


def test_loose_files_count_as_mods_only_above_minimum(home, steam):
    big = install_steam_game(steam, 40, "Big", 40 * MB)
    small = install_steam_game(steam, 41, "Small", 40 * MB)
    write(os.path.join(big, "Data/mod.esp"), 20 * MB)
    write(os.path.join(small, "logs/log.txt"), 1 * MB)
    games = {g["appid"]: g for g in scan_steam(home).values()}
    assert games["40"]["mods"] == 20 * MB
    assert games["41"]["mods"] == 0


def test_broken_and_uninstalled_manifests_are_skipped(home, steam):
    install_steam_game(steam, 50, "Fine", 10 * MB)
    write_manifest(steam, 51, "Gone", "Gone", 10 * MB)  # No folder: not installed.
    with open(os.path.join(steam, "steamapps/appmanifest_52.acf"), "w") as f:
        f.write('"AppState"\n{\n\t"appid"\t\t"52"\n')  # Cut off mid-write.
    assert [g["appid"] for g in scan_steam(home).values()] == ["50"]


def test_scan_sizes_folder_shortcut_and_marks_unknown_unsized(home):
    game = os.path.join(home, "Games/Indie")
    write(os.path.join(game, "bin/indie.exe"), 3 * MB)
    write_shortcuts(
        home,
        {"appid": 3000000001, "AppName": "Indie", "Exe": f'"{game}/bin/indie.exe"', "StartDir": f'"{game}/bin"'},
        {"appid": 3000000002, "AppName": "Mystery", "Exe": '"/usr/bin/true"', "StartDir": '"/usr/bin"'},
    )
    result = scanner.scan(home)
    assert result["sizes"]["3000000001"]["kind"] == "folder"
    assert result["sizes"]["3000000001"]["paths"] == [game]  # Widened to the top folder under ~/Games.
    assert result["sizes"]["3000000001"]["base"] == 3 * MB
    assert result["unsized"]["3000000002"] == {"name": "Mystery", "kind": "unknown"}
    assert result["total_bytes"] == 3 * MB


def test_scan_shortcut_inside_steam_game_reuses_its_size(home, steam):
    folder = install_steam_game(steam, 60, "Modded", 25 * MB)
    write_shortcuts(home, {"appid": 3000000003, "AppName": "Launcher", "Exe": f'"{folder}/launcher.sh"'})
    result = scanner.scan(home)
    assert result["sizes"]["3000000003"]["kind"] == "steam-game"
    assert result["sizes"]["3000000003"]["bytes"] == 25 * MB
    assert result["steam"]["60"] == {"name": "Modded", "base": 25 * MB, "mods": 0}


def test_scan_stops_between_folders_when_asked(home, steam):
    install_steam_game(steam, 70, "First", 10 * MB)
    install_steam_game(steam, 71, "Second", 10 * MB)
    checks = []

    def stop_after_first_folder():
        checks.append(None)
        return len(checks) > 1

    with pytest.raises(scanner.ScanStopped):
        scanner.scan(home, stop_after_first_folder)
    assert len(checks) == 2


def test_scan_mod_organizer_splits_game_and_mods(home):
    game = os.path.join(home, "Games/Fallout")
    write(os.path.join(game, "Fallout.exe"), 10 * MB)
    instance = os.path.join(home, "Games/ModOrganizer2/fo")
    write(os.path.join(instance, "ModOrganizer.exe"), 1 * MB)
    write(os.path.join(instance, "mods/Big Mod/big.esp"), 7 * MB)
    write(os.path.join(instance, "downloads/big.7z"), 2 * MB)
    with open(os.path.join(instance, "ModOrganizer.ini"), "w") as f:
        f.write(f"[General]\ngamePath=@ByteArray(Z:{game})\n")
    write_shortcuts(home, {"appid": 3000000004, "AppName": "Fallout MO2", "Exe": f'"{instance}/launch.sh"',
                           "StartDir": f'"{instance}"'})
    info = scanner.scan(home)["sizes"]["3000000004"]
    assert info["kind"] == "mod-organizer"
    assert info["mods"] == 9 * MB
    assert info["base"] == 11 * MB + os.path.getsize(os.path.join(instance, "ModOrganizer.ini"))


def test_measure_does_not_follow_symlinks(tmp_path):
    outside = write(str(tmp_path / "outside/huge.bin"), 100 * MB)
    write(str(tmp_path / "game/data.bin"), 1 * MB)
    os.symlink(outside, tmp_path / "game/link.bin")
    os.symlink(tmp_path / "outside", tmp_path / "game/linkdir")
    assert scanner.measure(str(tmp_path / "game")) == 1 * MB


def test_unreadable_mod_organizer_instance_does_not_fail(tmp_path):
    missing = str(tmp_path / "gone")
    kind, base, mods = scanner._resolve_mo2(missing, {missing: "/game"})
    assert (kind, base) == ("mod-organizer", ["/game"])


def test_watched_paths_include_every_steamapps_folder(home, steam, tmp_path):
    sd = str(tmp_path / "sdcard")
    with open(os.path.join(steam, "steamapps/libraryfolders.vdf"), "w") as f:
        f.write(f'"libraryfolders"\n{{\n\t"1"\n\t{{\n\t\t"path"\t\t"{sd}"\n\t}}\n}}\n')
    write_shortcuts(home)
    paths = scanner.watched_paths(home)
    assert os.path.join(steam, "steamapps") in paths
    assert os.path.join(sd, "steamapps") in paths
    assert any(p.endswith("shortcuts.vdf") for p in paths)


def test_installing_a_steam_game_changes_steamapps_mtime(steam):
    apps = os.path.join(steam, "steamapps")
    os.utime(apps, (0, 0))
    install_steam_game(steam, 70, "New", 1 * MB)
    assert os.path.getmtime(apps) > 0
