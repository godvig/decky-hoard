# Changelog

All notable changes to Hoard. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and versions follow [Semantic Versioning](https://semver.org/).

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

[0.3.0]: https://github.com/godvig/decky-hoard/releases/tag/v0.3.0
