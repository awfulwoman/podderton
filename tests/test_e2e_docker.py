"""
E2E Docker smoke test: container boots and serves feeds.
Requires Docker to be available. Skip otherwise.
Run with: .venv/bin/pytest tests/test_e2e_docker.py -v -m e2e
"""

import shutil
import socket
import subprocess
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest
import requests

DOCKER_AVAILABLE = shutil.which("docker") is not None

# Minimal valid MP3: ID3v2 header + one silent MPEG frame (enough for a real file)
_MINIMAL_MP3 = (
    b"ID3\x03\x00\x00\x00\x00\x00\x00"  # ID3v2.3 header, 0 bytes of tags
    + b"\xff\xfb\x90\x00"               # MPEG1, Layer3, 128kbps, 44100Hz
    + b"\x00" * 413                     # silent frame payload
)

_FEED_XML_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd">
  <channel>
    <title>E2E Test Feed</title>
    <description>Test</description>
    <itunes:summary>E2E test podcast summary</itunes:summary>
    <link>http://example.com</link>
    <item>
      <title>Episode 1</title>
      <description>First episode</description>
      <enclosure url="{audio_url}" length="423" type="audio/mpeg"/>
      <pubDate>Mon, 01 Jan 2024 00:00:00 +0000</pubDate>
    </item>
  </channel>
</rss>"""


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


class _FeedServer(BaseHTTPRequestHandler):
    """Minimal HTTP server that serves a podcast feed and a tiny MP3."""

    feed_xml: bytes = b""

    def log_message(self, fmt, *args):
        pass  # Suppress request logs

    def do_GET(self):
        if self.path == "/feed.xml":
            self.send_response(200)
            self.send_header("Content-Type", "application/rss+xml")
            self.send_header("Content-Length", str(len(self.feed_xml)))
            self.end_headers()
            self.wfile.write(self.feed_xml)
        elif self.path == "/episode1.mp3":
            self.send_response(200)
            self.send_header("Content-Type", "audio/mpeg")
            self.send_header("Content-Length", str(len(_MINIMAL_MP3)))
            self.end_headers()
            self.wfile.write(_MINIMAL_MP3)
        else:
            self.send_error(404)


@pytest.mark.e2e
@pytest.mark.skipif(not DOCKER_AVAILABLE, reason="Docker not available")
def test_full_container_lifecycle():
    """Build image, run container with local feed, verify it boots and serves."""
    repo_root = Path(__file__).parent.parent

    # Build the image
    build_result = subprocess.run(
        ["docker", "build", "-t", "podderton-test", str(repo_root)],
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert build_result.returncode == 0, f"Docker build failed:\n{build_result.stderr}"

    # Start local feed server so Docker container can download from it.
    # On macOS Docker Desktop, host.docker.internal resolves to the host.
    feed_port = _find_free_port()
    server_port = _find_free_port()
    host_alias = "host.docker.internal"
    audio_url = f"http://{host_alias}:{feed_port}/episode1.mp3"
    feed_xml = _FEED_XML_TEMPLATE.format(audio_url=audio_url).encode()
    _FeedServer.feed_xml = feed_xml

    httpd = HTTPServer(("0.0.0.0", feed_port), _FeedServer)
    feed_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    feed_thread.start()

    container_id = None
    try:
        with tempfile.TemporaryDirectory() as config_dir, tempfile.TemporaryDirectory() as podcasts_dir:
            config_path = Path(config_dir)
            podcasts_path = Path(podcasts_dir)

            (config_path / "feeds.yaml").write_text(
                f"path: /podcasts\n"
                f"subscribe:\n"
                f"  feeds:\n"
                f"    - name: Test Feed\n"
                f"      id: testfeed\n"
                f"      url: http://{host_alias}:{feed_port}/feed.xml\n"
            )

            run_result = subprocess.run(
                [
                    "docker", "run", "-d",
                    "-p", f"{server_port}:9988",
                    "-v", f"{config_path}:/config",
                    "-v", f"{podcasts_path}:/podcasts",
                    "--add-host", f"host.docker.internal:host-gateway",
                    "podderton-test",
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
            assert run_result.returncode == 0, f"docker run failed:\n{run_result.stderr}"
            container_id = run_result.stdout.strip()

            # Wait for server to become available (max 60s — subscribe runs before server starts)
            base_url = f"http://localhost:{server_port}"
            deadline = time.time() + 60
            server_up = False
            while time.time() < deadline:
                try:
                    resp = requests.get(base_url + "/", timeout=2)
                    if resp.status_code == 200:
                        server_up = True
                        break
                except requests.exceptions.ConnectionError:
                    pass
                time.sleep(1)

            assert server_up, "Server did not become available within 60 seconds"

            # GET / returns 200 with HTML containing "testfeed"
            resp = requests.get(base_url + "/", timeout=10)
            assert resp.status_code == 200
            assert "testfeed" in resp.text, f"'testfeed' not in HTML:\n{resp.text[:500]}"

            # GET /feeds/testfeed.xml returns 200 with XML
            feed_resp = requests.get(base_url + "/feeds/testfeed.xml", timeout=10)
            assert feed_resp.status_code == 200
            content = feed_resp.text
            assert "<?xml" in content or "<rss" in content, \
                f"Expected XML:\n{content[:500]}"

            # podcasts volume: testfeed/ dir with at least one .mp3
            testfeed_dir = podcasts_path / "testfeed"
            assert testfeed_dir.is_dir(), "testfeed/ not found in podcasts volume"
            mp3_files = list(testfeed_dir.glob("*.mp3"))
            assert len(mp3_files) >= 1, f"No .mp3 in {testfeed_dir}"

            # podcasts volume: feeds/ dir with at least one .xml
            feeds_dir = podcasts_path / "feeds"
            assert feeds_dir.is_dir(), "feeds/ not found in podcasts volume"
            xml_files = list(feeds_dir.glob("*.xml"))
            assert len(xml_files) >= 1, f"No .xml in {feeds_dir}"

    finally:
        httpd.shutdown()
        if container_id:
            subprocess.run(["docker", "stop", container_id], capture_output=True, timeout=30)
            subprocess.run(["docker", "rm", container_id], capture_output=True, timeout=30)
