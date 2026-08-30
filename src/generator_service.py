import os
import threading
import time
from datetime import datetime, timezone

import config
import publish
import server


def _mtime(path):
    """Return the mtime of path, or None if it does not exist."""
    try:
        return os.path.getmtime(path)
    except OSError:
        return None


def main(config_file):
    cfg = config.file(config_file)
    interval = config.generate_interval(cfg)
    subs_path = config.subscriptions_path(cfg)
    signal_path = os.path.join(subs_path, ".updated")

    print(f"Generator heartbeat: every {interval}s")

    # Generate feeds once on startup
    publish.main(config_file)
    last_seen = _mtime(signal_path)

    # Start HTTP server in a daemon thread
    t = threading.Thread(target=server.main, args=(config_file,), daemon=True)
    t.start()
    print(f"Server running on http://0.0.0.0:9988")

    while True:
        time.sleep(interval)
        current = _mtime(signal_path)
        if current is not None and current != last_seen:
            last_seen = current
            publish.main(config_file)
            ts = datetime.now(timezone.utc).isoformat()
            print(f"[{ts}] Feeds regenerated (signal updated at {current})")
