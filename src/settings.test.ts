import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { DEFAULT_SETTINGS, Settings, shownState, sizeLabelOn, sortOverrideOn } from "./settings";
import { EMPTY_STATE, OverviewLike, SizesState, STEAM_GAME_APP_TYPE, THIRD_PARTY_APP_TYPE } from "./sizes";
import { setSortOverrideEnabled } from "./sortOverride";

let overviews: Record<number, OverviewLike>;

const sized: SizesState = {
  ...EMPTY_STATE,
  sizes: { 3000000001: { name: "Shortcut", bytes: 300, base: 200, mods: 100, kind: "folder", paths: [] } },
  unsized: { 3000000002: { name: "Emulator", kind: "unknown" } },
  steam: { 10: { name: "Modded", base: 1000, mods: 50 } },
  total_bytes: 300,
};

// What index.tsx does with each new set of settings.
function apply(settings: Settings) {
  setSortOverrideEnabled(sortOverrideOn(settings), shownState(sized, settings));
}

beforeEach(() => {
  overviews = {
    3000000001: { appid: 3000000001, app_type: THIRD_PARTY_APP_TYPE, size_on_disk: "0" },
    10: { appid: 10, app_type: STEAM_GAME_APP_TYPE, size_on_disk: "1000" },
  };
  Object.assign(globalThis, { appStore: { GetAppOverviewByAppID: (id: number) => overviews[id] ?? null } });
});

afterEach(() => {
  setSortOverrideEnabled(false, EMPTY_STATE);
  delete (globalThis as { appStore?: unknown }).appStore;
});

describe("master switch", () => {
  const off = { ...DEFAULT_SETTINGS, enabled: false };

  it("turns every feature off, whatever their own settings say", () => {
    expect(sortOverrideOn(off)).toBe(false);
    expect(sizeLabelOn(off)).toBe(false);
    expect(sortOverrideOn(DEFAULT_SETTINGS)).toBe(true);
    expect(sizeLabelOn(DEFAULT_SETTINGS)).toBe(true);
  });

  it("puts Steam's own sizes back when turned off, and Hoard's when turned on", () => {
    apply(DEFAULT_SETTINGS);
    expect([overviews[3000000001].size_on_disk, overviews[10].size_on_disk]).toEqual(["300", "1050"]);
    apply(off);
    expect([overviews[3000000001].size_on_disk, overviews[10].size_on_disk]).toEqual(["0", "1000"]);
    apply(DEFAULT_SETTINGS);
    expect([overviews[3000000001].size_on_disk, overviews[10].size_on_disk]).toEqual(["300", "1050"]);
  });
});

describe("non-Steam scanning off", () => {
  const noShortcuts = { ...DEFAULT_SETTINGS, scan_shortcuts: false };

  it("hides shortcut sizes but keeps Steam games", () => {
    const shown = shownState(sized, noShortcuts);
    expect([shown.sizes, shown.unsized, shown.total_bytes]).toEqual([{}, {}, 0]);
    expect(shown.steam).toBe(sized.steam);
    expect(shownState(sized, DEFAULT_SETTINGS)).toBe(sized);
  });

  it("gives shortcuts Steam's value back in the sort, and leaves modded Steam games", () => {
    apply(DEFAULT_SETTINGS);
    apply(noShortcuts);
    expect([overviews[3000000001].size_on_disk, overviews[10].size_on_disk]).toEqual(["0", "1050"]);
  });
});
