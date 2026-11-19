// The backend's settings and what each one turns on. No Steam or Decky globals in
// here, so it can be unit tested on its own.

import { createStore, SizesState } from "./sizes";

export interface Settings {
  // The master switch. Off, every feature below is off too.
  enabled: boolean;
  // "Include mods in sorting". Keeps its first name so saved settings still apply.
  sort_override: boolean;
  size_label: boolean;
  scan_shortcuts: boolean;
  // Hoard's only network access, off until the user turns it on.
  check_updates: boolean;
}

export const DEFAULT_SETTINGS: Settings = {
  enabled: true,
  sort_override: true,
  size_label: true,
  scan_shortcuts: true,
  check_updates: false,
};

export function sortOverrideOn(settings: Settings): boolean {
  return settings.enabled && settings.sort_override;
}

export function sizeLabelOn(settings: Settings): boolean {
  return settings.enabled && settings.size_label;
}

// The scan results Hoard may use. The backend keeps shortcut sizes while shortcut
// scanning is off, so they are dropped here.
export function shownState(state: SizesState, settings: Settings): SizesState {
  if (settings.scan_shortcuts) return state;
  const steam = new Set(Object.keys(state.steam ?? {}));
  return {
    ...state,
    sizes: {},
    unsized: {},
    total_bytes: 0,
    biggest: state.biggest?.filter((game) => game.source === "steam"),
    entries: state.entries?.filter((entry) => steam.has(entry.appid)),
  };
}

// The game page patch and the sort override start only once the saved settings are
// known, so this default never turns anything on by itself.
export const settingsStore = createStore<Settings>(DEFAULT_SETTINGS);
