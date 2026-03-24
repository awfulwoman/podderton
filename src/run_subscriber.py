import sys
import subscriber_service

if __name__ == "__main__":
    subscriber_service.main(sys.argv[1] if len(sys.argv) > 1 else "/config/feeds.yaml")
