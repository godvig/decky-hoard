"""Work out how much disk space each game and its mods use.

Read-only: it parses shortcuts.vdf, Steam's app manifests, Mod Organizer and
OpenMW configs and Heroic's install records, and walks game folders. It never
writes to Steam's files and never touches the network.
"""

import glob
import json
import os
import re
import stat
import struct

ROM_PLAYLISTS = (".cue", ".m3u")
# Launchers rather than games: their own size says nothing about the game.
SKIPPED_FILE_SUFFIXES = (".sh", ".desktop", ".so")
QUOTED_PATH = re.compile(r""""(/[^"]+)"|'(/[^']+)'""")
PS3_EBOOT = re.compile(r"/(?:PS3_GAME/)?USRDIR/EBOOT\.BIN$", re.IGNORECASE)
BARE_PATH = re.compile(r"""(?:^|\s)(/(?:home|run/media)/\S+)""")
FLATPAK_ID = re.compile(r"\b[a-zA-Z][\w-]*(?:\.[\w-]+){2,}\b")
HEROIC_APP = re.compile(r"heroic://launch(?:/[a-z]+/|\?appName=)([^&\"'\s]+)")
MO2_GAME_PATH = re.compile(r"^gamePath=(?:@ByteArray\()?Z:(.+?)\)?$", re.MULTILINE)
# What a Mod Organizer instance holds as mods; the rest is the program itself.
MO2_MOD_FOLDERS = ("mods", "overwrite", "downloads")
# Files beyond Steam's manifest below this are logs and configs, not mods.
LOOSE_MODS_MINIMUM = 10 * 1024 ** 2


class ScanStopped(Exception):
    """Raised by a scan whose should_stop returned true."""


def _never() -> bool:
    return False


def parse_shortcuts(data: bytes) -> list[dict]:
    """Parse Steam's binary shortcuts.vdf into a list of shortcut dicts."""
    pos = 0

    def read_string() -> str:
        nonlocal pos
        end = data.index(b"\0", pos)
        value = data[pos:end].decode("utf-8", "replace")
        pos = end + 1
        return value

    def read_object() -> dict:
        nonlocal pos
        out = {}
        while pos < len(data):
            kind = data[pos]
            pos += 1
            if kind == 8:
                return out
            key = read_string()
            if kind == 0:
                out[key] = read_object()
            elif kind == 1:
                out[key] = read_string()
            elif kind == 2:
                out[key] = struct.unpack_from("<I", data, pos)[0]
                pos += 4
            else:
                raise ValueError(f"unknown vdf type {kind} at {pos}")
        return out

    return list(read_object().get("shortcuts", {}).values())


def load_shortcuts(home: str) -> dict[int, dict]:
    """All shortcuts across the machine's Steam accounts, keyed by appid."""
    found = {}
    for path in shortcut_files(home):
        try:
            with open(path, "rb") as f:
                for entry in parse_shortcuts(f.read()):
                    # Key case varies between Steam versions and writers.
                    entry = {k.lower(): v for k, v in entry.items()}
                    if entry.get("appid"):
                        found[entry["appid"]] = entry
        except (OSError, ValueError, struct.error):
            continue
    return found


def shortcut_files(home: str) -> list[str]:
    return glob.glob(os.path.join(home, ".local/share/Steam/userdata/*/config/shortcuts.vdf"))


