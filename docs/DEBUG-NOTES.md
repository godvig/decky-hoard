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

- Since v0.3.0 the frontend is TypeScript in `src/`, built with rollup (`pnpm build`) on
  decky-plugin-template: `index.tsx` (panel, wiring), `gamePage.tsx` (route patch and
  stat), `sortOverride.ts` (overview override, setting `sort_override`, default on),
  `sizes.ts` (pure formatting and state, unit tested).
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

## Risks found while reading (handled in v0.2.2)

1. `playSectionClasses.GameStatsSection` / `appDetailsClasses.InnerContainer`
   are Steam's minified class names via @decky/ui. If Steam changes them, the
   label vanishes. Now `console.warn` fires once per session when the
   row isn't on the game page after 5 s.
2. `_resolve_mo2` called `os.listdir(start)` without catching `OSError`, so one
   unreadable instance folder failed the whole scan. Now it is caught.
3. Installing or uninstalling a Steam game didn't trigger a rescan. `_needs_scan` now
   also watches each library's `steamapps` folder mtime (`scanner.watched_paths`).
   Steam rewrites manifests while downloading, so expect a rescan every 15 min
   during a download.
4. Tools such as Proton and Steam Linux Runtime are sized too. Harmless now: the
   frontend only touches overviews with `app_type` 1 (games). A future
   "Biggest games" list must filter on `app_type` the same way.

## Gaps before store submission

- Done in v0.3.0: template port with `@decky/api`, pnpm 9 lockfile, BSD-3-Clause
  LICENSE with the template's notice kept below, author and name "Hoard".
- `plugin.json` `publish.image` is still empty, and `assets/store.png` is a
  placeholder. Point it at the PNG's raw URL once the repo exists.
- The name "Hoard" is not checked against the store, GitHub or trademarks yet.

## Tests

`tests/test_scanner.py` covers synthetic Steam libraries, second library,
workshop and loose mods, broken/uninstalled manifests, folder and unknown
shortcuts, shortcut inside a Steam game, Mod Organizer, and symlinks.

```bash
pnpm lint && pnpm typecheck && pnpm test
python3 -m venv .venv && .venv/bin/pip install pytest && .venv/bin/pytest -q tests
```
