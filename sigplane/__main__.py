__version__ = "1.0.0"

import argparse
import logging
import signal
import sys

from .sigplane import SigplaneDaemon

if __name__ == "__main__":
    format = "%(asctime)s: %(message)s"
    logging.basicConfig(format=format, level=logging.INFO, datefmt="%H:%M:%S")
    parser = argparse.ArgumentParser(
        prog=None
        if globals().get("__spec__") is None
        else "python -m {}".format(__spec__.name.partition(".")[0])
    )
    parser.add_argument(
        "-c", "--config", help="config file", required=False, default="config.yml"
    )
    args = parser.parse_args()
    daemon = SigplaneDaemon(config=args.config)
    daemon.start()

    def ctrl_c_handler(sig, frame):
        print("Ctrl+C pressed! Shutting down...")
        daemon.save()
        sys.exit(0)

    signal.signal(signal.SIGINT, ctrl_c_handler)
    signal.pause()
