import asyncio
import json
import os
import sys
import threading
import time

import decky

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import classify
import cleanup
import scanner
import updates

CACHE_NAME = "sizes.json"
SETTINGS_NAME = "settings.json"
UPDATES_NAME = "updates.json"
APP_TYPES_NAME = "app_types.json"
LAST_PLAYED_NAME = "last_played.json"
# Every folder clean-up removes, with its size and time.
CLEANUP_LOG_NAME = "cleanup.log"
STALE_MONTHS_RANGE = (1, 36)
BIG_GIB_RANGE = (10, 1000)
DMI_PRODUCT = "/sys/devices/virtual/dmi/id/product_name"
# enabled is the master switch. sort_override keeps its first name so saved settings still apply.
DEFAULT_SETTINGS = {"enabled": True, "sort_override": True, "size_label": True, "scan_shortcuts": True,
                    # Hoard's only network access, so it waits for the user to ask for it.
                    "check_updates": False,
                    "biggest_games": True,
                    "not_played": True,
                    "mods_overview": True,
                    "cleanup": True,
                    # How long a game must go unplayed to show under "Not played".
                    "stale_months": 6,
                    # Piles: Steam collections Hoard makes, each off until turned on.
                    "pile_big": False,
                    "pile_stale": False,
                    "pile_modded": False,
                    "pile_on_disk": False,
                    "pile_big_gib": 50,
                    # Empty means the device's model, such as Steam Machine.
                    "device_name": "",
                    # The collections Hoard made, as {pile: {"id": ..., "name": ...}}. Only these
                    # are ever changed or removed, found by id and never by name.
                    "pile_collections": {},
                    # The user's "Not a game" and "Count as game", as {appid: kind}.
                    "kind_overrides": {}}
# Shortcut results a scan without shortcuts carries over from the last cache.
SHORTCUT_FIELDS = ("sizes", "unsized", "total_bytes")
RESCAN_AFTER_SECONDS = 24 * 60 * 60
CHECK_EVERY_SECONDS = 15 * 60