def _read_json(path: str):
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def load_heroic_installs(home: str) -> dict[str, str]:
    """Map Heroic's appName to the folder it installed that game in."""
    installs = {}
    for root in (
        os.path.join(home, ".var/app/com.heroicgameslauncher.hgl/config"),
        os.path.join(home, ".config"),
    ):
        for rel in ("heroic/legendaryConfig/legendary/installed.json", "legendary/installed.json"):
            data = _read_json(os.path.join(root, rel))
            if isinstance(data, dict):
                for name, info in data.items():
                    if isinstance(info, dict) and info.get("install_path"):
                        installs[name] = info["install_path"]
        data = _read_json(os.path.join(root, "heroic/gog_store/installed.json"))
        if isinstance(data, dict):
            for info in data.get("installed") or []:
                if info.get("appName") and info.get("install_path"):
                    installs[info["appName"]] = info["install_path"]
        data = _read_json(os.path.join(root, "heroic/nile_config/nile/installed.json"))
        if isinstance(data, list):
            for info in data:
                if isinstance(info, dict) and info.get("id") and info.get("path"):
                    installs[info["id"]] = info["path"]
        data = _read_json(os.path.join(root, "heroic/sideload_apps/library.json"))
        if isinstance(data, dict):
            for info in data.get("games") or []:
                if info.get("app_name") and info.get("folder_name"):
                    installs[info["app_name"]] = info["folder_name"]
    return installs


def _user_path(path: str, home: str) -> bool:
    return path.startswith((home + "/", "/run/media/"))


def _paths_in_options(options: str, home: str) -> list[str]:
    quoted = [double or single for double, single in QUOTED_PATH.findall(options)]
    candidates = quoted + BARE_PATH.findall(options)
    return [p for p in candidates if _user_path(p, home) and os.path.exists(p)]


def _split_exe(exe: str) -> tuple[str, str]:
    """Split the Exe field into the program and any arguments stored after it."""
    match = re.match(r'"([^"]*)"(.*)$', exe, re.DOTALL)
    return (match.group(1), match.group(2)) if match else (exe, "")


def _playlist_members(path: str) -> list[str]:
    """Files a .cue or .m3u points at, which hold the actual game data."""
    members = [path]
    folder = os.path.dirname(path)
    try:
        with open(path, errors="replace") as f:
            lines = f.read().splitlines()
    except OSError:
        return members
    for line in lines:
        line = line.strip()
        if path.lower().endswith(".cue"):
            match = re.match(r'FILE\s+"?(.+?)"?\s+\S+$', line, re.IGNORECASE)
            name = match.group(1) if match else None
        else:
            name = line if line and not line.startswith("#") else None
        if name:
            member = os.path.join(folder, name)
            if os.path.isfile(member):
                members.append(member)
    return members


def _game_folder(path: str, home: str) -> str:
    """Widen a folder under ~/Games to the game's top folder."""
    games = os.path.join(home, "Games") + os.sep
    if path.startswith(games):
        return games + path[len(games):].split(os.sep, 1)[0]
    return path


def resolve(entry: dict, home: str, heroic: dict[str, str]) -> tuple[str, list[str]]:
    """Return (kind, paths to measure); no paths means the size is unknown."""
    # EmuDeck's parser keeps ROM paths in Exe; others use the launch options.
    exe, exe_args = _split_exe(entry.get("exe") or "")
    options = f'{exe_args} {entry.get("launchoptions") or ""}'
    start =(entry.get("startdir") or "").strip('"').rstrip("/")

    match = HEROIC_APP.search(options)
    if match:
        path = heroic.get(match.group(1))
        return ("heroic", [path]) if path and os.path.isdir(path) else ("heroic-not-installed", [])

    # A ROM or other game file handed to an emulator on the command line.
    for path in _paths_in_options(options, home):
        if path.lower().endswith(SKIPPED_FILE_SUFFIXES):
            continue
        if path.lower().endswith(ROM_PLAYLISTS):
            return "rom", _playlist_members(path)
        # A PS3 game is launched through a tiny EBOOT.BIN inside its folder.
        return "rom", [PS3_EBOOT.sub("", path)]

    # Web pages opened in a browser take up no space of their own.
    if re.search(r"https?://", options):
        return "web", []

    start_ok = (
        _user_path(start + "/", home)
        and os.path.isdir(start)
        and os.path.dirname(start) != home  # ~/Downloads, ~/Applications, ...
        and start != home
        and "/Emulation/tools" not in start
    )
    if start_ok:
        return "folder", [_game_folder(start, home)]

    if os.path.basename(exe) == "flatpak":
        ids = FLATPAK_ID.findall(options)
        if ids:
            app = ids[0]
            paths = [
                os.path.join(home, ".local/share/flatpak/app", app),
                os.path.join("/var/lib/flatpak/app", app),
                os.path.join(home, ".var/app", app),
            ]
            paths = [p for p in paths if os.path.isdir(p)]
            if paths:
                return "flatpak", paths
        return "unknown", []

    if _user_path(exe, home) and os.path.isfile(exe) and not exe.lower().endswith(SKIPPED_FILE_SUFFIXES):
        return "file", [_game_folder(exe, home)]
    return "unknown", []


