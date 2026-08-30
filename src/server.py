import config
import json
import os
import xml.etree.ElementTree as ET
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import unquote

PORT = 9988
_config_file = None
_cfg_cache = {"key": None, "data": None}

ITUNES_NS = 'http://www.itunes.com/dtds/podcast-1.0.dtd'
ET.register_namespace('itunes', ITUNES_NS)

CHUNK = 65536


def load_config():
    """Read the config file, reparsing only when its path or mtime changes."""
    try:
        mtime = os.path.getmtime(_config_file)
    except OSError:
        mtime = None
    key = (_config_file, mtime)
    if _cfg_cache["key"] != key:
        _cfg_cache["data"] = config.file(_config_file)
        _cfg_cache["key"] = key
    return _cfg_cache["data"]


def get_mime(path):
    if path.endswith('.xml'):
        return 'application/rss+xml'
    if path.endswith('.mp3'):
        return 'audio/mpeg'
    if path.endswith('.m4a'):
        return 'audio/mp4'
    if path.endswith('.ogg') or path.endswith('.opus'):
        return 'audio/ogg'
    if path.endswith('.jpg') or path.endswith('.jpeg'):
        return 'image/jpeg'
    if path.endswith('.png'):
        return 'image/png'
    return 'application/octet-stream'


def listing_html(base_path, cfg):
    subs_path = config.subscriptions_path(cfg)
    generate_cfg = cfg.get('generate', {}) or {}
    custom_feeds = generate_cfg.get('feeds', []) or []

    rows = []
    if os.path.isdir(subs_path):
        for feed_id in sorted(os.listdir(subs_path)):
            feed_dir = os.path.join(subs_path, feed_id)
            if not os.path.isdir(feed_dir):
                continue
            feed_json_path = os.path.join(feed_dir, 'meta.json')
            if not os.path.exists(feed_json_path):
                continue
            with open(feed_json_path) as f:
                meta = json.load(f)
            title = meta.get('title') or feed_id
            episodes_dir = os.path.join(feed_dir, 'episodes')
            episode_count = sum(
                1 for fn in os.listdir(episodes_dir)
                if fn.endswith('.json')
            ) if os.path.isdir(episodes_dir) else 0
            artwork = f'/subscriptions/{feed_id}/feed.jpg' if os.path.exists(os.path.join(feed_dir, 'feed.jpg')) else ''
            xml_url = f'/feeds/{feed_id}.xml'
            img_tag = f'<img src="{artwork}" width="64" height="64" style="vertical-align:middle">' if artwork else ''
            rows.append(
                f'<tr><td>{img_tag}</td>'
                f'<td>{title}</td>'
                f'<td>{episode_count}</td>'
                f'<td><a href="{xml_url}">{xml_url}</a></td></tr>'
            )

    # Custom feeds
    custom_rows = []
    for fc in custom_feeds:
        name = fc.get('name', '')
        fid = fc.get('id', '')
        xml_url = f'/feeds/{fid}.xml'
        custom_rows.append(f'<tr><td></td><td>{name} (custom)</td><td></td><td><a href="{xml_url}">{xml_url}</a></td></tr>')

    all_rows = '\n'.join(rows + custom_rows)
    return f"""<!DOCTYPE html>
<html><head><title>Podderton</title></head>
<body>
<h1>Podderton</h1>
<p>Combined feed: <a href="/feeds.xml">/feeds.xml</a></p>
<table border="1" cellpadding="6">
<tr><th>Art</th><th>Feed</th><th>Episodes</th><th>XML</th></tr>
{all_rows}
</table>
</body></html>"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print(f"[{self.address_string()}] {fmt % args}")

    def _write_body(self, data):
        if self.command != 'HEAD':
            self.wfile.write(data)

    def public_base(self, cfg):
        """Absolute base URL for feed links: config override, else request headers."""
        override = config.public_url(cfg)
        if override:
            return override
        proto = self.headers.get('X-Forwarded-Proto', 'http')
        host = self.headers.get('X-Forwarded-Host') or self.headers.get('Host')
        if not host:
            host = f'localhost:{PORT}'
        return f'{proto}://{host}'

    def send_feed(self, file_path, cfg):
        """Serve an RSS file, rewriting site-relative URLs to absolute."""
        if not os.path.isfile(file_path):
            self.send_error(404, 'Not Found')
            return
        try:
            tree = ET.parse(file_path)
        except ET.ParseError:
            self.send_file(file_path, 'application/rss+xml')
            return
        base = self.public_base(cfg)
        root = tree.getroot()
        for el in root.iter():
            tag = el.tag.split('}')[-1]
            if tag == 'enclosure' and el.get('url', '').startswith('/'):
                el.set('url', base + el.get('url'))
            elif tag == 'image' and el.get('href', '').startswith('/'):
                el.set('href', base + el.get('href'))
            elif tag == 'url' and el.text and el.text.startswith('/'):
                el.text = base + el.text
        body = ET.tostring(root, encoding='utf-8', xml_declaration=True)
        self.send_response(200)
        self.send_header('Content-Type', 'application/rss+xml')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self._write_body(body)

    def send_file(self, file_path, content_type):
        if not os.path.isfile(file_path):
            self.send_error(404, 'Not Found')
            return
        size = os.path.getsize(file_path)

        start, end, status = 0, size - 1, 200
        rng = self.headers.get('Range')
        if rng and rng.startswith('bytes='):
            spec = rng[len('bytes='):].split(',')[0].strip()
            lo, _, hi = spec.partition('-')
            try:
                if lo:
                    start = int(lo)
                    end = int(hi) if hi else size - 1
                elif hi:
                    start = max(0, size - int(hi))
                end = min(end, size - 1)
                if 0 <= start <= end:
                    status = 206
            except ValueError:
                status = 200

        length = end - start + 1 if status == 206 else size
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Accept-Ranges', 'bytes')
        self.send_header('Content-Length', str(length))
        if status == 206:
            self.send_header('Content-Range', f'bytes {start}-{end}/{size}')
        self.end_headers()

        if self.command == 'HEAD':
            return
        with open(file_path, 'rb') as f:
            if status == 206:
                f.seek(start)
            remaining = length
            while remaining > 0:
                chunk = f.read(min(CHUNK, remaining))
                if not chunk:
                    break
                self.wfile.write(chunk)
                remaining -= len(chunk)

    def do_HEAD(self):
        self.do_GET()

    def do_GET(self):
        cfg = load_config()
        base_path = config.basepath(cfg)
        path = unquote(self.path.split('?')[0])

        # Root listing page
        if path == '/':
            webpage_cfg = cfg.get('webpage', {}) or {}
            display = webpage_cfg.get('display', True)
            if display is False or str(display).lower() == 'false':
                body = b'Podderton is running.'
                self.send_response(200)
                self.send_header('Content-Type', 'text/plain')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self._write_body(body)
            else:
                html = listing_html(base_path, cfg).encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.send_header('Content-Length', str(len(html)))
                self.end_headers()
                self._write_body(html)
            return

        # /feeds.xml — default combined feed
        if path == '/feeds.xml':
            self.send_feed(os.path.join(base_path, 'feeds', 'feeds.xml'), cfg)
            return

        # /feeds/<id>.xml
        if path.startswith('/feeds/') and path.endswith('.xml'):
            fname = os.path.basename(path)
            self.send_feed(os.path.join(base_path, 'feeds', fname), cfg)
            return

        # /<id>.xml — short custom-feed route
        stripped = path.lstrip('/')
        if stripped.endswith('.xml') and '/' not in stripped:
            candidate = os.path.join(base_path, 'feeds', os.path.basename(stripped))
            if os.path.isfile(candidate):
                self.send_feed(candidate, cfg)
                return

        # /<feed_id>/... (files within the podcast tree)
        parts = stripped.split('/')
        if len(parts) >= 2:
            root = os.path.realpath(base_path)
            requested = os.path.realpath(os.path.join(base_path, *parts))
            if requested != root and not requested.startswith(root + os.sep):
                self.send_error(404, 'Not Found')
                return
            self.send_file(requested, get_mime(parts[-1]))
            return

        self.send_error(404, 'Not Found')


def main(config_file):
    global _config_file
    _config_file = config_file
    server = HTTPServer(('0.0.0.0', PORT), Handler)
    print(f'Serving on http://0.0.0.0:{PORT}')
    server.serve_forever()
