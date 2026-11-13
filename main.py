import asyncio
import json
import os
import sys
import time

import decky

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scanner

CACHE_NAME = "sizes.json"
SETTINGS_NAME = "settings.json"
DEFAULT_SETTINGS = {"sort_override": True}
RESCAN_AFTER_SECONDS = 24 * 60 * 60
CHECK_EVERY_SECONDS = 15 * 60


class Plugin:
    _task = None
    _scan_lock = None
    _scanning = False

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

    def _needs_scan(self, cache):
        # Written before mods were measured.
        if "steam" not in cache:
            return True
        scanned_at = cache.get("scanned_at", 0)
        if time.time() - scanned_at > RESCAN_AFTER_SECONDS:
            return True
        # A game was added or removed since the last scan.
        for path in scanner.watched_paths(decky.DECKY_USER_HOME):
            try:
                if os.path.getmtime(path) > scanned_at:
                    return True
            except OSError:
                pass
        return False

    async def _scan(self):
        if self._scanning:
            return
        self._scanning = True
        try:
            started = time.time()
            result = await asyncio.to_thread(scanner.scan, decky.DECKY_USER_HOME)
            result["scanned_at"] = started
            await asyncio.to_thread(self._save_cache, result)
            decky.logger.info(
                "sized %d shortcuts, %d unsized, in %.1fs",
                len(result["sizes"]), len(result["unsized"]), time.time() - started,
            )
        except Exception:
            decky.logger.exception("scan failed")
        finally:
            self._scanning = False
        await decky.emit("sizes_updated")

    async def _watch(self):
        while True:
            if self._needs_scan(self._load_cache()):
                await self._scan()
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
            settings[key] = type(DEFAULT_SETTINGS[key])(value)
            self._write_json(self._settings_path(), settings)
        return settings

    async def rescan(self):
        asyncio.ensure_future(self._scan())
        return True

    async def _main(self):
        # Scans walk large folders, so stay out of the way of running games.
        os.nice(19)
        self._task = asyncio.ensure_future(self._watch())

    async def _unload(self):
        if self._task:
            self._task.cancel()
