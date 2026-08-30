import os
import requests

TIMEOUT = 30
USER_AGENT = "Podderton/1.0 (+https://github.com/awfulwoman/podderton)"


def get_file(url):
    """Fetch a URL and return its body as bytes."""

    response = requests.get(url, timeout=TIMEOUT, headers={"User-Agent": USER_AGENT})
    if response.status_code == 200:
        return response.content
    else:
        raise Exception(f"Failed to fetch {url}: {response.status_code}")


def download(url, dest_path):
    """Stream a URL to dest_path atomically via a .part file."""

    tmp = dest_path + ".part"
    with requests.get(url, timeout=TIMEOUT, stream=True,
                      headers={"User-Agent": USER_AGENT}) as response:
        if response.status_code != 200:
            raise Exception(f"Failed to fetch {url}: {response.status_code}")
        with open(tmp, "wb") as f:
            for chunk in response.iter_content(chunk_size=65536):
                if chunk:
                    f.write(chunk)
    os.replace(tmp, dest_path)
