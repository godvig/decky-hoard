import asyncio
import json
import os
import sys
import threading
import time

import decky

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scanner
import updates

CACHE_NAME = "sizes.json"
SETTINGS_NAME = "settings.json"
UPDATES_NAME = "updates.json"
# enabled is the master switch. sort_override keeps its first name so saved settings still apply.
DEFAULT_SETTINGS = {"enabled": True, "sort_override": True, "size_label": True, "scan_shortcuts": True,
                    # Hoard's only network access, so it waits for the user to ask for it.
                    "check_updates": False}
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
            settings.update({k: v for k, v in saved.items() if k in DEFAULT_SETTINGS})
        except (OSError, ValueError, AttributeError):
            pass
        return settings

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
        # Written before mods were measured.
        if "steam" not in cache:
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

    async def _scan(self):
        if self._scanning:
            return
        self._scanning = True
        try:
            started = time.time()
            include_shortcuts = self._load_settings()["scan_shortcuts"]
            result = await asyncio.to_thread(scanner.scan, decky.DECKY_USER_HOME, self._stopping.is_set,
                                             include_shortcuts)
            if not include_shortcuts:
                # Hidden while shortcut scanning is off, not forgotten.
                cache = self._load_cache()
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
        cache = self._load_cache()
        cache["scanning"] = self._scanning
        return cache

    async def get_settings(self):
        return self._load_settings()

    async def set_setting(self, key, value):
        settings = self._load_settings()
        if key in DEFAULT_SETTINGS:
            was_on = settings[key]
            settings[key] = type(DEFAULT_SETTINGS[key])(value)
            self._write_json(self._settings_path(), settings)
            # Catch up now rather than at the watcher's next check, up to 15 minutes later.
            if settings[key] and not was_on and self._should_scan():
                asyncio.ensure_future(self._scan())
            if settings[key] and not was_on and self._update_check_due():
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
        asyncio.ensure_future(self._scan())
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
