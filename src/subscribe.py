import config
import files
import json
import os
import feedparser
import validators
import remote
import utils

def subscriptions(configuration):
    """Get the subscriptions from the configuration."""
    # Extract the subscriptions from the configuration
    return configuration.get("subscribe", {}).get("feeds", [])

def _episode_guid(json_path):
    """Read the stored guid from an episode metadata file, or None."""
    try:
        with open(json_path) as f:
            return json.load(f).get("guid")
    except (OSError, ValueError):
        return None

def simplify_metadata(remote_feed, configured_feed):
    """Ensure the feed metadata exists."""

    if 'title' not in remote_feed or not remote_feed.title:
        raise Exception(f"No valid title exists.")       
    if 'summary' not in remote_feed or not remote_feed.summary:
        raise Exception(f"No valid summary exists.")

    data = {
        "title": remote_feed.title,
        "summary": remote_feed.summary,
        "url": configured_feed['url'],
        "author": remote_feed.get("author") or remote_feed.get("itunes_author"),
    }

    return data


def fetch_feed(feed_url):
    """Fetch and parse a feed once. Returns the feedparser result."""
    return feedparser.parse(remote.get_file(feed_url))

def get_meta(feed_url):
    """Fetch the feed metadata from the given feed URL."""
    return fetch_feed(feed_url).feed

def get_entries(feed_url):
    """Fetch the feed entries from the given feed URL."""
    return fetch_feed(feed_url).entries

def get_feed_image_url(meta):
    """Fetch the image from the given feed URL."""

    if not hasattr(meta, 'image'):
        return None
    if isinstance(meta.image, str) and validators.url(meta.image):
        return meta.image
    if hasattr(meta.image, 'href') and validators.url(meta.image.href):
        return meta.image.href
    return None


def main(config_file):
    cfg = config.file(config_file)
    configured_feeds = subscriptions(cfg)
    subs_path = config.subscriptions_path(cfg)
    any_downloaded = False

    if files.write_dir(subs_path):
        print("Subscriptions directory prepared.")


    for configured_feed in configured_feeds:
        parsed = fetch_feed(configured_feed.get("url"))
        feed_meta = parsed.feed
        entries = parsed.entries
        feed_dir = os.path.join(subs_path, configured_feed.get("id"))

        if files.write_dir(feed_dir):
            print(f"Directory for {configured_feed.get('name')} prepared.")

        if files.write_json(feed_meta, os.path.join(feed_dir, "source.json")):
            print(f"Original metadata for {configured_feed.get('name')} written.")

        simplified_meta = simplify_metadata(feed_meta, configured_feed)
        if files.write_json(simplified_meta, os.path.join(feed_dir, "meta.json")):
            print(f"Simplified metadata for {configured_feed.get('name')} written.")

        feed_image_path = os.path.join(feed_dir, "feed.jpg")
        if not os.path.exists(feed_image_path):
            feed_image_url = get_feed_image_url(feed_meta)
            if feed_image_url:
                if files.write_bytes(remote.get_file(feed_image_url), feed_image_path):
                    print(f"Artwork for {configured_feed.get('name')} written.")


        # Download episode audio files
        episodes_dir = os.path.join(feed_dir, "episodes")
        files.write_dir(episodes_dir)
        file_format = configured_feed.get("file_format", "{title}.ext")

        for entry in entries:
            # Find audio enclosure
            audio_url = None
            audio_type = None
            for link in getattr(entry, 'links', []):
                if link.get('rel') == 'enclosure':
                    audio_url = link.get('href')
                    audio_type = link.get('type', '')
                    break
            if not audio_url and hasattr(entry, 'enclosures') and entry.enclosures:
                enc = entry.enclosures[0]
                audio_url = enc.get('href')
                audio_type = enc.get('type', '')

            if not audio_url:
                continue

            # Determine extension
            ext = '.mp3'
            if audio_url and '.' in audio_url.split('?')[0].split('/')[-1]:
                ext = '.' + audio_url.split('?')[0].split('/')[-1].rsplit('.', 1)[-1]
            elif audio_type and '/' in audio_type:
                type_map = {'audio/mpeg': '.mp3', 'audio/mp4': '.m4a', 'audio/ogg': '.ogg', 'audio/x-m4a': '.m4a'}
                ext = type_map.get(audio_type, '.mp3')

            tokens = utils.define_string_tokens(entry)
            filename = utils.replace_string_tokens(file_format, tokens)
            if '{' in filename or '}' in filename:
                print(f"WARNING: unknown token in file_format {file_format!r}; using default")
                filename = utils.replace_string_tokens("{title}.ext", tokens)
            filename = filename.replace('.ext', ext)
            # Sanitize filename
            for ch in ['/', '\\', ':', '*', '?', '"', '<', '>', '|']:
                filename = filename.replace(ch, '_')

            guid = getattr(entry, 'id', None) or audio_url
            filepath = os.path.join(episodes_dir, filename)
            if os.path.exists(filepath):
                existing = _episode_guid(os.path.splitext(filepath)[0] + '.json')
                if existing is None or existing == guid:
                    continue  # already have this episode (or a pre-guid download)
                # Two distinct episodes resolve to the same filename — disambiguate.
                stem_name, ext_name = os.path.splitext(filename)
                n = 2
                while True:
                    filepath = os.path.join(episodes_dir, f"{stem_name} ({n}){ext_name}")
                    if not os.path.exists(filepath):
                        break
                    if _episode_guid(os.path.splitext(filepath)[0] + '.json') == guid:
                        break
                    n += 1
                if os.path.exists(filepath):
                    continue

            try:
                remote.download(audio_url, filepath)
                print(f"Downloaded: {entry.title}")
                any_downloaded = True
            except Exception as e:
                print(f"Failed to download {entry.title}: {e}")
                continue

            # Save episode metadata JSON
            stem = os.path.splitext(filepath)[0]
            json_path = stem + '.json'
            if not os.path.exists(json_path):
                episode_image_url = None
                if hasattr(entry, 'image') and hasattr(entry.image, 'href'):
                    episode_image_url = entry.image.href
                if not episode_image_url:
                    for link in getattr(entry, 'links', []):
                        if link.get('type', '').startswith('image/'):
                            episode_image_url = link.get('href')
                            break
                metadata = {
                    'title': getattr(entry, 'title', None),
                    'summary': getattr(entry, 'summary', getattr(entry, 'description', None)),
                    'published': getattr(entry, 'published', None),
                    'duration': getattr(entry, 'itunes_duration', None),
                    'episode': getattr(entry, 'itunes_episode', None),
                    'season': getattr(entry, 'itunes_season', None),
                    'audio_url': audio_url,
                    'image_url': episode_image_url,
                    'guid': guid,
                }
                files.write_json(metadata, json_path)
                print(f"Metadata saved: {entry.title}")

            # Save episode artwork
            art_path = stem + '.jpg'
            if not os.path.exists(art_path):
                episode_image_url = None
                if hasattr(entry, 'image') and hasattr(entry.image, 'href'):
                    episode_image_url = entry.image.href
                if not episode_image_url:
                    for link in getattr(entry, 'links', []):
                        if link.get('type', '').startswith('image/'):
                            episode_image_url = link.get('href')
                            break
                if episode_image_url:
                    try:
                        files.write_bytes(remote.get_file(episode_image_url), art_path)
                        print(f"Artwork saved: {entry.title}")
                    except Exception as e:
                        print(f"Failed to download artwork for {entry.title}: {e}")

    return any_downloaded
