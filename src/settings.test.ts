import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { DEFAULT_SETTINGS, Settings, shownState, sizeLabelOn, sortOverrideOn } from "./settings";
import { EMPTY_STATE, OverviewLike, SizesState, STEAM_GAME_APP_TYPE, THIRD_PARTY_APP_TYPE } from "./sizes";
import { setSortOverrideEnabled } from "./sortOverride";

let overviews: Record<number, OverviewLike>;

const sized: SizesState = {
  ...EMPTY_STATE,
  sizes: { 3000000001: { name: "Shortcut", bytes: 300, base: 200, mods: 100, source: "folder", paths: [] } },
  unsized: { 3000000002: { name: "Emulator", source: "unknown", kind: "emulator" } },
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

  it("drops shortcuts from the rankings and the game-or-not list", () => {
    const state: SizesState = {
      ...sized,
      biggest: [
        { appid: "10", name: "Modded", bytes: 1050, mods: 50, source: "steam" },
        { appid: "3000000001", name: "Shortcut", bytes: 300, mods: 100, source: "folder" },
      ],
      entries: [
        { appid: "3000000002", name: "Emulator", kind: "emulator", guessed: false, overridden: false, review: true },
        { appid: "10", name: "Modded", kind: "game", guessed: false, overridden: false, review: false },
      ],
    };
    const shown = shownState(state, noShortcuts);
    expect(shown.biggest?.map((game) => game.appid)).toEqual(["10"]);
    expect(shown.entries?.map((entry) => entry.appid)).toEqual(["10"]);
  });

  it("gives shortcuts Steam's value back in the sort, and leaves modded Steam games", () => {
    apply(DEFAULT_SETTINGS);
    apply(noShortcuts);
    expect([overviews[3000000001].size_on_disk, overviews[10].size_on_disk]).toEqual(["0", "1050"]);
  });
});
