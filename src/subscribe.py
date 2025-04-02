import config
import utils
import files
import os
import feedparser
import requests
import pprint

def subscriptions(configuration):
    """Get the subscriptions from the configuration."""
    # Extract the subscriptions from the configuration
    return configuration.get("subscribe", {}).get("feeds", [])

def simplify_metadata(meta):
    """Ensure the feed metadata exists."""

    pprint.pprint(meta)    

    if 'title' not in meta or not meta.title:
        raise Exception(f"No valid title exists.")       
    if 'summary' not in meta or not meta.summary:
        raise Exception(f"No valid summary exists.")

    data = {
        "title": meta.title,
        "summary": meta.summary,
        "url": feed['url']
    }
    
    # file_name = os.path.join(
    #     utils.return_configuration_basepath(configuration),
    #     feed['id'],
    #     # feed['id'] + ".json"
    #     "description.json"
    # )

    # with open(file_name, 'w', encoding='utf-8') as f:
    #     json.dump(data, f, ensure_ascii=False, indent=4)

    return data


def meta(feed_url):
    """Fetch the feed metadata from the given feed URL."""
    
    response = requests.get(feed_url)
    if response.status_code == 200:
        return feedparser.parse(response.content).feed
    else:
        raise Exception(f"Failed to fetch {feed_url}: {response.status_code}")
    
def entries(feed_url):
    """Fetch the feed entries from the given feed URL."""
    
    response = requests.get(feed_url)
    if response.status_code == 200:
        return feedparser.parse(response.content).entries
    else:
        raise Exception(f"Failed to fetch {feed_url}: {response.status_code}")


def main(config_file):
    cfg = config.file(config_file)
    feeds = subscriptions(cfg)
    
    if files.write_dir(config.basepath(cfg)):
        print("Base directory prepared.")
        
    
    for feed in feeds:
        feed_dir = os.path.join(config.basepath(cfg), feed.get("id"))
        if files.write_dir(feed_dir):
            print(f"Directory for {feed.get('name')} prepared.")

        feed_json = meta(feed.get("url"))
        if files.write_json(feed_json, os.path.join(config.basepath(cfg), feed.get("id"), "original.json")):
            print(f"Original metadata for {feed.get('name')} written.")
        
        
            

        # Write the feed metadata to a JSON file
            # Title
            # Description
        
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




