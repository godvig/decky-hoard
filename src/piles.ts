// Piles: Steam collections that Hoard makes from its own data and keeps up to date.
// Hoard only ever changes or removes a collection whose id it stored when it made it,
// never one found by name, so the user's own collections are out of reach. No Decky
// globals in here: the collection store is passed in, so it can be unit tested on its own.

import { Pile, PileCollection } from "./sizes";

// The part of an app overview a collection takes.
export interface AppLike {
  appid: number;
}

// The parts of Steam's collection store and collections that Hoard uses.
export interface CollectionLike {
  id: string;
  allApps: AppLike[];
  AddApps(apps: AppLike[]): void;
  RemoveApps(apps: AppLike[]): void;
  Save(): Promise<void>;
}

export interface CollectionStoreLike {
  NewUnsavedCollection(name: string, filter: undefined, apps: AppLike[]): CollectionLike;
  SaveCollection(collection: CollectionLike): Promise<void>;
  DeleteCollection(id: string): Promise<unknown>;
  GetCollection(id: string): CollectionLike | null;
}

// What a sync did, for the caller to store.
export type SyncResult =
  | { kind: "kept"; collection: PileCollection }
  | { kind: "made"; collection: PileCollection }
  // The user deleted Hoard's collection in Steam: take that as turning the pile off.
  | { kind: "gone" };

// Steam's store when it has every method Hoard needs, or null to leave Piles off.
export function collectionStoreOf(candidate: unknown): CollectionStoreLike | null {
  const store = candidate as Partial<Record<keyof CollectionStoreLike, unknown>> | null | undefined;
  const methods: (keyof CollectionStoreLike)[] = ["NewUnsavedCollection", "SaveCollection", "DeleteCollection", "GetCollection"];
  return store && methods.every((name) => typeof store[name] === "function") ? (store as CollectionStoreLike) : null;
}

function isCollection(value: unknown): value is CollectionLike {
  const collection = value as Partial<CollectionLike> | null;
  return (
    !!collection &&
    typeof collection.id === "string" &&
    collection.id.length > 0 &&
    Array.isArray(collection.allApps) &&
    typeof collection.AddApps === "function" &&
    typeof collection.RemoveApps === "function" &&
    typeof collection.Save === "function"
  );
}

async function make(store: CollectionStoreLike, pile: Pile, apps: AppLike[]): Promise<SyncResult> {
  const collection = store.NewUnsavedCollection(pile.name, undefined, apps);
  if (!isCollection(collection)) throw new Error("Steam made a collection Hoard can't read");
  await store.SaveCollection(collection);
  return { kind: "made", collection: { id: collection.id, name: pile.name } };
}

// Brings one pile's collection in line with what Hoard found. Writes only on a change.
export async function syncPile(
  store: CollectionStoreLike,
  pile: Pile,
  overviewOf: (appid: number) => AppLike | null,
): Promise<SyncResult> {
  const apps = pile.appids.map((appid) => overviewOf(Number(appid))).filter((app): app is AppLike => app !== null);
  if (!pile.collection) return make(store, pile, apps);

  const existing = store.GetCollection(pile.collection.id);
  if (existing === null) return { kind: "gone" };
  if (!isCollection(existing)) throw new Error("Steam's collection doesn't look as Hoard expects");
  // A new threshold or device name makes a new name. Hoard owns this collection, so it can
  // replace it rather than rename it through a field Steam doesn't offer for that.
  if (pile.collection.name !== pile.name) {
    await store.DeleteCollection(existing.id);
    return make(store, pile, apps);
  }

  const have = new Set(existing.allApps.map((app) => String(app.appid)));
  const want = new Set(pile.appids);
  const added = apps.filter((app) => !have.has(String(app.appid)));
  const removed = existing.allApps.filter((app) => !want.has(String(app.appid)));
  if (added.length || removed.length) {
    existing.AddApps(added);
    existing.RemoveApps(removed);
    await existing.Save();
  }
  return { kind: "kept", collection: pile.collection };
}

// Removes a pile's collection, if Hoard's id still points at one.
export async function removePile(store: CollectionStoreLike, collection: PileCollection): Promise<void> {
  if (store.GetCollection(collection.id) !== null) await store.DeleteCollection(collection.id);
}
