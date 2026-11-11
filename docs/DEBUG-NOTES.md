# Debug notes (v0.2.1)

Written 2026-11-11 after reading the code and checking the running Steam client
over its CEF debug port (localhost:8080). The release plan listed two bugs as
hypotheses written without seeing the code: (A) no size for regular Steam games,
(B) the injected label hides the Play row. **Neither shows up in v0.2.1.**

## How sizes are computed (backend)

- `main.py` runs a watcher every 15 min. It rescans when the cache is older than
  24 h, when any `shortcuts.vdf` changed, or when the cache predates mod sizes.
  Scans run in a thread (`asyncio.to_thread`) at `nice 19`, and the result is
  cached in `DECKY_PLUGIN_SETTINGS_DIR/sizes.json`. `sizes_updated` is emitted after each scan.
- `scanner.scan_steam` reads every library in `steamapps/libraryfolders.vdf`
  plus the primary one. Base size is the manifest's `SizeOnDisk`. Mods are
  workshop content, the Mod Organizer folders of an instance pointed at that
  game, and loose files in the game folder beyond `SizeOnDisk` (only when
  ≥ 10 MB, so logs and configs don't count). This walks every installed game
  folder, which is why a scan takes ~8–25 s here.
- `scanner.scan` resolves each shortcut in this order: inside a Steam game
  folder → reuse that game; Mod Organizer instance; OpenMW; Heroic; ROM or file
  path in the launch options; web link (no size); start folder; Flatpak; exe.
  A folder under `~/Games` is widened to its top folder. Folders shared between
  shortcuts are only counted once in `total_bytes`.

## How the frontend shows it

- `dist/index.js` is hand-written (no build step, no source elsewhere).
- Sort/filter: it overwrites `overview.size_on_disk` in `appStore` in memory,
  for shortcuts (`app_type` 1073741824) and for Steam games (`app_type` 1) that
  have mods. The original value is restored on unload.
- Game page: a router patch on `/library/app/:appid` **pushes** a `SizeStat`
  element into the `InnerContainer` children (insert, never replace, guarded by
  a key). `SizeStat` renders only a hidden span and portals the real stat into
  Steam's `GameStatsSection` (the Last Played / Play Time row), found with a
  MutationObserver. If that row is missing it renders nothing.
- Appid type: both kinds look up by `overview.appid` (number) in objects keyed by
  string, which JavaScript coerces, so Steam and non-Steam use the same path.

## Status of the planned bugs

**A — size missing for Steam games: fixed.** The cache holds 44 Steam apps and
169 shortcuts, with 23 shortcuts left unsized. Live check: Hades II
(1145350, type 1) has `size_on_disk` 11774185682, the same value as the cache.
A Steam game installed after the last scan still shows Steam's own number
(the `sizeText` fallback).

**B — Play row disappears: not reproducible from the code.** Nothing is replaced
or indexed. The likely earlier cause was an element placed between the header
and the play bar, which themes such as Clean Gameview paint over or push off
screen. That is why the stat now lives inside the stats row. Still has to be
confirmed by eye in Gaming Mode, see `TEST-MATRIX.md`.

## Real risks found while reading

1. `playSectionClasses.GameStatsSection` / `appDetailsClasses.InnerContainer`
   are Steam's minified class names via @decky/ui. If Steam changes them, the
   label vanishes quietly. Add a one-time `console.warn` when the row isn't found
   within a few seconds.
2. `_resolve_mo2` calls `os.listdir(start)` without catching `OSError`. One
   unreadable instance folder makes the whole scan fail ("scan failed" in the
   log), not just that game.
3. A newly installed or uninstalled Steam game doesn't trigger a rescan (only
   `shortcuts.vdf` mtimes are watched). Watching the `steamapps` folders' mtimes would fix it.
4. Tools such as Proton and Steam Linux Runtime are sized too. Harmless, but
   they would show up in a future "Biggest games" list.

## Gaps before store submission

- The frontend uses `window.__DECKY_SECRET_INTERNALS_..._deckyLoaderAPIInit`
  directly instead of `@decky/api`, and has no source or build. The store CI
  builds from the template (TypeScript + rollup, pnpm 9, lockfile 9.0), so the
  frontend has to be ported to `src/index.tsx` on the decky-plugin-template.
- `package.json` says MIT and `plugin.json` says author "deck". Both have to change to the
  BSD-3-Clause decision and a real author. There is no `LICENSE` file yet.
- Name: "Non-Steam Sizes" no longer fits (it does Steam games too). Rename
  when the toolkit name is chosen.
- `plugin.json` `publish.image` is empty, and the store needs a PNG.

## Tests

`tests/test_scanner.py` covers synthetic Steam libraries, second library,
workshop and loose mods, broken/uninstalled manifests, folder and unknown
shortcuts, shortcut inside a Steam game, Mod Organizer, and symlinks.

```bash
python3 -m venv .venv && .venv/bin/pip install pytest && .venv/bin/pytest -q tests
```
