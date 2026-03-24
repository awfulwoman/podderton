import sys
import time
import os
from datetime import datetime, timezone

import config
import subscribe


def main(config_file):
    cfg = config.file(config_file)
    interval = config.subscribe_interval(cfg)
    print(f"Subscriber heartbeat: every {interval}s")

    while True:
        ts = datetime.now(timezone.utc).isoformat()
        print(f"[{ts}] Checking for new episodes...")
        got_new = subscribe.main(config_file)

        if got_new:
            subs_path = config.subscriptions_path(cfg)
            signal_path = os.path.join(subs_path, ".updated")
            with open(signal_path, "w") as f:
                f.write(datetime.now(timezone.utc).isoformat())

        time.sleep(interval)
