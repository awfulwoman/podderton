import os
import sys
import json
import time
import threading
import pytest
import yaml
import responses as responses_lib
import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../src"))

import config
import subscribe
import publish
import server

FEED_URL = "http://example.com/feed.xml"
COVER_URL = "http://example.com/cover.jpg"
EP1_URL = "http://example.com/episode1.mp3"
EP2_URL = "http://example.com/episode2.mp3"
EP3_URL = "http://example.com/episode3.mp3"
DUMMY_BYTES = b"\xff\xfb\x90\x00" * 256
DUMMY_IMAGE = b"\xff\xd8\xff\xe0" * 64


def _mock_subscribe(sample_feed_xml):
    responses_lib.add(responses_lib.GET, FEED_URL, body=sample_feed_xml.encode(), status=200)
    responses_lib.add(responses_lib.GET, COVER_URL, body=DUMMY_IMAGE, status=200)
    responses_lib.add(responses_lib.GET, EP1_URL, body=DUMMY_BYTES, status=200)
    responses_lib.add(responses_lib.GET, EP2_URL, body=DUMMY_BYTES, status=200)
    responses_lib.add(responses_lib.GET, EP3_URL, body=DUMMY_BYTES, status=200)


# ─── Test 1: Default config creation ─────────────────────────────────────────

class TestDefaultConfigCreation:
    def test_creates_config_with_defaults(self, tmp_path):
        config_path = str(tmp_path / "config" / "feeds.yaml")
        result = config.file(config_path)

        assert os.path.exists(config_path)
        assert "path" in result
        assert "subscribe" in result
        assert "generate" in result
        assert result["subscribe"]["feeds"] == []
        assert result["generate"]["type"] == "separate"


# ─── Test 2: Config loading from existing file ────────────────────────────────

class TestConfigLoading:
    def test_loads_existing_config(self, tmp_path):
        podcast_dir = tmp_path / "podcasts"
        podcast_dir.mkdir()
        config_data = {
            "path": str(podcast_dir),
            "subscribe": {
                "feeds": [{"name": "My Show", "id": "myshow", "url": FEED_URL}]
            },
            "generate": {"type": "separate"},
        }
        config_path = tmp_path / "feeds.yaml"
        with open(config_path, "w") as f:
            yaml.dump(config_data, f)

        result = config.file(str(config_path))

        assert result["subscribe"]["feeds"][0]["id"] == "myshow"
        assert config.basepath(result) == str(podcast_dir)


# ─── Test 3: Directory structure creation ────────────────────────────────────

class TestDirectoryStructure:
    @responses_lib.activate
    def test_creates_expected_dirs_and_files(self, tmp_path, sample_feed_xml):
        podcast_dir = tmp_path / "podcasts"
        podcast_dir.mkdir()
        config_data = {
            "path": str(podcast_dir),
            "subscribe": {
                "feeds": [{"name": "Test Feed", "id": "testfeed", "url": FEED_URL}]
            },
            "generate": {"type": "separate"},
        }
        config_path = tmp_path / "feeds.yaml"
        with open(config_path, "w") as f:
            yaml.dump(config_data, f)

        _mock_subscribe(sample_feed_xml)
        subscribe.main(str(config_path))

        assert podcast_dir.is_dir()
        feed_dir = podcast_dir / "testfeed"
        assert feed_dir.is_dir()
        assert (feed_dir / "feed.json").exists()
        assert (feed_dir / "original.json").exists()

        with open(feed_dir / "feed.json") as f:
            meta = json.load(f)
        assert "title" in meta
        assert "summary" in meta
        assert "url" in meta


# ─── Test 4: Server starts and responds ──────────────────────────────────────

class TestServerStartup:
    def test_server_responds(self, tmp_path, sample_feed_xml):
        podcast_dir = tmp_path / "podcasts"
        podcast_dir.mkdir()
        config_data = {
            "path": str(podcast_dir),
            "subscribe": {
                "feeds": [{"name": "Test Feed", "id": "testfeed", "url": FEED_URL}]
            },
            "generate": {"type": "separate"},
        }
        config_path = str(tmp_path / "feeds.yaml")
        with open(config_path, "w") as f:
            yaml.dump(config_data, f)

        # Populate directory with mocked HTTP (context manager avoids leaking into server poll)
        with responses_lib.RequestsMock() as rsps:
            rsps.add(rsps.GET, FEED_URL, body=sample_feed_xml.encode(), status=200)
            rsps.add(rsps.GET, COVER_URL, body=DUMMY_IMAGE, status=200)
            rsps.add(rsps.GET, EP1_URL, body=DUMMY_BYTES, status=200)
            rsps.add(rsps.GET, EP2_URL, body=DUMMY_BYTES, status=200)
            rsps.add(rsps.GET, EP3_URL, body=DUMMY_BYTES, status=200)
            subscribe.main(config_path)

        publish.main(config_path)

        t = threading.Thread(target=server.main, args=(config_path,), daemon=True)
        t.start()

        resp = None
        for _ in range(30):
            try:
                resp = requests.get("http://localhost:9988/", timeout=1)
                if resp.status_code == 200:
                    break
            except Exception:
                pass
            time.sleep(0.5)

        assert resp is not None and resp.status_code == 200
        assert "Podderton" in resp.text or "text" in resp.headers.get("Content-Type", "")
