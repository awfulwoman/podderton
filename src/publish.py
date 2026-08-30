import config
import files
import os
import json
import xml.etree.ElementTree as ET
from email.utils import formatdate
import time

ITUNES_NS = 'http://www.itunes.com/dtds/podcast-1.0.dtd'
ET.register_namespace('itunes', ITUNES_NS)

_AUDIO_MIME = {
    '.mp3': 'audio/mpeg',
    '.m4a': 'audio/mp4',
    '.ogg': 'audio/ogg',
    '.opus': 'audio/opus',
}


def _it(tag):
    """Return a namespace-qualified iTunes tag name."""
    return f'{{{ITUNES_NS}}}{tag}'


def parse_date(date_str):
    """Parse a date string to a timestamp, return 0 on failure."""
    if not date_str:
        return 0
    for fmt in ('%a, %d %b %Y %H:%M:%S %z', '%a, %d %b %Y %H:%M:%S %Z',
                '%Y-%m-%dT%H:%M:%S%z', '%Y-%m-%dT%H:%M:%SZ'):
        try:
            import datetime
            return datetime.datetime.strptime(date_str, fmt).timestamp()
        except (ValueError, TypeError):
            pass
    return 0


def make_rss_feed(title, description, link, image_url, items, author=None, explicit=False):
    """Build an RSS 2.0 ElementTree from channel metadata and items list."""
    rss = ET.Element('rss', version='2.0')
    channel = ET.SubElement(rss, 'channel')
    ET.SubElement(channel, 'title').text = title
    ET.SubElement(channel, 'description').text = description
    ET.SubElement(channel, 'link').text = link or ''
    ET.SubElement(channel, _it('summary')).text = description or ''
    ET.SubElement(channel, _it('explicit')).text = 'yes' if explicit else 'no'
    if author:
        ET.SubElement(channel, _it('author')).text = author
    if image_url:
        img = ET.SubElement(channel, 'image')
        ET.SubElement(img, 'url').text = image_url
        ET.SubElement(img, 'title').text = title or ''
        ET.SubElement(img, 'link').text = link or ''
        ET.SubElement(channel, _it('image'), href=image_url)

    for item_data in items:
        item = ET.SubElement(channel, 'item')
        ET.SubElement(item, 'title').text = item_data.get('title') or ''
        ET.SubElement(item, 'description').text = item_data.get('summary') or ''
        guid = ET.SubElement(item, 'guid')
        guid.text = item_data.get('guid') or item_data.get('enclosure_url') or ''
        guid.set('isPermaLink', 'false')
        pub = item_data.get('published')
        if pub:
            ET.SubElement(item, 'pubDate').text = pub
        enclosure_url = item_data.get('enclosure_url', '')
        enclosure_len = str(item_data.get('enclosure_length', 0))
        ET.SubElement(item, 'enclosure', url=enclosure_url,
                      type=item_data.get('enclosure_type') or 'audio/mpeg',
                      length=enclosure_len)
        duration = item_data.get('duration')
        if duration:
            ET.SubElement(item, _it('duration')).text = str(duration)
        ep_image = item_data.get('image_url')
        if ep_image:
            ET.SubElement(item, _it('image'), href=ep_image)

    return ET.ElementTree(rss)


def gather_feed_items(feed_dir, feed_id):
    """Scan a feed directory and return a list of episode dicts sorted by date desc."""
    items = []
    episodes_dir = os.path.join(feed_dir, 'episodes')
    if not os.path.isdir(episodes_dir):
        return items
    for fname in os.listdir(episodes_dir):
        if not fname.endswith('.json'):
            continue
        json_path = os.path.join(episodes_dir, fname)
        with open(json_path) as f:
            try:
                ep = json.load(f)
            except Exception:
                continue
        stem = os.path.splitext(fname)[0]
        # Find corresponding audio file
        audio_file = None
        for ext in ('.mp3', '.m4a', '.ogg', '.opus'):
            candidate = os.path.join(episodes_dir, stem + ext)
            if os.path.exists(candidate):
                audio_file = stem + ext
                break
        enclosure_url = f'/subscriptions/{feed_id}/episodes/{audio_file}' if audio_file else ''
        enclosure_length = os.path.getsize(os.path.join(episodes_dir, audio_file)) if audio_file else 0
        enclosure_type = _AUDIO_MIME.get(os.path.splitext(audio_file)[1], 'audio/mpeg') if audio_file else 'audio/mpeg'
        items.append({
            'title': ep.get('title'),
            'summary': ep.get('summary'),
            'published': ep.get('published'),
            'duration': ep.get('duration'),
            'guid': ep.get('guid') or enclosure_url,
            'image_url': ep.get('image_url'),
            'enclosure_url': enclosure_url,
            'enclosure_length': enclosure_length,
            'enclosure_type': enclosure_type,
            '_ts': parse_date(ep.get('published')),
        })
    items.sort(key=lambda x: x['_ts'], reverse=True)
    return items


