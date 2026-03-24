"""Tiny HTTP server that serves mock podcast feeds and dummy audio files."""

import os
from http.server import HTTPServer, SimpleHTTPRequestHandler

PORT = 8080
MOCK_DIR = os.path.dirname(os.path.abspath(__file__))


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=MOCK_DIR, **kwargs)

    def log_message(self, fmt, *args):
        print(f"[mock] {fmt % args}")

    def do_GET(self):
        path = self.path.split("?")[0]

        # Serve audio requests as tiny valid-ish MP3/M4A stubs
        if path.startswith("/audio/"):
            self.send_response(200)
            ext = os.path.splitext(path)[1]
            content_type = {
                ".mp3": "audio/mpeg",
                ".m4a": "audio/mp4",
                ".ogg": "audio/ogg",
            }.get(ext, "application/octet-stream")
            # 1KB of silence-ish bytes
            body = b"\x00" * 1024
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        # Serve artwork requests as tiny JPEG stubs
        if path.startswith("/art/"):
            self.send_response(200)
            # Minimal valid JPEG (2x2 white pixel)
            body = bytes.fromhex(
                "ffd8ffe000104a46494600010100000100010000"
                "ffdb004300080606070605080707070909080a0c"
                "140d0c0b0b0c1912130f141d1a1f1e1d1a1c1c"
                "20242e2720222c231c1c2837292c30313434341f"
                "27393d38323c2e333432ffc0000b080002000201"
                "011100ffc4001f000001050101010101010000000"
                "0000000000102030405060708090a0bffc4004010"
                "0002010303020403050504040000017d010203000"
                "41105122131410613516107227114328191a10823"
                "42b1c11552d1f02433627282090a161718191a25"
                "2627ffda00080101000003100002000000001ff39"
                "ffd9"
            )
            self.send_header("Content-Type", "image/jpeg")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        # Everything else (feed XML etc) served from filesystem
        super().do_GET()


if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", PORT), Handler)
    print(f"Mock feed server on http://0.0.0.0:{PORT}")
    print(f"Feeds:  http://mock:{PORT}/feeds/test-podcast.xml")
    print(f"        http://mock:{PORT}/feeds/another-podcast.xml")
    server.serve_forever()
