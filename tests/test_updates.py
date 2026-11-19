"""The update check's pure parts. Nothing here touches the network."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import updates


def test_parse_version_takes_release_tags_only():
    assert updates.parse_version("v0.4.0") == (0, 4, 0)
    assert updates.parse_version("1.10.2") == (1, 10, 2)
    assert updates.parse_version("v1.0.0-beta") is None
    assert updates.parse_version("latest") is None


def test_latest_from_release_reads_the_tag_and_nothing_else():
    assert updates.latest_from_release({"tag_name": "v0.4.0", "html_url": "https://example.com"}) == "0.4.0"
    assert updates.latest_from_release({"tag_name": 4}) is None
    assert updates.latest_from_release({}) is None
    assert updates.latest_from_release(["v0.4.0"]) is None


def test_is_newer_compares_numbers_not_text():
    assert updates.is_newer("0.10.0", "0.9.0")
    assert not updates.is_newer("0.3.2", "0.3.2")
    assert not updates.is_newer("0.3.1", "0.3.2")
    assert not updates.is_newer(None, "0.3.2")
    assert not updates.is_newer("0.4.0", "dev")


def test_release_page_points_at_this_repository():
    assert updates.release_page("0.4.0") == "https://github.com/godvig/decky-hoard/releases/tag/v0.4.0"


def test_is_due_once_a_day():
    day = updates.CHECK_EVERY_SECONDS
    assert updates.is_due(0, day)
    assert not updates.is_due(day, day + day - 1)


def test_fetch_latest_is_none_when_offline(monkeypatch):
    def offline(*args, **kwargs):
        raise OSError("Network is unreachable")

    monkeypatch.setattr(updates.urllib.request, "urlopen", offline)
    assert updates.fetch_latest() is None
