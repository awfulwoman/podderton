import os
import pytest
import yaml

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


@pytest.fixture
def sample_feed_xml():
    with open(os.path.join(FIXTURES_DIR, "sample_feed.xml"), "r") as f:
        return f.read()


@pytest.fixture
def tmp_podcast_dir(tmp_path):
    podcast_dir = tmp_path / "podcasts"
    podcast_dir.mkdir()
    return podcast_dir


@pytest.fixture
def tmp_config(tmp_path, tmp_podcast_dir):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    config_path = config_dir / "feeds.yaml"
    config_data = {
        "path": str(tmp_podcast_dir),
        "subscribe": {
            "feeds": [
                {
                    "name": "Test Podcast",
                    "id": "testpod",
                    "url": "http://example.com/feed.xml",
                }
            ]
        },
        "generate": {"type": "separate"},
    }
    with open(config_path, "w") as f:
        yaml.dump(config_data, f)
    return str(config_path)
