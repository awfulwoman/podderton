import config
import utils
from requests import get
import feedparser
import pprint
import os
import json

def get_feed_meta(feed_url):
    """Fetch the feed metadata from the given feed URL."""
    
    response = get(feed_url)
    if response.status_code == 200:
        return feedparser.parse(response.content).feed
    else:
        raise Exception(f"Failed to fetch {feed_url}: {response.status_code}")
    
def get_feed_entries(feed_url):
    """Fetch the feed entries from the given feed URL."""
    
    response = get(feed_url)
    if response.status_code == 200:
        return feedparser.parse(response.content).entries
    else:
        raise Exception(f"Failed to fetch {feed_url}: {response.status_code}")

def get_image_url_from_feed_entry(entry):
    """Extract the image URL from the feed entry."""
    # Check if the entry has an image attribute
    if hasattr(entry, "image"):
        # If the image attribute is a URL, return it
        if isinstance(entry.image, str):
            return entry.image
        # If the image attribute is an object, return its href attribute
        elif hasattr(entry.image, "href"):
            return entry.image.href
    return None

def get_file_from_url(url, location):
    """Download an asset from the given URL and store it in the specified location."""
       
    response = get(url)
    if response.status_code == 200:
        filename = url.split("/")[-1]
        filename = urljoin(filename, urlparse(filename).path)
        path = location + filename
        # Ensure the directory exists
        os.makedirs(location, exist_ok=True)
        # Write the content to a file
        with open(path, "wb") as file:
            file.write(response.content)
        print(f"Downloaded {filename}")
    else:
        print(f"Failed to download {url}: {response.status_code}")


def ensure_filesystem_is_prepared(configuration):
    """Prepare the filesystem for storing downloaded assets."""

    print("Preparing filesystem...")
    pprint.pprint(configuration)

    if 'subscribe' not in configuration or not configuration['subscribe']:
        raise Exception("No 'subscribe' section defined in the configuration.")
    if 'path' not in configuration['subscribe'] or not configuration['subscribe']['path']:
        raise Exception("No valid path defined for storing downloaded assets.")
    
    base_path = configuration['subscribe']['path']
    base_path = os.path.expanduser(base_path)
    os.makedirs(base_path, exist_ok=True)
    pprint.pprint(base_path)

def ensure_feed_is_prepared(feed, configuration):
    """Prepare for the feed."""
    
    if 'name' not in feed or not feed['name']:
        raise Exception("No valid name defined for the feed.")
    if 'url' not in feed or not feed['url']:
        raise Exception(f"No valid URL defined for {feed['name']}.")
    if 'id' not in feed or not feed['id']:
        raise Exception(f"No valid id defined for {feed['name']}.")
    # if 'file_format' not in feed or not feed['file_format']:
    #     raise Exception("No valid file_format defined for the feed.")

    print(f"Preparing {feed["name"]} feed...")

    base_path = utils.get_basepath_from_configuration(configuration)

    os.makedirs(os.path.join(base_path, feed.get("id")), exist_ok=True)

def ensure_feed_metadata_exists(feed, configuration):
    """Ensure the feed metadata exists."""

    meta = get_feed_meta(feed['url'])
    
    # pprint.pprint(meta.title)
    # pprint.pprint(meta.description)

    print(meta.summary)

    if 'title' not in meta or not meta.title:
        raise Exception(f"No valid title exists for {feed['name']}.")       
    if 'summary' not in meta or not meta.summary:
        raise Exception(f"No valid summary exists for {feed['name']}.")
    
    data = {
        "title": meta.title,
        "summary": meta.summary,
        "url": feed['url']
    }
    
    file_name = os.path.join(
        utils.get_basepath_from_configuration(configuration),
        feed['id'],
        feed['id'] + ".json"
    )

    with open(file_name, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    



def ensure_entry_is_prepared(entry):
    """Prepare for the entry."""

def ensure_entry_metadata_exists(entry):
    """Ensure the entry metadata exists."""
def ensure_entry_audio_exists(entry):
    """Ensure the entry audio exists."""

def ensure_entry_image_exists(entry):
    """Ensure the entry image exists."""

def main(config_file):
    configuration = config.get(config_file)
    feeds = config.subscriptions(configuration)
    
    ensure_filesystem_is_prepared(configuration)
    
    # FOR EACH feed...
    # ensure_feed_is_prepared(feed)
    # Get feed metadata
    # Download the feed's assets (images, description, etc.)
    # FOR EACH entry in feed
    # ensure_entry_is_prepared
    # Look up the entry's file_format
    # replace the string tokens in the file_format
    # create the directory for the entry using file_format
    # download the entry's audio asset
    # download the entry's description to json
    # download the entry's image asset

    for feed in feeds:
        ensure_feed_is_prepared(feed, configuration)
        ensure_feed_metadata_exists(feed, configuration)

    #     meta = get_feed_meta(feed['url'])
    #     entries = get_feed_entries(feed['url'])
    #     pprint.pprint(meta)
    #     # pprint.pprint(entries)
