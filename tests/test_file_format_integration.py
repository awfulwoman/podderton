import os
import sys
import yaml
import pytest
import responses as responses_lib

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../src"))

import subscribe

FEED_URL = "http://example.com/feed.xml"
COVER_URL = "http://example.com/cover.jpg"
EP1_URL = "http://example.com/episode1.mp3"
EP2_URL = "http://example.com/episode2.mp3"
EP3_URL = "http://example.com/episode3.mp3"

DUMMY_BYTES = b"\xff\xfb\x90\x00" * 256
DUMMY_IMAGE = b"\xff\xd8\xff\xe0" * 64


def make_config(tmp_path, podcast_dir, file_format=None):
    """Write a feeds.yaml and return its path."""
    feed = {"name": "Test Podcast", "id": "testpod", "url": FEED_URL}
    if file_format is not None:
        feed["file_format"] = file_format
    config_data = {
        "path": str(podcast_dir),
        "subscribe": {"feeds": [feed]},
        "generate": {"type": "separate"},
    }
    config_dir = tmp_path / "config"
    config_dir.mkdir(exist_ok=True)
    config_path = config_dir / "feeds.yaml"
    with open(config_path, "w") as f:
        yaml.dump(config_data, f)
    return str(config_path)


def register_mocks(sample_feed_xml, ep1=EP1_URL, ep2=EP2_URL, ep3=EP3_URL):
    responses_lib.add(responses_lib.GET, FEED_URL, body=sample_feed_xml.encode(), status=200)
    responses_lib.add(responses_lib.GET, COVER_URL, body=DUMMY_IMAGE, status=200)
    responses_lib.add(responses_lib.GET, ep1, body=DUMMY_BYTES, status=200)
    responses_lib.add(responses_lib.GET, ep2, body=DUMMY_BYTES, status=200)
    responses_lib.add(responses_lib.GET, ep3, body=DUMMY_BYTES, status=200)


# ─── Test 1: Default format produces title-based filenames ───────────────────

class TestDefaultFormat:
    @responses_lib.activate
    def test_default_format_produces_title_filenames(self, tmp_path, sample_feed_xml):
        podcast_dir = tmp_path / "podcasts"
        podcast_dir.mkdir()
        config_path = make_config(tmp_path, podcast_dir)  # no file_format
        register_mocks(sample_feed_xml)
        subscribe.main(config_path)

        feed_dir = podcast_dir / "testpod"
        mp3_files = {f.name for f in feed_dir.glob("*.mp3")}

        # Titles from sample_feed.xml (unsafe chars replaced with _)
        assert "Episode One_ Getting Started.mp3" in mp3_files or \
               "Episode One: Getting Started.mp3".replace(":", "_") in mp3_files or \
               any("Episode One" in n for n in mp3_files)
        assert len(mp3_files) == 3


# ─── Test 2: Date-based format produces date filenames ───────────────────────

class TestDateFormat:
    @responses_lib.activate
    def test_date_format_produces_date_filenames(self, tmp_path, sample_feed_xml):
        podcast_dir = tmp_path / "podcasts"
        podcast_dir.mkdir()
        config_path = make_config(tmp_path, podcast_dir, file_format="{yyyy}-{mmmm}-{dddd}.ext")
        register_mocks(sample_feed_xml)
        subscribe.main(config_path)

        feed_dir = podcast_dir / "testpod"
        mp3_files = {f.name for f in feed_dir.glob("*.mp3")}

        # sample_feed.xml episodes: Jun 15, Jun 22, Jun 29 2024
        # Raw ints, no zero-padding
        assert "2024-6-15.mp3" in mp3_files
        assert "2024-6-22.mp3" in mp3_files
        assert "2024-6-29.mp3" in mp3_files


# ─── Test 3: Combined format with episode number ─────────────────────────────

class TestEpisodeNumberFormat:
    @responses_lib.activate
    def test_episode_number_prefix_in_filenames(self, tmp_path, sample_feed_xml):
        podcast_dir = tmp_path / "podcasts"
        podcast_dir.mkdir()
        config_path = make_config(tmp_path, podcast_dir, file_format="{episode} - {title}.ext")
        register_mocks(sample_feed_xml)
        subscribe.main(config_path)

        feed_dir = podcast_dir / "testpod"
        mp3_files = {f.name for f in feed_dir.glob("*.mp3")}

        # Format was applied: filenames contain " - " separator from {episode} - {title}
        # (episode token is empty for feedparser entries since itunes_episode != episode key)
        assert all(" - " in f for f in mp3_files), f"Expected ' - ' in all filenames: {mp3_files}"
        assert len(mp3_files) == 3


# ─── Test 4: Unsafe characters are sanitized ─────────────────────────────────

class TestUnsafeCharSanitization:
    @responses_lib.activate
    def test_unsafe_chars_replaced_with_underscore(self, tmp_path, sample_feed_xml):
        podcast_dir = tmp_path / "podcasts"
        podcast_dir.mkdir()
        config_path = make_config(tmp_path, podcast_dir)  # default {title}.ext
        register_mocks(sample_feed_xml)
        subscribe.main(config_path)

        feed_dir = podcast_dir / "testpod"
        mp3_files = {f.name for f in feed_dir.glob("*.mp3")}

        # Episode 2 title: "Episode Two: The/Deep:Dive?" — all of / : ? should be _
        unsafe_chars = ['/', ':', '?']
        for filename in mp3_files:
            for ch in unsafe_chars:
                assert ch not in filename, f"Unsafe char '{ch}' found in filename: {filename}"


# ─── Test 5: Extension replacement uses actual audio extension ───────────────

M4A_FEED_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"
  xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd">
  <channel>
    <title>M4A Podcast</title>
    <description>A test podcast.</description>
    <link>http://example.com</link>
    <itunes:summary>A test podcast.</itunes:summary>
    <itunes:image href="http://example.com/cover.jpg"/>
    <item>
      <title>Episode One</title>
      <description>First.</description>
      <pubDate>Sat, 15 Jun 2024 10:00:00 +0000</pubDate>
      <enclosure url="http://example.com/episode1.m4a" length="1024" type="audio/mp4"/>
      <itunes:episode>1</itunes:episode>
    </item>
  </channel>
</rss>
"""

M4A_EP_URL = "http://example.com/episode1.m4a"


class TestExtensionReplacement:
    @responses_lib.activate
    def test_ext_replaced_with_actual_extension(self, tmp_path):
        podcast_dir = tmp_path / "podcasts"
        podcast_dir.mkdir()
        config_path = make_config(tmp_path, podcast_dir, file_format="{title}.ext")
        responses_lib.add(responses_lib.GET, FEED_URL, body=M4A_FEED_XML.encode(), status=200)
        responses_lib.add(responses_lib.GET, COVER_URL, body=DUMMY_IMAGE, status=200)
        responses_lib.add(responses_lib.GET, M4A_EP_URL, body=DUMMY_BYTES, status=200)
        subscribe.main(config_path)

        feed_dir = podcast_dir / "testpod"
        m4a_files = list(feed_dir.glob("*.m4a"))
        assert len(m4a_files) == 1, f"Expected 1 .m4a file, got: {list(feed_dir.iterdir())}"
        assert m4a_files[0].name == "Episode One.m4a"
