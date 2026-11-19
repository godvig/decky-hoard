// Every string Hoard shows, in one place.

export const KOFI_URL = "https://ko-fi.com/godvig?ref=hoard-panel";
export const INSTALL_URL = "https://github.com/godvig/decky-hoard/releases/latest/download/Hoard.zip";

export const strings = {
  enable: "Enable Hoard",
  enableDescription: "Off, Hoard changes nothing in Steam and pauses its scans.",
  offNotice: "Hoard is off. Steam shows its own sizes.",

  shortcutsTitle: "Non-Steam games",
  sized: "Sized",
  sizedOf: (sized: number, games: number) => `${sized} of ${games} games`,
  total: "Total",
  lastScan: "Last scan",
  notYet: "Not yet",
  shortcutsOff: "Non-Steam scanning is off.",
  rescan: "Rescan now",
  scanning: "Scanning...",

  biggestTitle: "Biggest games",
  noGames: "No games sized yet",
  withMods: (mods: string) => `${mods} of it mods`,
  sources: {
    steam: "Steam",
    "steam-game": "Steam",
    rom: "ROM",
    folder: "Folder",
    file: "Folder",
    heroic: "Heroic",
    flatpak: "Flatpak",
    "mod-organizer": "Mod Organizer",
    openmw: "OpenMW",
  } as Record<string, string>,

  gameOrNot: "Game or not",
  gameOrNotDescription: "Only games are counted and ranked. Disk totals take everything.",
  kinds: { game: "Game", app: "App", emulator: "Emulator", tool: "Tool" },
  guessed: "guessed",
  setByYou: "set by you",
  showAll: (count: number) => `Show ${count} more`,

  features: "Features",
  show: "Show",
  hide: "Hide",
  sizeLabel: "Size on the game page",
  sizeLabelDescription: "Shows size on disk, game + mods, next to Last Played and Play Time.",
  includeMods: "Include mods in sorting",
  includeModsDescription:
    "Sorting and filters by size on disk use the total size, game + mods, including non-Steam games.",
  scanShortcuts: "Non-Steam scanning",
  scanShortcutsDescription: "Measures the folders of non-Steam shortcuts.",
  checkUpdates: "Check for updates",
  checkUpdatesDescription:
    "Once a day, asks GitHub for the latest Hoard version. Nothing about you or your library is sent.",

  updatesTitle: "Updates",
  upToDate: (version: string) => `Up to date (v${version})`,
  updateAvailable: (version: string) => `Update available: v${version}`,
  updateHowTo: `In Decky's settings, open Developer and use Install Plugin from URL with ${INSTALL_URL}`,
  latestUnknown: "Latest version not known yet",
  notChecked: "Not checked yet",
  lastChecked: "Last checked",
  checkNow: "Check now",
  checking: "Checking...",
  openRelease: "Open release page",

  support: "If Hoard saved you from a full drive, you can buy me a coffee",
  supportButton: "Support on Ko-fi",
  version: "Version",

  sizeOnDisk: "Size on disk",
  game: "game",
  mods: "mods",
  noMods: "(no mods)",
};
