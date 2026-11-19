// Scan results from the backend, and how they are shown. No Steam or Decky
// globals in here, so it can be unit tested on its own.

import { strings } from "./strings";

export const STEAM_GAME_APP_TYPE = 1;
export const THIRD_PARTY_APP_TYPE = 1073741824;

// Decided by the backend (classify.py). Counts and rankings take only games.
export type Kind = "game" | "app" | "emulator" | "tool";

export interface ModPart {
  // workshop, mod-organizer, openmw, or loose: files beyond what Steam installed.
  where: string;
  // With ~ for the home folder.
  shown: string;
  bytes: number;
}

export interface MeasuredSize {
  name: string;
  base: number;
  mods: number;
  // False when no rule says where this game's mods would be: unknown, not none.
  mods_known?: boolean;
  mod_parts?: ModPart[];
  kind?: Kind;
}

export interface ShortcutSize extends MeasuredSize {
  bytes: number;
  // How the scanner found its files, such as rom, folder or heroic.
  source: string;
  paths: string[];
}

export interface RankedGame {
  appid: string;
  name: string;
  bytes: number;
  mods: number;
  source: string;
  mod_parts?: ModPart[];
}

export interface ModsOverview {
  games: (RankedGame & { share: number })[];
  bytes: number;
}

export interface Entry {
  appid: string;
  name: string;
  kind: Kind;
  // No rule said what it is, so it counts as a game until the user says otherwise.
  guessed: boolean;
  overridden: boolean;
  // Not a game, or only guessed to be one: worth a look from the user.
  review: boolean;
}

export interface NotPlayed {
  months: number;
  games: (RankedGame & { last_played: number })[];
  bytes: number;
  // Steam has no play time for these: never played, or not in this account's library.
  unknown: RankedGame[];
  unknown_bytes: number;
}

export interface Counts {
  shortcut_games: number;
  sized_shortcut_games: number;
  guessed: number;
}

export interface SizesState {
  sizes: Record<string, ShortcutSize>;
  unsized: Record<string, { name: string; source: string; kind?: Kind }>;
  steam: Record<string, MeasuredSize>;
  scanned_at: number;
  scanning: boolean;
  total_bytes?: number;
  counts?: Counts;
  biggest?: RankedGame[];
  entries?: Entry[];
  not_played?: NotPlayed;
  mods?: ModsOverview;
  // Set once the plugin unloads, so an open game page drops the stat.
  removed?: boolean;
}

// The part of Steam's app overview the plugin reads.
export interface OverviewLike {
  appid: number;
  app_type: number;
  size_on_disk?: number | string;
  rt_last_time_played?: number;
}

export const EMPTY_STATE: SizesState = { sizes: {}, unsized: {}, steam: {}, scanned_at: 0, scanning: false };

export function formatBytes(bytes: number): string {
  const gib = bytes / 1024 ** 3;
  if (gib >= 1024) return `${(gib / 1024).toFixed(2)} TB`;
  return gib >= 1 ? `${gib.toFixed(1)} GB` : `${Math.round(bytes / 1024 ** 2)} MB`;
}

export function sizeText(state: SizesState, overview: OverviewLike, compact: boolean): string | null {
  const info = state.sizes[overview.appid] ?? state.steam?.[overview.appid];
  if (info?.base !== undefined) {
    let mods = strings.noMods;
    if (info.mods > 0) mods = `+ ${formatBytes(info.mods)} ${strings.mods}`;
    else if (info.mods_known === false) mods = strings.modsUnknown;
    return `${formatBytes(info.base)}${compact ? "" : ` ${strings.game}`} ${mods}`;
  }
  // A Steam game installed since the last scan: its mods aren't measured yet.
  const bytes = Number(overview.size_on_disk);
  return overview.app_type !== THIRD_PARTY_APP_TYPE && bytes > 0 ? formatBytes(bytes) : null;
}

// Shortcuts can share a folder, so the backend's total counts each folder once.
export function totalBytes(state: SizesState): number {
  return state.total_bytes ?? Object.values(state.sizes).reduce((sum, item) => sum + item.bytes, 0);
}

export function createStore<T>(initial: T) {
  let state = initial;
  const listeners = new Set<(state: T) => void>();
  return {
    get: () => state,
    set(next: T) {
      state = next;
      listeners.forEach((listener) => listener(state));
    },
    subscribe(listener: (state: T) => void) {
      listeners.add(listener);
      return () => {
        listeners.delete(listener);
      };
    },
  };
}

export const store = createStore(EMPTY_STATE);
