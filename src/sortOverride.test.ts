import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { EMPTY_STATE, OverviewLike, SizesState, STEAM_GAME_APP_TYPE, THIRD_PARTY_APP_TYPE } from "./sizes";
import { applySizes, appTypes, clearSizes, setSortOverrideEnabled } from "./sortOverride";

let overviews: Record<number, OverviewLike>;

const sized: SizesState = {
  ...EMPTY_STATE,
  sizes: { 3000000001: { name: "Shortcut", bytes: 300, base: 200, mods: 100, source: "folder", paths: [] } },
  steam: {
    10: { name: "Modded", base: 1000, mods: 50 },
    11: { name: "Plain", base: 2000, mods: 0 },
  },
};

beforeEach(() => {
  overviews = {
    3000000001: { appid: 3000000001, app_type: THIRD_PARTY_APP_TYPE, size_on_disk: "0" },
    10: { appid: 10, app_type: STEAM_GAME_APP_TYPE, size_on_disk: "1000" },
    11: { appid: 11, app_type: STEAM_GAME_APP_TYPE, size_on_disk: "2000" },
  };
  Object.assign(globalThis, { appStore: { GetAppOverviewByAppID: (id: number) => overviews[id] ?? null } });
});

afterEach(() => {
  setSortOverrideEnabled(false, EMPTY_STATE);
  delete (globalThis as { appStore?: unknown }).appStore;
});

describe("sort override", () => {
  it("does nothing until enabled", () => {
    applySizes(sized);
    expect(overviews[3000000001].size_on_disk).toBe("0");
  });

  it("writes shortcut sizes and Steam games with mods only", () => {
    setSortOverrideEnabled(true, sized);
    expect(overviews[3000000001].size_on_disk).toBe("300");
    expect(overviews[10].size_on_disk).toBe("1050");
    expect(overviews[11].size_on_disk).toBe("2000");
  });

  it("restores Steam's values when disabled", () => {
    setSortOverrideEnabled(true, sized);
    setSortOverrideEnabled(false, sized);
    expect(overviews[3000000001].size_on_disk).toBe("0");
    expect(overviews[10].size_on_disk).toBe("1000");
  });

  it("restores a Steam game whose mods were removed", () => {
    setSortOverrideEnabled(true, sized);
    applySizes({ ...sized, steam: { 10: { name: "Modded", base: 1000, mods: 0 } } });
    expect(overviews[10].size_on_disk).toBe("1000");
  });

  it("leaves apps of another type alone", () => {
    overviews[10].app_type = 4; // A tool, such as Proton.
    setSortOverrideEnabled(true, sized);
    expect(overviews[10].size_on_disk).toBe("1000");
    clearSizes();
  });
});

describe("app types", () => {
  it("reports Steam's type for the apps it knows only", () => {
    overviews[20] = { appid: 20, app_type: 4, size_on_disk: "10" };
    expect(appTypes(["10", "20", "99"])).toEqual({ 10: STEAM_GAME_APP_TYPE, 20: 4 });
  });
});
