import config
import json
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import unquote

PORT = 9988
_config_file = None


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
    feeds_dir = os.path.join(base_path, 'feeds')
    generate_cfg = cfg.get('generate', {}) or {}
    custom_feeds = generate_cfg.get('feeds', []) or []

    rows = []
    for feed_id in sorted(os.listdir(base_path)):
        feed_dir = os.path.join(base_path, feed_id)
        if not os.path.isdir(feed_dir) or feed_id == 'feeds':
            continue
        feed_json_path = os.path.join(feed_dir, 'feed.json')
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
        artwork = f'/{feed_id}/feed.jpg' if os.path.exists(os.path.join(feed_dir, 'feed.jpg')) else ''
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

    def send_file(self, file_path, content_type):
        if not os.path.isfile(file_path):
            self.send_error(404, 'Not Found')
            return
        size = os.path.getsize(file_path)
        self.send_response(200)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(size))
        self.end_headers()
        with open(file_path, 'rb') as f:
            self.wfile.write(f.read())

    def do_GET(self):
        cfg = config.file(_config_file)
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
                self.wfile.write(body)
            else:
                html = listing_html(base_path, cfg).encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.send_header('Content-Length', str(len(html)))
                self.end_headers()
                self.wfile.write(html)
            return

        # /feeds.xml — default combined feed
        if path == '/feeds.xml':
            self.send_file(os.path.join(base_path, 'feeds', 'feeds.xml'), 'application/rss+xml')
            return

        # /feeds/<id>.xml
        if path.startswith('/feeds/') and path.endswith('.xml'):
            fname = path[len('/feeds/'):]
            self.send_file(os.path.join(base_path, 'feeds', fname), 'application/rss+xml')
            return

        # /<feed_id>/... (files within feed directory)
        parts = path.lstrip('/').split('/')
        if len(parts) >= 2:
            file_path = os.path.join(base_path, *parts)
            self.send_file(file_path, get_mime(parts[-1]))
            return

        self.send_error(404, 'Not Found')


def main(config_file):
    global _config_file
    _config_file = config_file
    server = HTTPServer(('0.0.0.0', PORT), Handler)
    print(f'Serving on http://0.0.0.0:{PORT}')
    server.serve_forever()
