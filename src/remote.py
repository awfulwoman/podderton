import requests

def get_file(url):
    """Fetch the feed metadata from the given feed URL."""
    
    response = requests.get(url)
    if response.status_code == 200:
        return response.content
    else:
        raise Exception(f"Failed to fetch {url}: {response.status_code}")