from requests import get
import feedparser


def get_feed_meta(feed_url):
    """Fetch the RSS feed metadata from the given URL."""
    # Make a request to the URL and parse the RSS feed
    response = get(feed_url)
    if response.status_code == 200:
        return feedparser.parse(response.content).feed
    else:
        raise Exception(f"Failed to fetch {feed_url}: {response.status_code}")
    
def get_feed_entries(feed_url):
    """Fetch the RSS feed entries from the given URL."""
    # Make a request to the URL and parse the RSS feed
    response = get(feed_url)
    if response.status_code == 200:
        return feedparser.parse(response.content).entries
    else:
        raise Exception(f"Failed to fetch {feed_url}: {response.status_code}")


def download_asset(url, location):
    """Download an asset from the given URL."""
    # Make a request to the URL and save the content to a file
    
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