class Plugin:
    _task = None
    _scan_lock = None
    _scanning = False
    _checking = False

    def __init__(self):
        # Read by the scan thread, which task cancellation can't reach.
        self._stopping = threading.Event()

    def _cache_path(self):
        return os.path.join(decky.DECKY_PLUGIN_SETTINGS_DIR, CACHE_NAME)

    def _load_cache(self):
        try:
            with open(self._cache_path()) as f:
                return json.load(f)
        except (OSError, ValueError):
            return {"sizes": {}, "unsized": {}, "steam": {}, "scanned_at": 0}

    def _save_cache(self, result):
        self._write_json(self._cache_path(), result)

    def _write_json(self, path, data):
        tmp = path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(data, f)
        os.replace(tmp, path)

    def _settings_path(self):
        return os.path.join(decky.DECKY_PLUGIN_SETTINGS_DIR, SETTINGS_NAME)

    def _load_settings(self):
        settings = dict(DEFAULT_SETTINGS)
        try:
            with open(self._settings_path()) as f:
                saved = json.load(f)
            settings.update({k: v for k, v in saved.items()
                             if k in DEFAULT_SETTINGS and isinstance(v, type(DEFAULT_SETTINGS[k]))})
        except (OSError, ValueError, AttributeError):
            pass
        return settings

    def _app_types_path(self):
        return os.path.join(decky.DECKY_PLUGIN_SETTINGS_DIR, APP_TYPES_NAME)

    def _load_app_types(self):
        return self._load_ints(self._app_types_path())

    def _last_played_path(self):
        return os.path.join(decky.DECKY_PLUGIN_SETTINGS_DIR, LAST_PLAYED_NAME)

    def _load_ints(self, path):
        try:
            with open(path) as f:
                data = json.load(f)
            return {str(k): v for k, v in data.items() if isinstance(v, int) and not isinstance(v, bool)}
        except (OSError, ValueError, AttributeError):
            return {}

    def _save_ints(self, path, data):
        clean = {str(k): v for k, v in data.items() if isinstance(v, int) and not isinstance(v, bool)}
        if clean != self._load_ints(path):
            self._write_json(path, clean)

    def _updates_path(self):
        return os.path.join(decky.DECKY_PLUGIN_SETTINGS_DIR, UPDATES_NAME)

    def _load_updates(self):
        try:
            with open(self._updates_path()) as f:
                state = json.load(f)
            if isinstance(state, dict):
                return state
        except (OSError, ValueError):
            pass
        return {"attempted_at": 0, "checked_at": 0, "latest": None}

    def _update_info(self, state):
        current = decky.DECKY_PLUGIN_VERSION
        latest = state.get("latest")
        available = updates.is_newer(latest, current)
        return {"current": current, "latest": latest, "checked_at": state.get("checked_at", 0),
                "checking": self._checking, "available": available,
                "url": updates.release_page(latest) if available else None}

    def _update_check_due(self):
        settings = self._load_settings()
        return (settings["enabled"] and settings["check_updates"]
                and updates.is_due(self._load_updates().get("attempted_at", 0), time.time()))

    async def _check_updates(self):
        if self._checking:
            return
        self._checking = True
        try:
            latest = await asyncio.to_thread(updates.fetch_latest)
            state = self._load_updates()
            # Counted even when it fails, so an offline Deck asks at most once a day too.
            state["attempted_at"] = time.time()
            if latest:
                state.update(latest=latest, checked_at=state["attempted_at"])
            else:
                decky.logger.info("update check got no answer, trying again in a day")
            self._write_json(self._updates_path(), state)
        finally:
            self._checking = False
        await decky.emit("updates_changed")

    def _needs_scan(self, cache):
        # Written by an earlier Hoard, before mods were measured or entries had a kind.
        if cache.get("format") != scanner.CACHE_FORMAT:
            return True
        include_shortcuts = self._load_settings()["scan_shortcuts"]
        # Shortcut sizes kept from before shortcut scanning was turned off are stale.
        if include_shortcuts and not cache.get("shortcuts_scanned", True):
            return True
        scanned_at = cache.get("scanned_at", 0)
        if time.time() - scanned_at > RESCAN_AFTER_SECONDS:
            return True
        # A game was added or removed since the last scan.
        for path in scanner.watched_paths(decky.DECKY_USER_HOME, include_shortcuts):
            try:
                if os.path.getmtime(path) > scanned_at:
                    return True
            except OSError:
                pass
        return False

    def _should_scan(self):
        # Turned off, Hoard leaves the disk alone until it's turned on again.
        return self._load_settings()["enabled"] and self._needs_scan(self._load_cache())

    async def _scan(self, full=False):
        """full measures every folder. Otherwise unchanged Steam games without mods are reused."""
        if self._scanning:
            return
        self._scanning = True
        try:
            started = time.time()
            include_shortcuts = self._load_settings()["scan_shortcuts"]
            cache = self._load_cache()
            previous = None if full else cache.get("steam")
            result = await asyncio.to_thread(scanner.scan, decky.DECKY_USER_HOME, self._stopping.is_set,
                                             include_shortcuts, previous)
            if not include_shortcuts:
                # Hidden while shortcut scanning is off, not forgotten.
                result.update({field: cache[field] for field in SHORTCUT_FIELDS if field in cache})
            result["shortcuts_scanned"] = include_shortcuts
            result["scanned_at"] = started
            await asyncio.to_thread(self._save_cache, result)
            decky.logger.info(
                "sized %d shortcuts, %d unsized, in %.1fs",
                len(result["sizes"]), len(result["unsized"]), time.time() - started,
            )
        except scanner.ScanStopped:
            decky.logger.info("scan stopped after %.1fs, plugin is unloading", time.time() - started)
            return
        except Exception:
            decky.logger.exception("scan failed")
        finally:
            self._scanning = False
        await decky.emit("sizes_updated")

    async def _watch(self):
        while True:
            if self._should_scan():
                await self._scan()
            if self._update_check_due():
                await self._check_updates()
            await asyncio.sleep(CHECK_EVERY_SECONDS)

    async def get_sizes(self):
        settings = self._load_settings()
        cache = self._load_cache()
        if not settings["scan_shortcuts"]:
            # Kept on disk for when scanning is turned back on, but left out of every count and list.
            cache.update(sizes={}, unsized={}, total_bytes=0)
        cache = classify.apply_kinds(cache, self._load_app_types(), settings["kind_overrides"],
                                     self._load_ints(self._last_played_path()), time.time(), settings["stale_months"])
        cache["piles"] = {key: {**pile, "on": settings[f"pile_{key}"],
                                "collection": settings["pile_collections"].get(key)}
                          for key, pile in classify.piles(cache, settings["pile_big_gib"], self._device_name()).items()}
        cache["device"] = self._device_name()
        cache["scanning"] = self._scanning
        return cache

    def _device_name(self):
        try:
            with open(DMI_PRODUCT) as f:
                product = f.read()
        except OSError:
            product = ""
        return classify.device_name(self._load_settings()["device_name"], product, os.uname().nodename)

    async def find_leftovers(self):
        """A dry run: leftover shader caches and Proton prefixes, nothing removed."""
        return await asyncio.to_thread(cleanup.find, decky.DECKY_USER_HOME)

    async def remove_shader_caches(self, paths):
        """Remove the shader caches the user confirmed, as far as the rules still allow."""
        settings = self._load_settings()
        if not (settings["enabled"] and settings["cleanup"]) or not isinstance(paths, list):
            return {"removed": [], "bytes": 0, "skipped": [], "missing": []}
        log = os.path.join(decky.DECKY_PLUGIN_SETTINGS_DIR, CLEANUP_LOG_NAME)
        result = await asyncio.to_thread(cleanup.remove_shader_caches, decky.DECKY_USER_HOME,
                                         [path for path in paths if isinstance(path, str)], log)
        decky.logger.info("clean-up removed %d shader caches, %d bytes, skipped %d",
                          len(result["removed"]), result["bytes"], len(result["skipped"]))
        return result

    async def set_pile_collection(self, key, collection_id, name):
        """Remember the collection Steam made for a pile, or forget it with an id of None."""
        settings = self._load_settings()
        collections = dict(settings["pile_collections"])
        if key in classify.PILE_KEYS and isinstance(collection_id, str) and collection_id:
            collections[key] = {"id": collection_id, "name": str(name)}
        else:
            collections.pop(key, None)
        settings["pile_collections"] = collections
        self._write_json(self._settings_path(), settings)
        return collections

    async def set_app_types(self, types):
        """Steam's app type per installed Steam app. Only the frontend can ask Steam for them."""
        self._save_ints(self._app_types_path(), types)
        return True

    async def set_last_played(self, times):
        """Steam's last-played time per app, in seconds. Hoard doesn't track play time itself."""
        self._save_ints(self._last_played_path(), times)
        return True

    async def set_counts_as_game(self, appid, counts):
        """The panel's switch: an override only where it differs from what the rules say."""
        rules = classify.apply_kinds(self._load_cache(), self._load_app_types(), {})
        rule_kind = next((group[str(appid)]["kind"] for group in (rules["sizes"], rules["unsized"], rules["steam"])
                          if str(appid) in group), "game")
        wanted = "game" if counts else ("app" if rule_kind == "game" else rule_kind)
        return await self.set_kind(appid, None if wanted == rule_kind else wanted)

    async def set_kind(self, appid, kind):
        """Override what an entry is. A kind of None goes back to Hoard's own rules."""
        settings = self._load_settings()
        overrides = dict(settings["kind_overrides"])
        if kind in classify.KINDS:
            overrides[str(appid)] = kind
        else:
            overrides.pop(str(appid), None)
        settings["kind_overrides"] = overrides
        self._write_json(self._settings_path(), settings)
        return await self.get_sizes()

    async def get_settings(self):
        return self._load_settings()

    async def set_setting(self, key, value):
        settings = self._load_settings()
        # Switches, numbers and the device name. Overrides and collections have their own calls.
        if isinstance(DEFAULT_SETTINGS.get(key), (bool, int, str)):
            was_on = settings[key]
            settings[key] = type(DEFAULT_SETTINGS[key])(value)
            ranges = {"stale_months": STALE_MONTHS_RANGE, "pile_big_gib": BIG_GIB_RANGE}
            if key in ranges:
                settings[key] = min(max(settings[key], ranges[key][0]), ranges[key][1])
            if key == "device_name":
                settings[key] = settings[key].strip()[:40]
            self._write_json(self._settings_path(), settings)
            # Catch up now rather than at the watcher's next check, up to 15 minutes later.
            if settings[key] is True and not was_on and self._should_scan():
                asyncio.ensure_future(self._scan())
            if settings[key] is True and not was_on and self._update_check_due():
                asyncio.ensure_future(self._check_updates())
        return settings

    async def get_version(self):
        return decky.DECKY_PLUGIN_VERSION

    async def get_update(self):
        return self._update_info(self._load_updates())

    async def check_updates_now(self):
        settings = self._load_settings()
        if settings["enabled"] and settings["check_updates"]:
            await self._check_updates()
        return self._update_info(self._load_updates())

    async def rescan(self):
        if not self._load_settings()["enabled"]:
            return False
        # Asked for by the user, so measure everything rather than trust the last scan.
        asyncio.ensure_future(self._scan(full=True))
        return True

    async def _main(self):
        # Scans walk large folders, so stay out of the way of running games.
        os.nice(19)
        self._task = asyncio.ensure_future(self._watch())

    async def _unload(self):
        # Otherwise the scan thread keeps the process alive until Decky kills it.
        self._stopping.set()
        if self._task:
            self._task.cancel()
