// Steam's size sort and "size on disk" sections read this field straight from
// each app's overview. It lives in memory only, so nothing is written to Steam.

import { OverviewLike, SizesState, STEAM_GAME_APP_TYPE, THIRD_PARTY_APP_TYPE } from "./sizes";

// Appid to the value Steam had before we changed it.
const patched = new Map<number, OverviewLike["size_on_disk"]>();
// Off until the saved setting is known, so a disabled override never flickers on.
let enabled = false;

function overviewOf(appid: number): OverviewLike | null {
  if (typeof appStore === "undefined") return null;
  // Typed as a number by @decky/ui, but Steam stores a string.
  return appStore.GetAppOverviewByAppID(appid) as unknown as OverviewLike | null;
}

// Returns whether the size was written.
function setSize(appid: number, appType: number, bytes: number): boolean {
  const overview = overviewOf(appid);
  if (overview?.app_type !== appType) return false;
  if (!patched.has(overview.appid)) patched.set(overview.appid, overview.size_on_disk);
  const value = String(bytes);
  if (overview.size_on_disk !== value) overview.size_on_disk = value;
  return true;
}

function restoreSize(appid: number) {
  const overview = overviewOf(appid);
  if (overview) overview.size_on_disk = patched.get(appid);
  patched.delete(appid);
}

export function applySizes(state: SizesState) {
  if (!enabled) return;
  const written = new Set<number>();
  for (const [appid, info] of Object.entries(state.sizes)) {
    if (setSize(Number(appid), THIRD_PARTY_APP_TYPE, info.bytes)) written.add(Number(appid));
  }
  // Steam's own number already is right for a Steam game without mods.
  for (const [appid, info] of Object.entries(state.steam ?? {})) {
    if (info.mods > 0 && setSize(Number(appid), STEAM_GAME_APP_TYPE, info.base + info.mods)) written.add(Number(appid));
  }
  // A game that lost its mods, or a shortcut no longer scanned, gets Steam's value back.
  for (const appid of [...patched.keys()]) {
    if (!written.has(appid)) restoreSize(appid);
  }
}

export function clearSizes() {
  for (const appid of [...patched.keys()]) restoreSize(appid);
}

export function setSortOverrideEnabled(value: boolean, state: SizesState) {
  enabled = value;
  if (value) applySizes(state);
  else clearSizes();
}