def measure(path: str, should_stop=_never) -> int:
    """Bytes used by a file or folder tree, without following symlinks."""
    try:
        info = os.lstat(path)
    except OSError:
        return 0
    if not stat.S_ISDIR(info.st_mode):
        return info.st_size if stat.S_ISREG(info.st_mode) else 0
    total = 0
    stack = [path]
    while stack:
        # Checked per folder, so a stop waits for one folder listing at most.
        if should_stop():
            raise ScanStopped
        try:
            with os.scandir(stack.pop()) as entries:
                for item in entries:
                    try:
                        if item.is_symlink():
                            continue
                        if item.is_dir(follow_symlinks=False):
                            stack.append(item.path)
                        elif item.is_file(follow_symlinks=False):
                            total += item.stat(follow_symlinks=False).st_size
                    except OSError:
                        continue
        except OSError:
            continue
    return total


def mo2_instances(home: str) -> dict[str, str]:
    """Map each Mod Organizer instance folder to the game folder it modifies."""
    instances = {}
    for ini in glob.glob(os.path.join(home, "Games/ModOrganizer2/*/ModOrganizer.ini")):
        try:
            with open(ini, errors="replace") as f:
                match = MO2_GAME_PATH.search(f.read())
        except OSError:
            continue
        if match:
            instances[os.path.dirname(ini)] = match.group(1).replace("\\\\", "/").replace("\\", "/")
    return instances


def _mo2_mod_paths(instance: str) -> list[str]:
    return [os.path.join(instance, name) for name in MO2_MOD_FOLDERS]


def _resolve_mo2(start: str, instances: dict[str, str]) -> tuple[str, list[str], list[str]] | None:
    game = instances.get(start)
    if game is None:
        return None
    base = [game]
    try:
        names = os.listdir(start)
    except OSError:
        names = []
    for name in names:
        if name not in MO2_MOD_FOLDERS:
            base.append(os.path.join(start, name))
    if os.path.isdir(start + "-prefix"):
        base.append(start + "-prefix")
    return "mod-organizer", base, _mo2_mod_paths(start)


def _resolve_openmw(start: str, home: str) -> tuple[str, list[str], list[str]] | None:
    if start != os.path.join(home, "Games/OpenMW"):
        return None
    base, mods = {start}, set()
    try:
        with open(os.path.join(home, ".config/openmw/openmw.cfg"), errors="replace") as f:
            for line in f:
                if line.startswith("data="):
                    path = line[5:].strip().strip('"')
                    target = base if os.path.isfile(os.path.join(path, "Morrowind.esm")) else mods
                    target.add(_game_folder(path, home))
    except OSError:
        pass
    # The mod installer keeps its downloaded archives beside the mods.
    mods |= {f"{path}-cache" for path in mods if os.path.isdir(f"{path}-cache")}
    return "openmw", sorted(base), sorted(mods)


def _steam_libraries(home: str) -> list[str]:
    steam = os.path.join(home, ".local/share/Steam")
    libraries = [steam]
    try:
        with open(os.path.join(steam, "steamapps/libraryfolders.vdf"), errors="replace") as f:
            libraries += re.findall(r'"path"\s+"([^"]+)"', f.read())
    except OSError:
        pass
    return list(dict.fromkeys(libraries))


