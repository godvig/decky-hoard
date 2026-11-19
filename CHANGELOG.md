# Changelog

All notable changes to Hoard. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and versions follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- **Enable Hoard** at the top of the Quick Access panel. Off, Hoard changes nothing in Steam
  and pauses its scans, without disabling the plugin in Decky.
- A **Features** section with a switch for each feature: the size on the game page,
  **Include mods in sorting** and **Non-Steam scanning**.
- A Ko-fi link and Hoard's version at the bottom of the panel.
- **Check for updates**, off by default. Once a day, and on **Check now**, Hoard asks GitHub for
  the latest release and shows whether an update is available, how to install it, and a button
  to its release page. It is Hoard's only network access; the README lists the exact request.

### Changed

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

[0.3.2]: https://github.com/godvig/decky-hoard/releases/tag/v0.3.2
[0.3.1]: https://github.com/godvig/decky-hoard/releases/tag/v0.3.1
[0.3.0]: https://github.com/godvig/decky-hoard/releases/tag/v0.3.0
