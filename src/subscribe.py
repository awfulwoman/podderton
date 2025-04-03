import config
import files
import os
import feedparser
import requests
import pprint
import validators
import remote

def subscriptions(configuration):
    """Get the subscriptions from the configuration."""
    # Extract the subscriptions from the configuration
    return configuration.get("subscribe", {}).get("feeds", [])

def simplify_metadata(remote_feed, configured_feed):
    """Ensure the feed metadata exists."""

    if 'title' not in remote_feed or not remote_feed.title:
        raise Exception(f"No valid title exists.")       
    if 'summary' not in remote_feed or not remote_feed.summary:
        raise Exception(f"No valid summary exists.")

    data = {
        "title": remote_feed.title,
        "summary": remote_feed.summary,
        "url": configured_feed['url']
    }

    return data


def get_meta(feed_url):
    """Fetch the feed metadata from the given feed URL."""
    
    response = requests.get(feed_url)
    if response.status_code == 200:
        return feedparser.parse(response.content).feed
    else:
        raise Exception(f"Failed to fetch {feed_url}: {response.status_code}")
    
def get_entries(feed_url):
    """Fetch the feed entries from the given feed URL."""
    
    response = requests.get(feed_url)
    if response.status_code == 200:
        return feedparser.parse(response.content).entries
    else:
        raise Exception(f"Failed to fetch {feed_url}: {response.status_code}")
    
def get_feed_image_url(meta):
    """Fetch the image from the given feed URL."""

    # Determine what represents the feed image

    if validators.url(meta.image):
        return validators.url

    if validators.url(meta.image.href):
        return meta.image.href
    
    return None


def main(config_file):
    cfg = config.file(config_file)
    configured_feeds = subscriptions(cfg)
    
    if files.write_dir(config.basepath(cfg)):
        print("Base directory prepared.")
        
    
    for configured_feed in configured_feeds:
        feed_meta = get_meta(configured_feed.get("url"))
        feed_dir = os.path.join(config.basepath(cfg), configured_feed.get("id"))
        
        if files.write_dir(feed_dir):
            print(f"Directory for {configured_feed.get('name')} prepared.")

        if files.write_json(feed_meta, os.path.join(config.basepath(cfg), configured_feed.get("id"), "original.json")):
            print(f"Original metadata for {configured_feed.get('name')} written.")
        
        simplified_meta = simplify_metadata(feed_meta, configured_feed)
        if files.write_json(simplified_meta, os.path.join(config.basepath(cfg), configured_feed.get("id"), "feed.json")):
            print(f"Simplified metadata for {configured_feed.get('name')} written.")            

        feed_image_path = os.path.join(config.basepath(cfg), configured_feed.get("id"), "feed.jpg")
        if not os.path.exists(feed_image_path):
            feed_image_url = get_feed_image_url(feed_meta)
            if feed_image_url:
                if files.write_image(remote.get_file(feed_image_url), feed_image_path):
                    print(f"Artwork for {configured_feed.get('name')} written.")   


        # Download the feed's assets (images, description, etc.)

        # entries = return_feed_entries(feed['url'])

        # for entry in entries:
        #     print(entry.title)
        #     files.create_directory(entry['id'])
        #     # ensure_entry_metadata_exists(entry)

            
            # Look up the entry's file_format
            # replace the string tokens in the file_format
            # create the directory for the entry using file_format
            # download the entry's audio asset
            # download the entry's description to json
            # download the entry's image asset
