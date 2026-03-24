import os
import threading
import time
from datetime import datetime, timezone

import config
import publish
import server


def main(config_file):
    cfg = config.file(config_file)
    interval = config.generate_interval(cfg)
    subs_path = config.subscriptions_path(cfg)
    signal_path = os.path.join(subs_path, ".updated")

    print(f"Generator heartbeat: every {interval}s")

    # Generate feeds once on startup
    publish.main(config_file)

    # Start HTTP server in a daemon thread
    t = threading.Thread(target=server.main, args=(config_file,), daemon=True)
    t.start()
    print(f"Server running on http://0.0.0.0:9988")

    while True:
        time.sleep(interval)
        if os.path.exists(signal_path):
            with open(signal_path) as f:
                signal_ts = f.read().strip()
            os.remove(signal_path)
            publish.main(config_file)
            ts = datetime.now(timezone.utc).isoformat()
            print(f"[{ts}] Feeds regenerated (triggered by update at {signal_ts})")
