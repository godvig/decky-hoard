# Hoard

A [Decky Loader](https://github.com/SteamDeckHomebrew/decky-loader) plugin that shows how much
disk space each game really uses, mods included, for Steam and non-Steam games alike.

Steam only knows the size of what it downloaded itself. A non-Steam shortcut shows no size at
all, and a Steam game with Workshop items, a Mod Organizer setup or loose mod files shows only
its base install. Hoard measures those folders and puts the result where you already look: the
game page, and Steam's own sort by size on disk.

<!-- GIF: the game page with "Size on disk" in the stats row, then the Quick Access panel. -->
*A demo GIF goes here.*

## Install

Hoard is distributed as a zip on [GitHub Releases](https://github.com/godvig/decky-hoard/releases),
not through the Decky store. You need Decky Loader 3 with developer mode on.

1. Open Quick Access → Decky → the gear icon, and turn on **Developer mode** under General.
2. Open the **Developer** page in Decky's settings. Under Third-Party Plugins, either:
   - enter this link at **Install Plugin from URL** and press **Install**:
     `https://github.com/godvig/decky-hoard/releases/latest/download/Hoard.zip`
   - or download `Hoard.zip` from the latest release, then press **Browse** at
     **Install Plugin from ZIP File** and pick it.
3. Accept Decky's warning about third-party plugins and confirm the install.
4. Hoard shows up in the Decky tab of Quick Access and starts its first scan.

**Updates are manual.** The Decky store doesn't know about Hoard, so it won't offer updates.
Turn on **Check for updates** in Hoard's Features to hear about new releases, or watch the
repository's releases on GitHub, and install again the same way. The link above always points to the latest release. Keep the file name `Hoard.zip`:
Decky looks for the installed Hoard to replace by the zip's file name.

## Features

- **Size on disk on the game page.** A stat in the row with Last Played and Play Time, for
  example `11.0 GB game + 2.3 GB mods`. On narrow screens it drops the word "game".
- **Sizes for non-Steam games.** Each shortcut is traced to its files, in this order: a Steam
  game folder it points into, a Mod Organizer 2 instance, OpenMW, Heroic, a ROM or file path in
  the launch options, the start folder, a Flatpak, the executable. A folder under `~/Games` is
  widened to its top folder, and folders shared by several shortcuts are counted once in totals.
- **Mods for Steam games.** Steam Workshop content, the `mods`, `overwrite` and `downloads`
  folders of a Mod Organizer instance for that game, and loose files in the game folder beyond
  what Steam installed (only when they add up to 10 MiB or more).
- **Library sort and filters.** Steam's sort by size on disk and its size filters include
  non-Steam games and mods. This changes Steam's numbers in memory only, never in Steam's files,
  and puts them back when Hoard unloads. Turn it off with **Include mods in sorting**.
- **Only games are counted.** Hoard sorts every entry into game, app, emulator or tool, and
  counts and rankings take only games: `Sized 160 of 161 games`, not 169 of 192. Disk totals
  still take everything. See [What counts as a game](#what-counts-as-a-game).
- **Biggest games.** The ten largest games in the panel, mods included, from Steam and non-Steam
  alike, with where each one comes from. Select one to open its game page.
- **Game or not.** A list in the panel of everything that isn't counted as a game, or that Hoard
  only guessed is one, each with a switch to count it or not. **Show more** lists the rest.
- **Quick Access panel.** How many non-Steam games are sized, the shortcuts' total, the last scan time, and
  **Rescan now**. Under **Features**, each feature has its own switch: the size on the game
  page, **Include mods in sorting**, and **Non-Steam scanning**. With non-Steam scanning off,
  shortcuts are neither measured nor shown; their last sizes are kept and refreshed when it's
  turned back on.
- **Enable Hoard.** The switch at the top of the panel. Off, Hoard changes nothing in Steam:
  no size on the game page, Steam's own sizes in the sort and filters, and no scans. On, it all
  comes back without a restart. Unlike disabling Hoard in Decky's settings, the panel stays
  there to turn it back on, and the setting is kept across restarts.
- **Quiet background scans.** Every 15 minutes Hoard checks whether to rescan: after 24 hours,
  or when a shortcut or a Steam library changed. Scans run at the lowest CPU priority so they
  stay out of a running game's way.
- **Update check, off by default.** Turn on **Check for updates** under Features, and Hoard asks
  GitHub once a day, and when you press **Check now**, whether a newer release exists. If so, the
  panel shows `Update available: vX.Y.Z`, how to install it, and a button that opens the release
  page. Hoard never downloads or installs anything itself.
- **No other network access.** The backend uses only Python's standard library and reads local
  files. See [Network access](#network-access) for the one request Hoard can make.

Known limits: loose files in a Steam game folder can include files the game made itself, such
as logs or shader caches, and they count as mods. A Steam game installed after the last scan
shows Steam's own size until the next scan.

## What counts as a game

One function, `classify.py`, decides it, and every count goes through it. In this order:

1. Your own choice under **Game or not**.
2. For Steam apps, Steam's own app type: game or tool (Proton, Steam Linux Runtime,
   redistributables). Until the frontend has passed Steam's types on, those tools are known by name.
3. For non-Steam shortcuts, how they launch:
   - a ROM on an emulator's command line is a game, even when the file has gone missing;
     an EmuDeck launcher (`~/Emulation/tools/launchers/`) on its own is an emulator;
   - a Heroic game, a Mod Organizer instance, OpenMW, or a shortcut into a Steam game is a game;
   - a web page in a browser, a bare system command such as `claude-desktop`, an installer
     (`setup.exe`, `Install.exe`), EmuDeck itself and Minecraft launchers are apps;
   - a Flatpak that is a known emulator, browser, launcher or app is that, and other Flatpaks,
     folders and files are games;
   - anything else counts as a game but is marked as guessed.

Shortcuts from every Steam account on the device are counted. If Hoard gets one of yours wrong,
switch it under **Game or not**, and open an issue with how the shortcut launches.

## Architecture

| Part | Files | Job |
|---|---|---|
| Update check | `updates.py` | Asks GitHub for the latest release's version and compares it with the installed one. Pure functions except the one request. |
| Classifier | `classify.py` | Decides what each entry is, and builds the counts, the biggest games and the game-or-not list from that. Pure functions. |
| Scanner | `scanner.py` | Reads `shortcuts.vdf`, Steam's library folders and app manifests, Mod Organizer, OpenMW and Heroic config, and measures folders. Pure functions, no Decky imports. |
| Backend | `main.py` | Decky plugin class. Runs the scan watcher in a thread, caches results, stores settings, emits `sizes_updated`. |
| Frontend | `src/` | `index.tsx` wires up the plugin and the Quick Access panel, `gamePage.tsx` patches the game page route, `sortOverride.ts` changes Steam's size fields, `sizes.ts` holds formatting and state, `settings.ts` decides which features are on, `strings.ts` holds every UI string. |

The backend writes `sizes.json` and `settings.json` to `DECKY_PLUGIN_SETTINGS_DIR`, which Decky
puts at `~/homebrew/settings/Hoard/`. The frontend asks for the cache when it loads and again
on every `sizes_updated` event.

The game page stat is portaled into Steam's stats row rather than added between the header and
the play bar. Themes such as Clean Gameview size the page to fit exactly and paint the hero
image over that gap, so anything placed there would hide the Play button.

`docs/DEBUG-NOTES.md` has the longer write-up, and `docs/TEST-MATRIX.md` the manual checks run
in Gaming Mode.

## Network access

With **Check for updates** off, which is the default, Hoard makes no network requests at all.
With it on, the backend (`updates.py`) makes this one request, at most once a day and when
you press **Check now**, and not while **Enable Hoard** is off:

```
GET https://api.github.com/repos/godvig/decky-hoard/releases/latest
Accept: application/vnd.github+json
User-Agent: Hoard
```

It sends no cookies, tokens, Steam IDs, Hoard version or anything about your library. From the
reply it reads only `tag_name`. The link behind **Open release page** is built from that version,
not taken from the reply. When offline, the check fails quietly and tries again a day later.
The time of the last attempt and the version found are kept in `updates.json` next to Hoard's
settings.

## Compatibility

- Decky Loader 3 (developed on 3.3.1) on SteamOS.
- Developed on a Steam Machine. The game page layout was checked at Steam Deck size (1280×800)
  in Big Picture, not on Steam Deck hardware.
- Hoard depends on Steam's internal class names for the game page through `@decky/ui`. If a
  Steam update renames them, the stat disappears and Hoard logs
  `[Hoard] stats row not found on the game page` in the console. The sort override and the
  Quick Access panel keep working.

## Tests and development

You need Node.js, pnpm 9, Python 3 and `zip`.

```bash
pnpm install
pnpm lint && pnpm typecheck && pnpm test
python3 -m venv .venv && .venv/bin/pip install pytest && .venv/bin/python -m pytest -q
pnpm zip
```

`pnpm test` runs the vitest tests in `src/`, and pytest runs `tests/` against fake Steam, Mod
Organizer and game folders. `pnpm zip` builds the frontend and writes `build/Hoard.zip`.
CI runs all of these on every pull request. Pushing a tag such as `v0.3.0`, matching the
version in `package.json`, publishes a release with the zip attached.

## Roadmap

Hoard is about storage: how big each game really is, what takes the space, and what can go.

- Finish the Gaming Mode checks in `docs/TEST-MATRIX.md` on more themes and storage setups.
- Faster rescans that measure only the games that changed.
- Installed games not played for a chosen number of months, with the space they take.
- An overview of the mods Hoard found for each game.
- Opt-in Steam collections from Hoard's data, such as games over 50 GB.
- Clean-up of leftover shader caches for games that are no longer installed.
- Submission to the Decky store.

## Support

Report bugs and ask for features in [GitHub issues](https://github.com/godvig/decky-hoard/issues).
For a bug, include the game, how it was added to Steam, and the end of the plugin log:

```bash
tail -50 ~/homebrew/logs/Hoard/"$(ls -t ~/homebrew/logs/Hoard | head -1)"
```

If Hoard saved you from a full drive, you can [buy me a coffee](https://ko-fi.com/godvig?ref=hoard).

## About

Hoard was built with AI assistance. The architecture and decisions are the author's.

## License

[BSD-3-Clause](LICENSE). Copyright (c) 2026, Adam Englund.
