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

  notPlayedTitle: (months: number) => `Not played in ${months} ${months === 1 ? "month" : "months"}`,
  months: "Months",
  couldFree: (count: number, size: string) => `${count} ${count === 1 ? "game" : "games"}, ${size} you could free`,
  lastPlayedOn: (date: string) => `Last played ${date}`,
  noPlayTime: (count: number, size: string) => `No play time recorded: ${count} ${count === 1 ? "game" : "games"}, ${size}`,
  noPlayTimeDescription: "Never played, or added by another Steam account. Not counted above.",
  showGames: (count: number) => `Show ${count}`,
  biggestGames: "Biggest games",
  biggestGamesDescription: "Lists the ten largest games in this panel.",
  notPlayed: "Not played",
  notPlayedDescription: "Lists installed games you haven't played for a while, using Steam's own last-played time.",

  modsTitle: "Mods",
  modsSummary: (count: number, size: string) => `${count} ${count === 1 ? "game" : "games"} with ${size} of mods`,
  modsNone: "No mods found",
  modsShare: (percent: number, total: string) => `${percent}% of ${total}`,
  modsHowTo: "Hoard finds mods only where it knows to look. The README lists where, and how to ask for more.",
  where: {
    workshop: "Steam Workshop",
    "mod-organizer": "Mod Organizer",
    openmw: "OpenMW",
    loose: "Other files in the game folder",
  } as Record<string, string>,
  looseNote: "May include files the game made itself, such as logs and caches.",
  modsOverview: "Mods",
  modsOverviewDescription: "Lists games with mods, how much space the mods take, and where they are.",

  pilesTitle: "Piles",
  pilesDescription: (device: string) =>
    `Steam collections Hoard keeps up to date, named for ${device}. Hoard only changes the ones it made.`,
  pileGames: (count: number) => `${count} ${count === 1 ? "game" : "games"}`,
  pileThreshold: "Size for the Over pile",
  deviceName: "Device name",
  deviceNameDescription: "Tells this device's piles apart from another device's on the same account.",
  pilesBroken: "Piles are paused: Steam's collections didn't work as Hoard expects. Nothing more was changed.",
  pilesWhileOff: "Hoard is off, so piles stay as they are in Steam until it is turned on.",
  removePileTitle: "Remove this pile?",
  removePileDescription: (name: string) =>
    `Hoard removes its collection "${name}" from Steam, on every device on this account. The games stay installed.`,
  removePile: "Remove",

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
  modsUnknown: "(mods —)",
};
