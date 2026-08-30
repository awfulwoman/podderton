"""Regression tests for the review fixes:

- config resolves PODDERTON_PATH and survives a read-only config dir
- the listing page renders every feed and does not crash when empty
- the HTTP server blocks path traversal and honours Range
- generated feeds carry absolute enclosure URLs and a <guid> per item
- the documented {yyyy-mm-dd} file_format works; unknown tokens fall back
"""

import json
import os
import sys
import threading
import time

import pytest
import requests
import responses as responses_lib
import yaml

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../src"))

import config
import publish
import server
import subscribe

FEED_URL = "http://example.com/feed.xml"
COVER_URL = "http://example.com/cover.jpg"
EP_URLS = [f"http://example.com/episode{i}.mp3" for i in (1, 2, 3)]
DUMMY_BYTES = b"\xff\xfb\x90\x00" * 256
DUMMY_IMAGE = b"\xff\xd8\xff\xe0" * 64


def _register_mocks(sample_feed_xml):
    responses_lib.add(responses_lib.GET, FEED_URL, body=sample_feed_xml.encode(), status=200)
    responses_lib.add(responses_lib.GET, COVER_URL, body=DUMMY_IMAGE, status=200)
    for url in EP_URLS:
        responses_lib.add(responses_lib.GET, url, body=DUMMY_BYTES, status=200)


def _write_config(tmp_path, podcast_dir, file_format=None, extra_feed=None):
    feed = {"name": "Test Podcast", "id": "testpod", "url": FEED_URL}
    if file_format is not None:
        feed["file_format"] = file_format
    feeds = [feed]
    if extra_feed:
        feeds.append(extra_feed)
    cfg = {
        "path": str(podcast_dir),
        "subscribe": {"feeds": feeds},
        "generate": {"type": "separate"},
    }
    p = tmp_path / "feeds.yaml"
    p.write_text(yaml.dump(cfg))
    return str(p)


# ─── config ─────────────────────────────────────────────────────────────────

def test_basepath_honours_podderton_path(monkeypatch):
    monkeypatch.setenv("PODDERTON_PATH", "/mnt/pods")
    assert config.basepath({}) == "/mnt/pods"


def test_yaml_path_beats_env(monkeypatch):
    monkeypatch.setenv("PODDERTON_PATH", "/mnt/pods")
    assert config.basepath({"path": "/from/yaml"}) == "/from/yaml"


def test_config_file_survives_readonly_dir(tmp_path):
    ro = tmp_path / "config"
    ro.mkdir()
    ro.chmod(0o500)
    try:
        cfg = config.file(str(ro / "feeds.yaml"))
        assert "subscribe" in cfg and "generate" in cfg
        assert not (ro / "feeds.yaml").exists()
    finally:
        ro.chmod(0o700)


def test_public_url_normalises_and_defaults():
    assert config.public_url({"url": "https://x.example.com/"}) == "https://x.example.com"
    assert config.public_url({}) is None


# ─── listing page ───────────────────────────────────────────────────────────

def test_listing_shows_every_feed(tmp_path):
    subs = tmp_path / "subscriptions"
    for fid, title in [("alpha", "Alpha"), ("beta", "Beta"), ("gamma", "Gamma")]:
        (subs / fid / "episodes").mkdir(parents=True)
        (subs / fid / "meta.json").write_text(json.dumps({"title": title, "summary": "s", "url": "u"}))
    html = server.listing_html(str(tmp_path), {"path": str(tmp_path)})
    for title in ("Alpha", "Beta", "Gamma"):
        assert f"<td>{title}</td>" in html


def test_listing_handles_empty_subscriptions(tmp_path):
    (tmp_path / "subscriptions").mkdir()
    html = server.listing_html(str(tmp_path), {"path": str(tmp_path)})
    assert "Podderton" in html  # rendered without raising


# ─── running server: traversal + range ──────────────────────────────────────

def _serve(tmp_path):
    """Start server.Handler on an ephemeral port; return (base_url, httpd)."""
    cfg_path = tmp_path / "feeds.yaml"
    if not cfg_path.exists():
        cfg_path.write_text(yaml.dump({"path": str(tmp_path), "subscribe": {"feeds": []},
                                       "generate": {"type": "separate"}}))
    server._config_file = str(cfg_path)
    httpd = server.HTTPServer(("0.0.0.0", 0), server.Handler)
    server.PORT = httpd.server_address[1]
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    time.sleep(0.2)
    return f"http://127.0.0.1:{httpd.server_address[1]}", httpd


