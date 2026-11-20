"""Leftover shader caches that Hoard may remove, and leftover Proton prefixes it only lists.

This is the one place Hoard deletes anything. The rules, all checked again right before a
removal rather than taken from an earlier list:

- Only folders directly in a library's steamapps/shadercache, named by an appid that no
  library lists as installed and no shortcut on any Steam account on the device uses.
- Nothing at all while a library in libraryfolders.vdf is missing, such as an SD card that
  isn't inserted, since its games would look uninstalled.
- Never a symlink, and never compatdata: a Proton prefix can hold saves and settings, so
  prefixes are listed with their size and left alone.
- Game folders are never touched; removing a game is Steam's own Uninstall.
"""

import os
import re
import shutil
import time

import scanner

TOKEN = re.compile(r'"((?:[^"\\]|\\.)*)"|([{}])')


def parse_vdf(text: str) -> dict:
    """Steam's text key-value format, as nested dicts. Unbalanced input yields what was read."""
    root: dict = {}
    stack = [root]
    key = None
    for quoted, brace in TOKEN.findall(text):
        if brace == "{":
            child: dict = {}
            if key is not None:
                stack[-1][key] = child
            stack.append(child)
            key = None
        elif brace == "}":
            if len(stack) > 1:
                stack.pop()
            key = None
        elif key is None:
            key = quoted
        else:
            stack[-1][key] = quoted
            key = None
    return root


def libraries(home: str) -> list[dict]:
    """Each Steam library with the appids it lists as installed and whether it is there now."""
    steam = os.path.join(home, ".local/share/Steam")
    try:
        with open(os.path.join(steam, "steamapps/libraryfolders.vdf"), errors="replace") as f:
            folders = parse_vdf(f.read()).get("libraryfolders", {})
    except OSError:
        folders = {}
    found = {}
    for entry in folders.values():
        if isinstance(entry, dict) and isinstance(entry.get("path"), str):
            apps = entry.get("apps")
            found[entry["path"]] = set(apps) if isinstance(apps, dict) else set()
    found.setdefault(steam, set())
    result = []
    for path, apps in found.items():
        steamapps = os.path.join(path, "steamapps")
        # A manifest counts too, in case libraryfolders.vdf is behind.
        for manifest in os.listdir(steamapps) if os.path.isdir(steamapps) else []:
            match = re.fullmatch(r"appmanifest_(\d+)\.acf", manifest)
            if match:
                apps.add(match.group(1))
        result.append({"path": path, "present": os.path.isdir(steamapps), "apps": apps})
    return result


def shortcut_ids(home: str) -> set[str]:
    # compatdata and shadercache name a shortcut by its appid as an unsigned 32-bit number.
    return {str(appid & 0xFFFFFFFF) for appid in scanner.load_shortcuts(home)}


def _leftover_folders(steamapps: str, kind: str, keep: set[str]) -> list[str]:
    folder = os.path.join(steamapps, kind)
    try:
        names = sorted(os.listdir(folder))
    except OSError:
        return []
    return [os.path.join(folder, name) for name in names
            if name.isdigit() and name not in keep and not os.path.islink(os.path.join(folder, name))
            and os.path.isdir(os.path.join(folder, name))]


def find(home: str) -> dict:
    """What could be freed. A dry run: nothing is removed."""
    libs = libraries(home)
    missing = [lib["path"] for lib in libs if not lib["present"]]
    if missing:
        return {"ok": False, "missing": [scanner._shown_path(path, home) for path in missing],
                "shader": [], "prefixes": [], "shader_bytes": 0, "prefix_bytes": 0}
    keep = set().union(*(lib["apps"] for lib in libs)) | shortcut_ids(home)

    def entries(kind: str) -> list[dict]:
        found = []
        for lib in libs:
            for path in _leftover_folders(os.path.join(lib["path"], "steamapps"), kind, keep):
                found.append({"appid": os.path.basename(path), "path": path,
                              "shown": scanner._shown_path(path, home), "bytes": scanner.measure(path)})
        return sorted(found, key=lambda entry: entry["bytes"], reverse=True)

    shader, prefixes = entries("shadercache"), entries("compatdata")
    return {"ok": True, "missing": [], "shader": shader, "prefixes": prefixes,
            "shader_bytes": sum(entry["bytes"] for entry in shader),
            "prefix_bytes": sum(entry["bytes"] for entry in prefixes)}


def remove_shader_caches(home: str, paths: list[str], log_path: str) -> dict:
    """Remove the given shader caches, but only those a fresh find still lists.

    The list the user confirmed may be minutes old: a game installed since then is kept.
    """
    fresh = find(home)
    if not fresh["ok"]:
        return {"removed": [], "bytes": 0, "skipped": list(paths), "missing": fresh["missing"]}
    allowed = {entry["path"]: entry for entry in fresh["shader"]}
    removed, skipped = [], []
    with open(log_path, "a") as log:
        for path in paths:
            entry = allowed.get(path)
            # Checked once more right here: a plain folder directly in a shadercache folder.
            if entry is None or os.path.islink(path) or os.path.basename(os.path.dirname(path)) != "shadercache":
                skipped.append(path)
                continue
            stamp = time.strftime("%Y-%m-%d %H:%M:%S")
            try:
                # rmtree removes links inside the folder, never what they point at.
                shutil.rmtree(path)
            except OSError as error:
                log.write(f"{stamp}\tfailed\t{entry['bytes']}\t{path}\t{error}\n")
                skipped.append(path)
                continue
            removed.append(entry)
            log.write(f"{stamp}\tremoved\t{entry['bytes']}\t{path}\n")
    return {"removed": [entry["shown"] for entry in removed], "bytes": sum(entry["bytes"] for entry in removed),
            "skipped": [scanner._shown_path(path, home) for path in skipped], "missing": []}
