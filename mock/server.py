"""Tiny HTTP server that serves mock podcast feeds, audio, and artwork."""

import os
from http.server import HTTPServer, SimpleHTTPRequestHandler

PORT = 8080
MOCK_DIR = os.path.dirname(os.path.abspath(__file__))


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=MOCK_DIR, **kwargs)

    def log_message(self, fmt, *args):
        print(f"[mock] {fmt % args}")


if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", PORT), Handler)
    print(f"Mock feed server on http://0.0.0.0:{PORT}")
    print(f"Feeds:  http://mock:{PORT}/feeds/test-podcast.xml")
    print(f"        http://mock:{PORT}/feeds/another-podcast.xml")
    server.serve_forever()