def generate_separate(base_path, subs_path, feeds_dir):
    """Generate one XML feed per feed directory under subs_path."""
    files.write_dir(feeds_dir)

    for feed_id in os.listdir(subs_path):
        feed_dir = os.path.join(subs_path, feed_id)
        if not os.path.isdir(feed_dir):
            continue
        feed_json_path = os.path.join(feed_dir, 'meta.json')
        if not os.path.exists(feed_json_path):
            continue
        with open(feed_json_path) as f:
            feed_meta = json.load(f)

        image_url = f'/subscriptions/{feed_id}/feed.jpg' if os.path.exists(os.path.join(feed_dir, 'feed.jpg')) else None
        items = gather_feed_items(feed_dir, feed_id)
        tree = make_rss_feed(
            title=feed_meta.get('title', ''),
            description=feed_meta.get('summary', ''),
            link=feed_meta.get('url', ''),
            image_url=image_url,
            items=items,
            author=feed_meta.get('author'),
        )
        out_path = os.path.join(feeds_dir, f'{feed_id}.xml')
        tree.write(out_path, encoding='unicode', xml_declaration=True)
        print(f"Generated feed: {out_path}")


def get_all_feed_ids(subs_path):
    """Return list of feed IDs (subdirs with meta.json) under subs_path."""
    ids = []
    for feed_id in os.listdir(subs_path):
        feed_dir = os.path.join(subs_path, feed_id)
        if os.path.isdir(feed_dir):
            if os.path.exists(os.path.join(feed_dir, 'meta.json')):
                ids.append(feed_id)
    return ids


def gather_items_for_feeds(subs_path, feed_ids):
    """Gather and return all episodes from the given feed IDs, sorted newest first."""
    all_items = []
    for feed_id in feed_ids:
        feed_dir = os.path.join(subs_path, feed_id)
        if os.path.isdir(feed_dir):
            all_items.extend(gather_feed_items(feed_dir, feed_id))
    all_items.sort(key=lambda x: x['_ts'], reverse=True)
    return all_items


def generate_combined(base_path, subs_path, feeds_dir):
    """Generate a single feeds/feeds.xml with all episodes from all feeds."""
    files.write_dir(feeds_dir)

    feed_ids = get_all_feed_ids(subs_path)
    all_items = gather_items_for_feeds(subs_path, feed_ids)
    tree = make_rss_feed(
        title='Podderton Combined Feed',
        description='All subscribed podcasts',
        link='',
        image_url=None,
        items=all_items,
    )
    out_path = os.path.join(feeds_dir, 'feeds.xml')
    tree.write(out_path, encoding='unicode', xml_declaration=True)
    print(f"Generated feed: {out_path}")


def generate_default_all(base_path, subs_path, feeds_dir):
    """Generate feeds/feeds.xml as the default all-episodes feed."""
    files.write_dir(feeds_dir)

    feed_ids = get_all_feed_ids(subs_path)
    all_items = gather_items_for_feeds(subs_path, feed_ids)
    tree = make_rss_feed(
        title='Podderton Combined Feed',
        description='All subscribed podcasts',
        link='',
        image_url=None,
        items=all_items,
    )
    out_path = os.path.join(feeds_dir, 'feeds.xml')
    tree.write(out_path, encoding='unicode', xml_declaration=True)
    print(f"Generated feed: {out_path}")


def generate_custom_feeds(base_path, subs_path, feeds_dir, custom_feeds):
    """Generate custom named feeds from config generate.feeds list."""
    if not custom_feeds:
        return
    files.write_dir(feeds_dir)

    for feed_cfg in custom_feeds:
        name = feed_cfg.get('name', 'Custom Feed')
        feed_id = feed_cfg.get('id', 'custom')
        input_ids = feed_cfg.get('feeds', [])
        items = gather_items_for_feeds(subs_path, input_ids)
        tree = make_rss_feed(
            title=name,
            description='',
            link='',
            image_url=None,
            items=items,
        )
        out_path = os.path.join(feeds_dir, f'{feed_id}.xml')
        tree.write(out_path, encoding='unicode', xml_declaration=True)
        print(f"Generated custom feed: {out_path}")


def main(config_file):
    cfg = config.file(config_file)
    base_path = config.basepath(cfg)
    subs_path = config.subscriptions_path(cfg)
    feeds_dir = config.feeds_path(cfg)
    generate_cfg = cfg.get('generate', {}) or {}
    generate_type = generate_cfg.get('type', 'separate')
    custom_feeds = generate_cfg.get('feeds', [])

    type_disabled = generate_type is False or str(generate_type).lower() == 'false'

    if not type_disabled:
        if generate_type == 'combined':
            generate_combined(base_path, subs_path, feeds_dir)
        else:
            # separate (default) — one XML per feed + default feeds.xml
            generate_separate(base_path, subs_path, feeds_dir)
            generate_default_all(base_path, subs_path, feeds_dir)

    generate_custom_feeds(base_path, subs_path, feeds_dir, custom_feeds)
