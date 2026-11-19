"""What each entry is: a game, an app, an emulator or a tool. Pure functions, no Decky imports.

Counts and rankings take only games; disk totals take everything. Every count goes through
is_game, so the rule lives in one place. Each rule below is documented in the README.
"""

import os
import re

KINDS = ("game", "app", "emulator", "tool")
STEAM_GAME_APP_TYPE = 1
STEAM_TOOL_APP_TYPE = 4
BIGGEST_COUNT = 10

# Used only when Steam hasn't told the frontend an app's type yet, such as on the first scan.
STEAM_TOOL_NAMES = re.compile(r"^(Proton\b|Steam Linux Runtime\b|Legacy Steam Runtime\b|"
                              r"Steamworks Common Redistributables\b)")

# Scanner sources that only ever point at a game.
GAME_SOURCES = ("rom", "heroic", "heroic-not-installed", "mod-organizer", "openmw", "steam-game")

EMULATOR_FLATPAKS = {
    "app.xemu.xemu", "io.github.shiiion.primehack", "info.cemu.Cemu", "io.mgba.mGBA",
    "net.kuribo64.melonDS", "net.pcsx2.PCSX2", "net.rpcs3.RPCS3", "net.shadps4.shadPS4",
    "org.azahar_emu.Azahar", "org.DolphinEmu.dolphin-emu", "org.duckstation.DuckStation",
    "org.libretro.RetroArch", "org.ppsspp.PPSSPP", "org.ryujinx.Ryujinx", "dev.ares.ares",
    "io.github.lime3ds.Lime3DS", "org.citra_emu.citra", "com.github.Vita3K.Vita3K",
}
APP_FLATPAKS = {
    # Browsers.
    "org.mozilla.firefox", "com.microsoft.Edge", "com.google.Chrome", "org.chromium.Chromium",
    "com.brave.Browser", "com.vivaldi.Vivaldi",
    # Launchers and frontends: the games they start are counted on their own.
    "com.heroicgameslauncher.hgl", "net.lutris.Lutris", "com.usebottles.bottles",
    "org.prismlauncher.PrismLauncher", "org.polymc.PolyMC", "com.valvesoftware.SteamLink",
    "org.es_de.frontend", "net.retrodeck.retrodeck",
    # Everything else people add to Steam.
    "net.ankiweb.Anki", "org.chessmd.chessmd", "tv.plex.PlexDesktop", "com.spotify.Client",
    "com.discordapp.Discord", "org.videolan.VLC",
}
# Executables that are apps however they were added.
APP_EXECUTABLES = re.compile(r"^(emudeck|polymc|prismlauncher|.*setup|install(er)?)(\.exe|\.appimage)?$",
                             re.IGNORECASE)
EMUDECK_LAUNCHERS = "/Emulation/tools/launchers/"
FLATPAK_ID = re.compile(r"\b[a-zA-Z][\w-]*(?:\.[\w-]+){2,}\b")


def shortcut_kind(program: str, options: str, source: str) -> tuple[str, bool]:
    """Kind of a non-Steam shortcut from how it launches, and whether that's only a guess.

    program and options are the shortcut's executable and its arguments, source is how the
    scanner found its files.
    """
    name = os.path.basename(program).lower()
    if source == "web":
        return "app", False
    if EMUDECK_LAUNCHERS in program:
        # A ROM on the command line makes it a game, even when that file has gone missing.
        return ("game" if "/Emulation/roms/" in options else "emulator"), False
    if source in GAME_SOURCES:
        return "game", False
    if APP_EXECUTABLES.match(name):
        return "app", False
    # Only when the shortcut is the Flatpak itself: a game run through Bottles is still a game.
    if name == "flatpak" and source in ("flatpak", "unknown"):
        ids = set(FLATPAK_ID.findall(options))
        if ids & EMULATOR_FLATPAKS:
            return "emulator", False
        if ids & APP_FLATPAKS:
            return "app", False
    # A bare command such as claude-desktop is a program installed on the system.
    if program and "/" not in program and name != "flatpak":
        return "app", False
    if source in ("folder", "file", "flatpak"):
        return "game", False
    return "game", True


def steam_kind(name: str, app_type: int | None) -> tuple[str, bool]:
    """Kind of an installed Steam app from Steam's own app type, or its name until that's known."""
    if app_type == STEAM_TOOL_APP_TYPE:
        return "tool", False
    if app_type == STEAM_GAME_APP_TYPE:
        return "game", False
    if STEAM_TOOL_NAMES.match(name):
        return "tool", False
    return "game", app_type is None


def is_game(item: dict) -> bool:
    return item.get("kind", "game") == "game"


def apply_kinds(cache: dict, app_types: dict[str, int], overrides: dict[str, str]) -> dict:
    """The cache with each entry's final kind and the counts built from it.

    An override from the user wins over Steam's app type, which wins over the rules.
    """
    result = dict(cache)
    for group in ("sizes", "unsized", "steam"):
        entries = {}
        for appid, item in cache.get(group, {}).items():
            item = dict(item)
            if group == "steam":
                item["kind"], item["guessed"] = steam_kind(item.get("name", ""), app_types.get(appid))
            item.setdefault("kind", "game")
            item.setdefault("guessed", False)
            item["overridden"] = overrides.get(appid) in KINDS
            if item["overridden"]:
                item["kind"], item["guessed"] = overrides[appid], False
            entries[appid] = item
        result[group] = entries
    games = [item for group in ("sizes", "unsized") for item in result[group].values() if is_game(item)]
    result["biggest"] = biggest_games(result)
    result["entries"] = entry_list(result)
    result["counts"] = {
        "shortcut_games": len(games),
        "sized_shortcut_games": sum(1 for appid, item in result["sizes"].items() if is_game(item)),
        "guessed": sum(1 for group in ("sizes", "unsized", "steam")
                       for item in result[group].values() if item["guessed"]),
    }
    return result


def biggest_games(result: dict, limit: int = BIGGEST_COUNT) -> list[dict]:
    """The largest games by size on disk, mods included, from Steam and shortcuts alike."""
    games = [{"appid": appid, "name": item["name"], "bytes": item["base"] + item["mods"], "mods": item["mods"],
              "source": "steam"}
             for appid, item in result.get("steam", {}).items() if is_game(item)]
    # A shortcut into a Steam game's folder is that same game, already listed above.
    games += [{"appid": appid, "name": item["name"], "bytes": item["bytes"], "mods": item.get("mods", 0),
               "source": item.get("source", "")}
              for appid, item in result.get("sizes", {}).items()
              if is_game(item) and item.get("source") != "steam-game"]
    return sorted(games, key=lambda game: game["bytes"], reverse=True)[:limit]


def entry_list(result: dict) -> list[dict]:
    """Every entry for the user to check: non-games and guesses first, then games, by name."""
    entries = [{"appid": appid, "name": item.get("name", appid), "kind": item["kind"], "guessed": item["guessed"],
                "overridden": item["overridden"], "review": not is_game(item) or item["guessed"]}
               for group in ("sizes", "unsized", "steam") for appid, item in result.get(group, {}).items()]
    return sorted(entries, key=lambda e: (not e["review"], e["name"].lower()))