def watched_paths(home: str) -> list[str]:
    """Paths whose mtime changes when a game is added or removed."""
    # Steam adds and deletes an appmanifest in steamapps for each install.
    return shortcut_files(home) + [os.path.join(library, "steamapps") for library in _steam_libraries(home)]


def scan_steam(home: str, instances: dict[str, str], size_of) -> dict[str, dict]:
    """Base and mod sizes of installed Steam apps, keyed by install folder."""
    modded = {game: instance for instance, game in instances.items()}
    games = {}
    for library in _steam_libraries(home):
        apps = os.path.join(library, "steamapps")
        for manifest in glob.glob(os.path.join(apps, "appmanifest_*.acf")):
            try:
                with open(manifest, errors="replace") as f:
                    fields = dict(re.findall(r'"(\w+)"\s+"([^"]*)"', f.read()))
                appid, name, base = fields["appid"], fields["name"], int(fields["SizeOnDisk"])
                folder = os.path.join(apps, "common", fields["installdir"])
            except (OSError, KeyError, ValueError):
                continue
            if not os.path.isdir(folder):
                continue
            mods = size_of([os.path.join(apps, "workshop/content", appid)])
            if folder in modded:
                mods += size_of(_mo2_mod_paths(modded[folder]))
            # Anything in the game folder that Steam didn't install came from a mod.
            loose = size_of([folder]) - base
            if loose >= LOOSE_MODS_MINIMUM:
                mods += loose
            games[folder] = {"appid": appid, "name": name, "base": base, "mods": mods}
    return games


def _steam_game(entry: dict, steam_games: dict[str, dict]) -> dict | None:
    """The Steam game a shortcut lives inside, such as a modding launcher."""
    exe, _ = _split_exe(entry.get("exe") or "")
    for folder, game in steam_games.items():
        if exe.startswith(folder + "/"):
            return game
    return None


def scan(home: str, should_stop=_never) -> dict:
    """Size every shortcut and Steam game. Results are keyed by appid as a string.

    Raises ScanStopped once should_stop returns true, so the plugin can unload mid-scan.
    """
    heroic = load_heroic_installs(home)
    instances = mo2_instances(home)
    measured: dict[str, int] = {}

    def size_of(paths: list[str]) -> int:
        for path in paths:
            if path not in measured:
                measured[path] = measure(path, should_stop)
        return sum(measured[path] for path in paths)

    steam_games = scan_steam(home, instances, size_of)
    sizes = {}
    unsized = {}
    counted = set()
    for appid, entry in load_shortcuts(home).items():
        name = entry.get("appname") or str(appid)
        game = _steam_game(entry, steam_games)
        if game:
            sizes[str(appid)] = {"name": name, "bytes": game["base"] + game["mods"], "base": game["base"],
                                 "mods": game["mods"], "kind": "steam-game", "paths": []}
            continue
        start = (entry.get("startdir") or "").strip('"').rstrip("/")
        special = _resolve_mo2(start, instances) or _resolve_openmw(start, home)
        kind, base_paths, mod_paths = special or (*resolve(entry, home, heroic), [])
        base, mods = size_of(base_paths), size_of(mod_paths)
        if base + mods > 0:
            sizes[str(appid)] = {"name": name, "bytes": base + mods, "base": base, "mods": mods,
                                 "kind": kind, "paths": base_paths + mod_paths}
            counted.update(base_paths + mod_paths)
        else:
            unsized[str(appid)] = {"name": name, "kind": kind}
    steam = {game["appid"]: {"name": game["name"], "base": game["base"], "mods": game["mods"]}
             for game in steam_games.values()}
    # Shortcuts can share a folder, so the total counts each folder only once.
    return {"sizes": sizes, "unsized": unsized, "steam": steam,
            "total_bytes": sum(measured[path] for path in counted)}
