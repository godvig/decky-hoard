import { beforeEach, describe, expect, it } from "vitest";

import { AppLike, CollectionLike, CollectionStoreLike, collectionStoreOf, removePile, syncPile } from "./piles";
import { Pile } from "./sizes";

// A stand-in for Steam's collection store that records every write.
function fakeStore() {
  const collections = new Map<string, CollectionLike>();
  const writes: string[] = [];
  let next = 1;
  const collection = (id: string, apps: AppLike[]): CollectionLike => ({
    id,
    allApps: [...apps],
    AddApps(added) {
      this.allApps.push(...added);
    },
    RemoveApps(removed) {
      this.allApps = this.allApps.filter((app) => !removed.includes(app));
    },
    async Save() {
      writes.push(`save ${id}`);
    },
  });
  const store: CollectionStoreLike = {
    NewUnsavedCollection: (_name, _filter, apps) => collection(`uc-${next++}`, apps),
    async SaveCollection(c) {
      collections.set(c.id, c);
      writes.push(`create ${c.id}`);
    },
    async DeleteCollection(id) {
      collections.delete(id);
      writes.push(`delete ${id}`);
    },
    GetCollection: (id) => collections.get(id) ?? null,
  };
  return { store, collections, writes };
}

const overviews: Record<number, AppLike> = { 10: { appid: 10 }, 11: { appid: 11 }, 12: { appid: 12 } };
const overviewOf = (appid: number) => overviews[appid] ?? null;
const pile = (appids: string[], extra: Partial<Pile> = {}): Pile => ({ name: "Over 50 GB · Den (Hoard)", appids, on: true, ...extra });

let fake: ReturnType<typeof fakeStore>;
beforeEach(() => {
  fake = fakeStore();
});

describe("collection store check", () => {
  it("takes a store with every method and nothing less", () => {
    expect(collectionStoreOf(fake.store)).toBe(fake.store);
    expect(collectionStoreOf({ ...fake.store, DeleteCollection: undefined })).toBeNull();
    expect(collectionStoreOf(undefined)).toBeNull();
  });
});

describe("syncPile", () => {
  it("makes a collection the first time and reports Steam's id", async () => {
    const result = await syncPile(fake.store, pile(["10", "99"]), overviewOf);
    expect(result).toEqual({ kind: "made", collection: { id: "uc-1", name: "Over 50 GB · Den (Hoard)" } });
    // 99 has no overview, such as another account's shortcut, so it is left out.
    expect(fake.collections.get("uc-1")?.allApps.map((app) => app.appid)).toEqual([10]);
  });

  it("adds and removes only what changed, and writes nothing when nothing did", async () => {
    const made = await syncPile(fake.store, pile(["10", "11"]), overviewOf);
    const collection = made.kind === "made" ? made.collection : null;
    fake.writes.length = 0;
    await syncPile(fake.store, pile(["10", "11"], { collection }), overviewOf);
    expect(fake.writes).toEqual([]);
    await syncPile(fake.store, pile(["11", "12"], { collection }), overviewOf);
    expect(fake.writes).toEqual(["save uc-1"]);
    expect(fake.collections.get("uc-1")?.allApps.map((app) => app.appid).sort()).toEqual([11, 12]);
  });

  it("replaces its own collection when the pile's name changes", async () => {
    await syncPile(fake.store, pile(["10"]), overviewOf);
    const result = await syncPile(
      fake.store,
      pile(["10"], { name: "Over 80 GB · Den (Hoard)", collection: { id: "uc-1", name: "Over 50 GB · Den (Hoard)" } }),
      overviewOf,
    );
    expect(fake.writes).toEqual(["create uc-1", "delete uc-1", "create uc-2"]);
    expect(result).toEqual({ kind: "made", collection: { id: "uc-2", name: "Over 80 GB · Den (Hoard)" } });
  });

  it("takes a collection the user deleted as the pile turned off, and makes no new one", async () => {
    const result = await syncPile(fake.store, pile(["10"], { collection: { id: "uc-9", name: "Over 50 GB · Den (Hoard)" } }), overviewOf);
    expect(result).toEqual({ kind: "gone" });
    expect(fake.writes).toEqual([]);
  });

  it("refuses a collection that doesn't look as expected", async () => {
    fake.collections.set("uc-5", { id: "uc-5" } as unknown as CollectionLike);
    await expect(syncPile(fake.store, pile(["10"], { collection: { id: "uc-5", name: "Over 50 GB · Den (Hoard)" } }), overviewOf)).rejects.toThrow();
    expect(fake.writes).toEqual([]);
  });

  it("never touches a collection Hoard didn't make", async () => {
    fake.collections.set("uc-mine", { id: "uc-mine", allApps: [{ appid: 10 }] } as unknown as CollectionLike);
    await syncPile(fake.store, pile(["11"]), overviewOf);
    await removePile(fake.store, { id: "uc-1", name: "x" });
    expect(fake.collections.has("uc-mine")).toBe(true);
    expect(fake.writes).toEqual(["create uc-1", "delete uc-1"]);
  });
});