@pytest.fixture
def running_server(tmp_path):
    subs = tmp_path / "subscriptions" / "testpod" / "episodes"
    subs.mkdir(parents=True)
    (tmp_path / "subscriptions" / "testpod" / "meta.json").write_text(
        json.dumps({"title": "T", "summary": "s", "url": "u"})
    )
    (subs / "ep1.mp3").write_bytes(bytes(range(256)) * 8)  # 2048 bytes
    (tmp_path.parent / "SECRET.txt").write_text("classified")

    base, httpd = _serve(tmp_path)
    yield base, tmp_path
    httpd.shutdown()
    httpd.server_close()


def test_path_traversal_blocked(running_server):
    base, _ = running_server
    r = requests.get(base + "/%2e%2e/SECRET.txt", timeout=5)
    assert r.status_code == 404
    assert "classified" not in r.text


def test_range_request_returns_206_slice(running_server):
    base, _ = running_server
    r = requests.get(base + "/subscriptions/testpod/episodes/ep1.mp3",
                     headers={"Range": "bytes=10-19"}, timeout=5)
    assert r.status_code == 206
    assert len(r.content) == 10
    assert r.headers["Content-Range"] == "bytes 10-19/2048"
    assert r.headers["Accept-Ranges"] == "bytes"


# ─── generated feeds ────────────────────────────────────────────────────────

@responses_lib.activate
def test_publish_writes_relative_urls_and_guids(tmp_path, sample_feed_xml):
    podcast_dir = tmp_path / "podcasts"
    podcast_dir.mkdir()
    cfg_path = _write_config(tmp_path, podcast_dir)
    _register_mocks(sample_feed_xml)
    subscribe.main(cfg_path)
    publish.main(cfg_path)

    xml_on_disk = (podcast_dir / "feeds" / "testpod.xml").read_text()
    assert 'url="/subscriptions/' in xml_on_disk          # relative on disk
    assert xml_on_disk.count("<guid") == 3
    assert "xmlns:itunes" in xml_on_disk


def test_server_rewrites_feed_urls_to_absolute(tmp_path):
    feeds = tmp_path / "feeds"
    feeds.mkdir()
    (feeds / "testpod.xml").write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<rss version="2.0"><channel><title>T</title>'
        '<item><title>E1</title><guid isPermaLink="false">g1</guid>'
        '<enclosure url="/subscriptions/testpod/episodes/ep1.mp3" type="audio/mpeg" length="10"/>'
        '</item></channel></rss>'
    )
    base, httpd = _serve(tmp_path)
    try:
        r = requests.get(base + "/feeds/testpod.xml",
                         headers={"Host": "pods.example.com", "X-Forwarded-Proto": "https"},
                         timeout=5)
        r_short = requests.get(base + "/testpod.xml", timeout=5)
    finally:
        httpd.shutdown()
        httpd.server_close()
    assert r.status_code == 200
    assert 'url="https://pods.example.com/subscriptions/testpod/episodes/ep1.mp3"' in r.text
    assert r_short.status_code == 200  # documented short route works


# ─── file_format ────────────────────────────────────────────────────────────

@responses_lib.activate
def test_documented_ymd_format(tmp_path, sample_feed_xml):
    podcast_dir = tmp_path / "podcasts"
    podcast_dir.mkdir()
    cfg_path = _write_config(tmp_path, podcast_dir, file_format="{yyyy-mm-dd}.ext")
    _register_mocks(sample_feed_xml)
    subscribe.main(cfg_path)

    names = {f.name for f in (podcast_dir / "subscriptions" / "testpod" / "episodes").glob("*.mp3")}
    assert names == {"2024-06-15.mp3", "2024-06-22.mp3", "2024-06-29.mp3"}


@responses_lib.activate
def test_unknown_token_falls_back_to_title(tmp_path, sample_feed_xml):
    podcast_dir = tmp_path / "podcasts"
    podcast_dir.mkdir()
    cfg_path = _write_config(tmp_path, podcast_dir, file_format="{nonsense}.ext")
    _register_mocks(sample_feed_xml)
    subscribe.main(cfg_path)

    names = {f.name for f in (podcast_dir / "subscriptions" / "testpod" / "episodes").glob("*.mp3")}
    assert len(names) == 3
    assert all("{" not in n and "}" not in n for n in names)
