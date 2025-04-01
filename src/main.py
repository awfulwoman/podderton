import os
import feedparser
from requests import get  # noqa
import pprint
from urllib.parse import urljoin, urlparse

def config():
    """Configuration function to set up global variables."""
    # Set up any configuration variables here
    # For example, you might want to set up logging or other settings
    pass
    # config()

def get_feed_from_url(url):
    """Fetch the RSS feed from the given URL."""
    # Make a request to the URL and parse the RSS feed
    response = get(url)
    if response.status_code == 200:
        return feedparser.parse(response.content)
    else:
        raise Exception(f"Failed to fetch RSS feed: {response.status_code}")
    
def extract_image_url(entry):
    """Extract the image URL from the RSS entry."""
    # Check if the entry has an image attribute
    if hasattr(entry, "image"):
        # If the image attribute is a URL, return it
        if isinstance(entry.image, str):
            return entry.image
        # If the image attribute is an object, return its href attribute
        elif hasattr(entry.image, "href"):
            return entry.image.href
    return None

def download_asset(url, location):
    """Download an asset from the given URL."""
    # Make a request to the URL and save the content to a file
    
    response = get(url)
    if response.status_code == 200:
        filename = url.split("/")[-1]
        path = location + urljoin(filename, urlparse(filename).path)
        # Ensure the directory exists
        os.makedirs(location, exist_ok=True)
        # Write the content to a file
        with open(path, "wb") as file:
            file.write(response.content)
        print(f"Downloaded {filename}")
    else:
        print(f"Failed to download {url}: {response.status_code}")

def main():
    print("Welcome to Podderton!")
    # rss = get_feed_from_url("https://podcast.global.com/show/5234547/episodes/feed")
    rss = get_feed_from_url("https://feeds.simplecast.com/4NOSW3hj")

    print("Feed type: ", rss.version)

    for item in rss.entries:
        # print(item.keys())
        print(extract_image_url(item))
        if extract_image_url(item):
            # Download the image if it exists
            print(f"Downloading image from {extract_image_url(item)}")
            download_asset(extract_image_url(item), "assets/")
            # Uncomment the following line to actually download the images
        

if __name__ == "__main__":
    main()