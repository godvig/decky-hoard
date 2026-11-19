"""Asks GitHub for the latest Hoard release. This is Hoard's only network access.

It reads a version number and nothing else: no download, no install, and the request
carries nothing about the user or the library.
"""

import json
import re
import urllib.request

LATEST_URL = "https://api.github.com/repos/godvig/decky-hoard/releases/latest"
RELEASE_PAGE = "https://github.com/godvig/decky-hoard/releases/tag/v{version}"
CHECK_EVERY_SECONDS = 24 * 60 * 60
TIMEOUT_SECONDS = 10
# A release tag such as v0.4.0. Anything else is ignored rather than guessed at.
TAG = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)$")


def parse_version(text: str) -> tuple[int, int, int] | None:
    match = TAG.match(text.strip())
    return (int(match[1]), int(match[2]), int(match[3])) if match else None


def latest_from_release(release: object) -> str | None:
    """The version of a release in GitHub's API format, or None if it has no usable tag."""
    tag = release.get("tag_name") if isinstance(release, dict) else None
    version = parse_version(tag) if isinstance(tag, str) else None
    return ".".join(map(str, version)) if version else None


def is_newer(latest: str | None, current: str) -> bool:
    latest_version, current_version = parse_version(latest or ""), parse_version(current)
    return latest_version is not None and current_version is not None and latest_version > current_version


def release_page(version: str) -> str:
    # Built from the checked version, so a reply from GitHub can't choose where the button goes.
    return RELEASE_PAGE.format(version=version)


def is_due(attempted_at: float, now: float) -> bool:
    return now - attempted_at >= CHECK_EVERY_SECONDS


def fetch_latest() -> str | None:
    """The latest release's version, or None when offline or GitHub doesn't answer as expected."""
    # GitHub turns away requests without a User-Agent. This one carries no version or ID.
    request = urllib.request.Request(LATEST_URL, headers={"Accept": "application/vnd.github+json",
                                                          "User-Agent": "Hoard"})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            return latest_from_release(json.load(response))
    except (OSError, ValueError):
        return None
