"""Run the notification scheduler as its own process (instead of SCHEDULER_ENABLED in the API).

    python -m scripts.run_scheduler          # loop every SCHEDULER_INTERVAL_SECONDS
    python -m scripts.run_scheduler --once   # single tick, e.g. from cron
"""

import argparse
import signal

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.jobs.scheduler import Scheduler, run_once

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--once", action="store_true", help="run one tick and exit")
    args = parser.parse_args()
    configure_logging(get_settings().log_level)

    if args.once:
        print(run_once())
    else:
        scheduler = Scheduler()
        signal.signal(signal.SIGINT, lambda *_: scheduler.stop())
        signal.signal(signal.SIGTERM, lambda *_: scheduler.stop())
        scheduler.start()
        scheduler.join()
