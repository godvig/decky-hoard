# Hoard

<p align="center"><img src="assets/store.png" alt="Hoard logo: a dragon resting on a stack of drives" width="200"></p>

A [Decky Loader](https://github.com/SteamDeckHomebrew/decky-loader) plugin that shows how much
disk space each game really uses, mods included, for Steam and non-Steam games alike.

Steam only knows the size of what it downloaded itself. A non-Steam shortcut shows no size at
all, and a Steam game with Workshop items, a Mod Organizer setup or loose mod files shows only
its base install. Hoard measures those folders and puts the result where you already look: the
game page, and Steam's own sort by size on disk.

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
- **Mods.** Found only where a rule says to look, listed under
  [Where Hoard looks for mods](#where-hoard-looks-for-mods). For a game no rule covers, such as a
  ROM or a folder game, the game page says `(mods —)`: unknown, not none.
- **Mods overview.** The games with mods in the panel, most mods first, each with the mods' size,
  their share of the game, and where they are. Press A on a game for each folder and its size.
- **Library sort and filters.** Steam's sort by size on disk and its size filters include
  non-Steam games and mods. This changes Steam's numbers in memory only, never in Steam's files,
  and puts them back when Hoard unloads. Turn it off with **Include mods in sorting**.
- **Only games are counted.** Hoard sorts every entry into game, app, emulator or tool, and
  counts and rankings take only games: `Sized 160 of 161 games`, not 169 of 192. Disk totals
  still take everything. See [What counts as a game](#what-counts-as-a-game).
- **Biggest games.** The ten largest games in the panel, mods included, from Steam and non-Steam
  alike, with where each one comes from. Select one to open its game page.
- **Not played in X months.** Installed games you haven't played for a number of months that
  you choose (1 to 36, 6 by default), largest first, and how much space they take together.
  The time is Steam's own last-played time; Hoard doesn't track play time itself. Games Steam
  has no time for, because they were never played or belong to another Steam account, are
  listed apart under **No play time recorded** and never counted as old. Selecting a game opens
  its page, where Steam's own Uninstall is: Hoard removes nothing here. If another plugin, such
  as Shared Play Stats, fills in last-played times from other local accounts, Hoard sees those
  times too.
- **Piles, off by default.** Steam collections that Hoard keeps up to date from its own data:
  **Over 50 GB** (the size is yours to set), **Not played in X months**, **Has mods** and
  **On disk**, which holds every installed game, family-shared and non-Steam ones included. Turn
  each one on by itself. See [Piles](#piles).
- **Short panel.** Biggest games, Not played and Mods each show one summary line, such as
  `Largest: XCOM 2, 206.7 GB`, until you open them, so the D-pad passes each list in one step.
- **Clean-up.** Finds leftovers of games that are no longer installed: shader caches, which
  Hoard can remove, and Proton prefixes, which it only lists because they can hold saves. See
  [Clean-up](#clean-up).
- **Game or not.** A list in the panel of everything that isn't counted as a game, or that Hoard
  only guessed is one, each with a switch to count it or not. **Show more** lists the rest.
- **Quick Access panel.** How many non-Steam games are sized, the shortcuts' total, the last scan time, and
  **Rescan now**. Under **Features**, each feature has its own switch: the size on the game
  page, **Include mods in sorting**, **Non-Steam scanning**, **Biggest games**, **Not played**,
  **Mods** and **Check for updates**. Piles have their own section. With non-Steam scanning off,
  shortcuts are neither measured nor shown; their last sizes are kept and refreshed when it's
  turned back on.
- **Enable Hoard.** The switch at the top of the panel. Off, Hoard changes nothing in Steam:
  no size on the game page, Steam's own sizes in the sort and filters, and no scans. On, it all
  comes back without a restart. Unlike disabling Hoard in Decky's settings, the panel stays
  there to turn it back on, and the setting is kept across restarts.
- **Quiet background scans.** Every 15 minutes Hoard checks whether to rescan: after 24 hours,
  or when a shortcut or a Steam library changed. Scans run at the lowest CPU priority so they
  stay out of a running game's way. A Steam game without mods whose app manifest, game folder
  and Workshop folder haven't changed keeps its last measurement for up to a week, so its folder
  isn't walked again. Games with mods and non-Steam shortcuts are measured every time, and
  **Rescan now** measures everything.
- **Update check, off by default.** Turn on **Check for updates** under Features, and Hoard asks
  GitHub once a day, and when you press **Check now**, whether a newer release exists. If so, the
  panel shows `Update available: vX.Y.Z`, how to install it, and a button that opens the release
  page. Hoard never downloads or installs anything itself.
- **No other network access.** The backend uses only Python's standard library and reads local
  files. See [Network access](#network-access) for the one request Hoard can make.

Known limits: loose files in a Steam game folder can include files the game made itself, such
as logs or shader caches, and they count as mods; the mods overview lists them apart. A Steam game installed after the last scan
shows Steam's own size until the next scan. A mod copied deep into a Steam game that had none,
without touching the game folder itself, can go unnoticed for up to a week; **Rescan now**
picks it up at once.

## Piles

A pile is an ordinary Steam collection, so it shows up in the library's **Collections** tab (on
the desktop, in the library's left column) and can be used like any other. Steam doesn't give a
collection a tab of its own: for a pile as a tab next to Installed and Non-Steam, use a tab plugin
such as TabMaster and add a tab that shows that collection. Hoard itself never adds, hides or
reorders tabs. How Hoard handles them:

- **Only its own.** Hoard stores the id Steam gives each collection it makes, and only ever
  changes or removes a collection by that id. It never looks collections up by name, never
  touches yours, and never hides, reorders or removes library tabs or changes whether Steam
  thinks a game is installed.
- **Per device.** Steam syncs collections to your account, so each pile's name ends with the
  device it describes, such as `Over 50 GB · Steam Machine (Hoard)`. The name comes from the
  device's model; change it under **Device name** in the panel. Steam keeps a collection's
  non-Steam games on the device that added them, so on another device a pile shows its Steam
  games only.
- **Quiet writes.** Hoard writes a pile only when its games changed, three seconds after the
  last change, so moving the size slider doesn't write on every step. A new size or device
  name replaces Hoard's collection with a newly named one.
- **Turning a pile off** removes its collection from Steam, on every device on the account,
  after you confirm. The games stay installed. Deleting a pile's collection in Steam yourself
  turns that pile off in Hoard.
- **With Enable Hoard off,** piles stay in Steam as they were and aren't updated.
- **If Steam changes.** Collections go through an internal Steam API. If it is missing or
  doesn't behave as Hoard expects, Piles pause for the session, log one line, and change
  nothing more.

## Clean-up

This is the only part of Hoard that removes anything, and it follows these rules:

- **A dry run first.** **Find leftovers** lists what it found and changes nothing.
- **Exact paths.** **Remove** shows every folder it will remove and the total, and waits for you
  to confirm.
- **Shader caches only.** A folder in a library's `steamapps/shadercache` is removed only when
  its appid is installed in no library and used by no non-Steam shortcut on any Steam account on
  the device. Steam rebuilds a shader cache if the game comes back.
- **Proton prefixes are never removed.** Folders in `steamapps/compatdata` for apps that aren't
  installed are listed with their size, because a prefix can hold saves and settings that Steam
  Cloud doesn't keep. Leftover prefixes often come from non-Steam shortcuts that were made again,
  which gives them a new id.
- **Nothing while a library is missing.** If a library in `libraryfolders.vdf` isn't there, such
  as an SD card that isn't inserted, Clean-up lists nothing, since its games would look
  uninstalled.
- **Checked again at removal.** Right before removing, Hoard looks again and keeps any folder
  that no longer qualifies, for example for a game installed since the list was made. It never
  follows a symlink.
- **Logged.** Every removed folder is written, with its size and time, to
  `~/homebrew/settings/Hoard/cleanup.log`.
- **Game folders are never touched.** To remove a game, use Steam's own Uninstall.

## Where Hoard looks for mods

| Game or manager | Where | Shown as |
|---|---|---|
| Any Steam game | `steamapps/workshop/content/<appid>` in the game's library | Steam Workshop |
| Any Steam game | Files in the game folder beyond the manifest's `SizeOnDisk`, when they add up to 10 MiB or more | Other files in the game folder |
| Mod Organizer 2 (a Steam game or a shortcut) | The instance's `mods`, `overwrite` and `downloads` folders | Mod Organizer |
| OpenMW | Every `data=` folder in `~/.config/openmw/openmw.cfg` other than the one with `Morrowind.esm`, and a `-cache` folder next to each | OpenMW |

"Other files in the game folder" is the one rule that can be wrong: it also catches files the
game made itself, such as logs and shader caches, and the overview says so. Paths are shown with
`~` for your home folder.

Mods somewhere else? Open a [mod location request](https://github.com/godvig/decky-hoard/issues/new?template=mod_location.yml)
with the game, the mod manager and the folders. Hoard adds a rule only for a place it can name exactly.

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
| Clean-up | `cleanup.py` | Finds leftover shader caches and Proton prefixes, and removes shader caches by the rules under Clean-up. The only code that deletes anything. |
| Classifier | `classify.py` | Decides what each entry is, and builds the counts, the biggest games, the not-played list and the game-or-not list from that. Pure functions. |
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
