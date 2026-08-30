import os
import sys
import subscriber_service

if __name__ == "__main__":
    cfg = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("PODDERTON_CONFIG", "/config/feeds.yaml")
    subscriber_service.main(cfg)
