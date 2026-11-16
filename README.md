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
Watch the repository's releases on GitHub to hear about new ones, and install again the same
way. The link above always points to the latest release. Keep the file name `Hoard.zip`:
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
  and puts them back when Hoard unloads. Turn it off with **Use in library sort**.
- **Quick Access panel.** How many shortcuts are sized, their total, the last scan time, and
  **Rescan now**.
- **Quiet background scans.** Every 15 minutes Hoard checks whether to rescan: after 24 hours,
  or when a shortcut or a Steam library changed. Scans run at the lowest CPU priority so they
  stay out of a running game's way.
- **No network access.** The backend uses only Python's standard library and reads local files.

Known limits: loose files in a Steam game folder can include files the game made itself, such
as logs or shader caches, and they count as mods. A Steam game installed after the last scan
shows Steam's own size until the next scan.

## Architecture

| Part | Files | Job |
|---|---|---|
| Scanner | `scanner.py` | Reads `shortcuts.vdf`, Steam's library folders and app manifests, Mod Organizer, OpenMW and Heroic config, and measures folders. Pure functions, no Decky imports. |
| Backend | `main.py` | Decky plugin class. Runs the scan watcher in a thread, caches results, stores settings, emits `sizes_updated`. |
| Frontend | `src/` | `index.tsx` wires up the plugin and the Quick Access panel, `gamePage.tsx` patches the game page route, `sortOverride.ts` changes Steam's size fields, `sizes.ts` holds formatting and state. |

The backend writes `sizes.json` and `settings.json` to `DECKY_PLUGIN_SETTINGS_DIR`, which Decky
puts at `~/homebrew/settings/Hoard/`. The frontend asks for the cache when it loads and again
on every `sizes_updated` event.

The game page stat is portaled into Steam's stats row rather than added between the header and
the play bar. Themes such as Clean Gameview size the page to fit exactly and paint the hero
image over that gap, so anything placed there would hide the Play button.

`docs/DEBUG-NOTES.md` has the longer write-up, and `docs/TEST-MATRIX.md` the manual checks run
in Gaming Mode.

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

- Finish the Gaming Mode checks in `docs/TEST-MATRIX.md` on more themes and storage setups.
- A list of the biggest games, mods included, in the Quick Access panel.
- Submission to the Decky store.

## Support

Report bugs and ask for features in [GitHub issues](https://github.com/godvig/decky-hoard/issues).
For a bug, include the game, how it was added to Steam, and the end of the plugin log:

```bash
tail -50 ~/homebrew/logs/Hoard/"$(ls -t ~/homebrew/logs/Hoard | head -1)"
```

## About

Hoard was built with AI assistance. The architecture and decisions are the author's.

## License

[BSD-3-Clause](LICENSE). Copyright (c) 2026, Adam Englund.
