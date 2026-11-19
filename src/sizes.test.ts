import { describe, expect, it, vi } from "vitest";

import { createStore, EMPTY_STATE, formatBytes, sizeText, SizesState, STEAM_GAME_APP_TYPE, THIRD_PARTY_APP_TYPE, totalBytes } from "./sizes";

const GB = 1024 ** 3;
const MB = 1024 ** 2;

function state(overrides: Partial<SizesState>): SizesState {
  return { ...EMPTY_STATE, ...overrides };
}

describe("formatBytes", () => {
  it("uses MB below one GB", () => {
    expect(formatBytes(512 * MB)).toBe("512 MB");
    expect(formatBytes(0)).toBe("0 MB");
  });

  it("uses one decimal for GB", () => {
    expect(formatBytes(GB)).toBe("1.0 GB");
    expect(formatBytes(87.44 * GB)).toBe("87.4 GB");
  });

  it("uses two decimals for TB", () => {
    expect(formatBytes(1536 * GB)).toBe("1.50 TB");
  });
});

describe("sizeText", () => {
  const shortcut = { appid: 3000000001, app_type: THIRD_PARTY_APP_TYPE };
  const steamGame = { appid: 10, app_type: STEAM_GAME_APP_TYPE, size_on_disk: String(20 * GB) };

  it("shows base and mods for a sized shortcut", () => {
    const s = state({ sizes: { 3000000001: { name: "A", bytes: 15 * GB, base: 10 * GB, mods: 5 * GB, source: "folder", paths: [] } } });
    expect(sizeText(s, shortcut, false)).toBe("10.0 GB game + 5.0 GB mods");
    expect(sizeText(s, shortcut, true)).toBe("10.0 GB + 5.0 GB mods");
  });

  it("says no mods when there are none", () => {
    const s = state({ steam: { 10: { name: "B", base: 2 * GB, mods: 0 } } });
    expect(sizeText(s, steamGame, false)).toBe("2.0 GB game (no mods)");
  });

  it("says mods are unknown when no rule covers the game", () => {
    const s = state({ sizes: { 3000000001: { name: "A", bytes: GB, base: GB, mods: 0, mods_known: false, source: "rom", paths: [] } } });
    expect(sizeText(s, shortcut, false)).toBe("1.0 GB game (mods —)");
  });

  it("falls back to Steam's size for a Steam game not scanned yet", () => {
    expect(sizeText(EMPTY_STATE, steamGame, false)).toBe("20.0 GB");
  });

  it("shows nothing for an unsized shortcut or an uninstalled game", () => {
    expect(sizeText(EMPTY_STATE, shortcut, false)).toBeNull();
    expect(sizeText(EMPTY_STATE, { ...steamGame, size_on_disk: "0" }, false)).toBeNull();
  });
});

describe("totalBytes", () => {
  it("prefers the backend's deduplicated total", () => {
    expect(totalBytes(state({ total_bytes: 7 }))).toBe(7);
  });

  it("sums shortcuts when no total was sent", () => {
    const item = { name: "", base: 0, mods: 0, source: "folder", paths: [] };
    expect(totalBytes(state({ sizes: { 1: { ...item, bytes: 2 }, 2: { ...item, bytes: 3 } } }))).toBe(5);
  });
});

describe("createStore", () => {
  it("notifies subscribers until they unsubscribe", () => {
    const store = createStore(EMPTY_STATE);
    const listener = vi.fn();
    const unsubscribe = store.subscribe(listener);
    const next = state({ scanning: true });
    store.set(next);
    expect(listener).toHaveBeenCalledWith(next);
    expect(store.get()).toBe(next);
    unsubscribe();
    store.set(EMPTY_STATE);
    expect(listener).toHaveBeenCalledTimes(1);
  });
});
