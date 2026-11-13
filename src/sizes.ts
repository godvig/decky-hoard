// Scan results from the backend, and how they are shown. No Steam or Decky
// globals in here, so it can be unit tested on its own.

export const STEAM_GAME_APP_TYPE = 1;
export const THIRD_PARTY_APP_TYPE = 1073741824;

export interface MeasuredSize {
  name: string;
  base: number;
  mods: number;
}

export interface ShortcutSize extends MeasuredSize {
  bytes: number;
  kind: string;
  paths: string[];
}

export interface SizesState {
  sizes: Record<string, ShortcutSize>;
  unsized: Record<string, { name: string; kind: string }>;
  steam: Record<string, MeasuredSize>;
  scanned_at: number;
  scanning: boolean;
  total_bytes?: number;
  // Set once the plugin unloads, so an open game page drops the stat.
  removed?: boolean;
}

// The part of Steam's app overview the plugin reads.
export interface OverviewLike {
  appid: number;
  app_type: number;
  size_on_disk?: number | string;
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
    const mods = info.mods > 0 ? `+ ${formatBytes(info.mods)} mods` : "(no mods)";
    return `${formatBytes(info.base)}${compact ? "" : " game"} ${mods}`;
  }
  // A Steam game installed since the last scan: its mods aren't measured yet.
  const bytes = Number(overview.size_on_disk);
  return overview.app_type !== THIRD_PARTY_APP_TYPE && bytes > 0 ? formatBytes(bytes) : null;
}

// Shortcuts can share a folder, so the backend's total counts each folder once.
export function totalBytes(state: SizesState): number {
  return state.total_bytes ?? Object.values(state.sizes).reduce((sum, item) => sum + item.bytes, 0);
}

type Listener = (state: SizesState) => void;

export function createStore(initial: SizesState) {
  let state = initial;
  const listeners = new Set<Listener>();
  return {
    get: () => state,
    set(next: SizesState) {
      state = next;
      listeners.forEach((listener) => listener(state));
    },
    subscribe(listener: Listener) {
      listeners.add(listener);
      return () => {
        listeners.delete(listener);
      };
    },
  };
}

export const store = createStore(EMPTY_STATE);
