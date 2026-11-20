# Changelog

All notable changes to Hoard. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and versions follow [Semantic Versioning](https://semver.org/).

## [0.4.0] - 2026-11-20

### Added

- **Enable Hoard** at the top of the Quick Access panel. Off, Hoard changes nothing in Steam
  and pauses its scans, without disabling the plugin in Decky.
- A **Features** section with a switch for each feature: the size on the game page,
  **Include mods in sorting** and **Non-Steam scanning**.
- A Ko-fi link and Hoard's version at the bottom of the panel.
- **Check for updates**, off by default. Once a day, and on **Check now**, Hoard asks GitHub for
  the latest release and shows whether an update is available, how to install it, and a button
  to its release page. It is Hoard's only network access; the README lists the exact request.

- Counts take only games: emulators, apps and tools such as Proton are left out, while disk
  totals still take everything. Each entry has a kind, decided in one place (`classify.py`).
- **Biggest games** in the panel: the ten largest games, mods included, from any source.
  Selecting one opens its game page.
- **Game or not** in the panel, to count an entry as a game or not when Hoard gets it wrong.
- **Not played in X months** in the panel: installed games not played for a number of months you
  choose, largest first, with the space they take together. It uses Steam's own last-played
  time, and games without one are listed apart rather than guessed.
- **Biggest games** and **Not played** each have a switch under Features.
- **Mods** in the panel: games with mods, most first, with the mods' share of the game and each
  folder they are in. Files Steam didn't install are listed apart, since they can be the game's own.
- **Piles**, off by default: Steam collections that Hoard keeps up to date, for games over a
  size you set, games not played for a while, games with mods, and every game on disk. Each is
  named for the device, changed only by the id Hoard stored, and removed only after you confirm.
- **Clean-up**: leftover shader caches of games no longer installed, found in a dry run and
  removed only after you confirm the exact folders, with a log. Leftover Proton prefixes are
  listed but never removed, since they can hold saves. Nothing happens while a library is missing.
- Biggest games, Not played and Mods start folded to one summary line each, so the rest of the
  panel is a few D-pad presses away.
- A mod location issue template, and a README table of every place Hoard looks for mods.
- Automatic scans skip Steam games without mods that haven't changed since they were last
  measured, for up to a week. **Rescan now** still measures everything.

### Fixed

- A Mod Organizer shortcut for a Steam game, such as Skyrim, was listed next to the Steam game
  itself, so the game showed up twice in Biggest games, Not played and Mods.

### Changed

- The game page shows `(mods —)` instead of `(no mods)` for games no mod rule covers, such as
  ROMs and folder games: Hoard doesn't know, which is not the same as none.
- The cache is rescanned once after updating, because its entries now carry a kind. The way a
  shortcut was found is now called its `source`.
- **Use in library sort** is now **Include mods in sorting**. The saved setting is kept.

## [0.3.2] - 2026-11-18

### Fixed

- Disabling, updating or uninstalling Hoard during a scan no longer takes 5 seconds and
  ends with Decky killing the backend. The scan now stops between folders.

## [0.3.1] - 2026-11-16

### Fixed

- The release zip is named `Hoard.zip`. Decky finds the installed plugin to replace by the
  zip's file name, so `Hoard-0.3.0.zip` left an earlier Hoard in another folder installed
  next to the new one.
- The README's install steps use Decky's exact labels and a link that always points to the
  latest release.

## [0.3.0] - 2026-11-16

The first public release, as a zip on GitHub Releases.

### Changed

- Renamed from Non-Steam Sizes to Hoard. Installed from the release zip, the plugin lives in
  `~/homebrew/plugins/Hoard/` and keeps its cache and settings in `~/homebrew/settings/Hoard/`,
  so an earlier install starts with a fresh scan and the default settings.
- The frontend is rewritten in TypeScript on Decky's plugin template and built with rollup.

### Added

- **Use in library sort** setting, on by default, to keep Steam's own sizes in the library sort
  and filters.
- Logo and store image.
- Release zip, CI and release workflows, and a README.

## [0.2.2] - 2026-11-12

Not published.

### Fixed

- One unreadable Mod Organizer folder no longer fails the whole scan.
- Installing or uninstalling a Steam game now triggers a rescan.

### Added

- A console warning when the game page has no stats row to show the size in.

## [0.2.1] - 2026-11-05

Not published. The first version, then called Non-Steam Sizes.

### Added

- Size on disk for non-Steam shortcuts, and base game plus mods for Steam games, on the game page.
- Those sizes in Steam's sort by size on disk and size filters.
- Quick Access panel with totals and a rescan button.

[0.4.0]: https://github.com/godvig/decky-hoard/releases/tag/v0.4.0
[0.3.2]: https://github.com/godvig/decky-hoard/releases/tag/v0.3.2
[0.3.1]: https://github.com/godvig/decky-hoard/releases/tag/v0.3.1
[0.3.0]: https://github.com/godvig/decky-hoard/releases/tag/v0.3.0
