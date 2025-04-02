import pprint
import config
import subscribe

def main():
    print("Welcome to Podderton!")
    working = config.read_yaml("/Users/charlie/Code/podderton/config.yaml")
    print("Config: ", working['input']['feeds'])


    # rss = get_feed_from_url("https://podcast.global.com/show/5234547/episodes/feed")
    feed = subscribe.get_feed_entries(working['input']['feeds'][0]['url'])

    pprint.pprint(feed[0])


    # for item in rss.entries:
    #     pprint.pprint(item)
    #     print(extract_image_url(item))
    #     if extract_image_url(item):
    #         # Download the image if it exists
    #         print(f"Downloading image from {extract_image_url(item)}")
    #         download_asset(extract_image_url(item), "assets/")
    #         # Uncomment the following line to actually download the images
        

if __name__ == "__main__":
    main()