import os
import sys
import json
import types
import pytest
import responses as responses_lib
import feedparser

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../src"))

import subscribe

FEED_URL = "http://example.com/feed.xml"
COVER_URL = "http://example.com/cover.jpg"
EP1_URL = "http://example.com/episode1.mp3"
EP2_URL = "http://example.com/episode2.mp3"
EP3_URL = "http://example.com/episode3.mp3"

DUMMY_BYTES = b"\xff\xfb\x90\x00" * 256  # ~1KB dummy audio
DUMMY_IMAGE = b"\xff\xd8\xff\xe0" * 64   # dummy JPEG bytes


class MockFeed(dict):
    """Dict with attribute access — mirrors feedparser FeedParserDict interface."""
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(key)


# ─── Test 1: Feed metadata parsing ───────────────────────────────────────────

class TestFeedMetadataParsing:
    @responses_lib.activate
    def test_get_meta_returns_parsed_title(self, sample_feed_xml):
        responses_lib.add(responses_lib.GET, FEED_URL, body=sample_feed_xml.encode(), status=200)
        meta = subscribe.get_meta(FEED_URL)
        assert meta.title == "Test Podcast"

    @responses_lib.activate
    def test_get_entries_returns_three(self, sample_feed_xml):
        responses_lib.add(responses_lib.GET, FEED_URL, body=sample_feed_xml.encode(), status=200)
        entries = subscribe.get_entries(FEED_URL)
        assert len(entries) == 3


# ─── Test 2: Feed image URL extraction ───────────────────────────────────────

class TestGetFeedImageUrl:
    def test_with_image_href(self):
        image = types.SimpleNamespace(href="http://example.com/cover.jpg")
        meta = types.SimpleNamespace(image=image)
        result = subscribe.get_feed_image_url(meta)
        assert result == "http://example.com/cover.jpg"

    def test_without_image(self):
        meta = types.SimpleNamespace()
        result = subscribe.get_feed_image_url(meta)
        assert result is None


# ─── Test 3: Metadata simplification ─────────────────────────────────────────

class TestSimplifyMetadata:
    def test_returns_expected_keys_and_values(self):
        remote = MockFeed(title="Test Podcast", summary="A show about testing.", link="http://example.com")
        configured = {"url": FEED_URL}
        result = subscribe.simplify_metadata(remote, configured)
        assert result["title"] == "Test Podcast"
        assert result["summary"] == "A show about testing."
        assert result["url"] == FEED_URL


# ─── Test 4: Full episode download flow ──────────────────────────────────────

def _register_all_mocks(sample_feed_xml):
    """Register all HTTP mocks needed for a full subscribe.main() run."""
    responses_lib.add(responses_lib.GET, FEED_URL, body=sample_feed_xml.encode(), status=200)
    responses_lib.add(responses_lib.GET, COVER_URL, body=DUMMY_IMAGE, status=200)
    responses_lib.add(responses_lib.GET, EP1_URL, body=DUMMY_BYTES, status=200)
    responses_lib.add(responses_lib.GET, EP2_URL, body=DUMMY_BYTES, status=200)
    responses_lib.add(responses_lib.GET, EP3_URL, body=DUMMY_BYTES, status=200)


class TestFullDownloadFlow:
    @responses_lib.activate
    def test_creates_all_expected_files(self, tmp_config, tmp_podcast_dir, sample_feed_xml):
        _register_all_mocks(sample_feed_xml)
        subscribe.main(tmp_config)

        feed_dir = tmp_podcast_dir / "testpod"
        assert feed_dir.is_dir(), "Feed subdirectory was not created"

        assert (feed_dir / "feed.json").exists(), "feed.json missing"
        assert (feed_dir / "original.json").exists(), "original.json missing"
        assert (feed_dir / "feed.jpg").exists(), "feed.jpg missing"

        mp3_files = list(feed_dir.glob("*.mp3"))
        ep_json_files = [f for f in feed_dir.glob("*.json") if f.name not in ("feed.json", "original.json")]

        assert len(mp3_files) == 3, f"Expected 3 mp3 files, got {len(mp3_files)}: {mp3_files}"
        assert len(ep_json_files) == 3, f"Expected 3 episode json files, got {len(ep_json_files)}: {ep_json_files}"

    @responses_lib.activate
    def test_feed_json_has_correct_content(self, tmp_config, tmp_podcast_dir, sample_feed_xml):
        _register_all_mocks(sample_feed_xml)
        subscribe.main(tmp_config)

        feed_dir = tmp_podcast_dir / "testpod"
        with open(feed_dir / "feed.json") as f:
            meta = json.load(f)

        assert meta["title"] == "Test Podcast"
        assert "summary" in meta
        assert "url" in meta

    @responses_lib.activate
    def test_episode_json_has_expected_fields(self, tmp_config, tmp_podcast_dir, sample_feed_xml):
        _register_all_mocks(sample_feed_xml)
        subscribe.main(tmp_config)

        feed_dir = tmp_podcast_dir / "testpod"
        ep_json_files = [f for f in feed_dir.glob("*.json") if f.name not in ("feed.json", "original.json")]
        assert ep_json_files

        with open(ep_json_files[0]) as f:
            ep_meta = json.load(f)

        assert "title" in ep_meta
        assert "audio_url" in ep_meta
        assert ep_meta["audio_url"] in (EP1_URL, EP2_URL, EP3_URL)


# ─── Test 5: Idempotent downloads ────────────────────────────────────────────

class TestIdempotentDownloads:
    @responses_lib.activate
    def test_audio_files_not_re_downloaded(self, tmp_config, tmp_podcast_dir, sample_feed_xml):
        # First run - downloads everything
        _register_all_mocks(sample_feed_xml)
        subscribe.main(tmp_config)

        # Second run - feed re-fetched, audio/image skipped
        responses_lib.add(responses_lib.GET, FEED_URL, body=sample_feed_xml.encode(), status=200)
        subscribe.main(tmp_config)

        ep1_calls = [c for c in responses_lib.calls if c.request.url == EP1_URL]
        ep2_calls = [c for c in responses_lib.calls if c.request.url == EP2_URL]
        ep3_calls = [c for c in responses_lib.calls if c.request.url == EP3_URL]

        assert len(ep1_calls) == 1, f"ep1 should only be fetched once, got {len(ep1_calls)}"
        assert len(ep2_calls) == 1, f"ep2 should only be fetched once, got {len(ep2_calls)}"
        assert len(ep3_calls) == 1, f"ep3 should only be fetched once, got {len(ep3_calls)}"

    @responses_lib.activate
    def test_no_error_on_second_run(self, tmp_config, tmp_podcast_dir, sample_feed_xml):
        _register_all_mocks(sample_feed_xml)
        subscribe.main(tmp_config)

        responses_lib.add(responses_lib.GET, FEED_URL, body=sample_feed_xml.encode(), status=200)
        # Should not raise
        subscribe.main(tmp_config)
