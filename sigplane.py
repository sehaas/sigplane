import datetime
import gzip
import json
import logging
import re
import signal
import sys
import threading
import time
import urllib.request

from signald import Signal

from sigplane.Config import Config
from sigplane.PlaneList import PlaneList


class SigplaneDaemon:
    DOMAIN = "https://globe.adsbexchange.com/"

    def __init__(self, config="config.yml"):
        self._config = Config.load(filename=config)
        self._subscriptions = PlaneList.load(self._config.planelist)

        self._signal_client = Signal(
            self._config.username, socket_path=("10.41.0.102", 15432)
        )

        threading.Thread(target=self.message_thread, daemon=True).start()
        threading.Thread(target=self.airplanes_thread, daemon=True).start()

        def ctrl_c_handler(sig, frame):
            self._subscriptions.save(self._config.planelist)
            print("You pressed Ctrl+C!")
            sys.exit(0)

        signal.signal(signal.SIGINT, ctrl_c_handler)
        signal.pause()

    def airplanes_thread(self):
        url = self._config.api_url
        logging.info("Fetch airplanes from %s", url)
        while True:
            request = urllib.request.Request(url)
            request.add_header("api-auth", self._config.api_key)
            request.add_header("Accept-Encoding", "gzip")
            response = urllib.request.urlopen(request)
            data = response.read()
            if response.info().get("Content-Encoding") == "gzip":
                data = gzip.decompress(data)
            data = json.loads(data)

            logging.info("%d available planes", data.get("total"))
            for ac in data.get("ac"):
                icao = ac.get("icao")
                subscribers, plane = self._subscriptions.check_icao(icao)
                if plane is not None:
                    last_seen = datetime.datetime.fromtimestamp(
                        float(ac.get("postime")) / 1000.0
                    )
                    plane.last_position = (float(ac.get("lat")), float(ac.get("lon")))
                    plane.reg = ac.get("reg")
                    plane.call = ac.get("call")
                    if (
                        plane.last_seen is None
                        or (last_seen - plane.last_seen) > self._config.plane_idle
                    ):
                        for n in subscribers:
                            self._signal_client.send_message(
                                n,
                                "Found plane %s (%s) at %s, %s\n%s?icao=%s"
                                % (
                                    plane.call,
                                    plane.reg,
                                    ac.get("lat"),
                                    ac.get("lon"),
                                    self.DOMAIN,
                                    icao,
                                ),
                                False,
                            )
                        logging.info(
                            "Plane found: %s (%s / %s). Notified %d subscibers",
                            plane.call,
                            plane.reg,
                            icao,
                            len(subscribers),
                        )
                    else:
                        logging.info(
                            "Plane still available: %s (%s / %s). Skipping notifications.",
                            plane.call,
                            plane.reg,
                            icao,
                        )
                    plane.last_seen = last_seen
            self._subscriptions.save(self._config.planelist)
            time.sleep(self._config.poll_interval)

    def message_thread(self):
        ICAO_PATTERN = "([0-9A-F]{6}|[0-9A-F]{1,5}(?=\\*))"

        @self._signal_client.chat_handler(
            re.compile("unsubscribe %s" % ICAO_PATTERN, re.I), order=10
        )
        def unsubscribe(message, match):
            # This will only be sent if nothing else matches, because matching
            # stops by default on the first function that matches.
            icao = match.group(1).upper()
            wildcard = "*" if len(icao) < 6 else ""
            number = message.source.get("number")
            self._subscriptions.unsubscribe(icao, number)
            logging.info("Unsubscribed %s from %s%s", number, icao, wildcard)
            return "unsubscribed from %s%s" % (icao, wildcard)

        @self._signal_client.chat_handler(
            re.compile("subscribe %s" % ICAO_PATTERN, re.I), order=11
        )
        def subscribe(message, match):
            # This will only be sent if nothing else matches, because matching
            # stops by default on the first function that matches.
            icao = match.group(1).upper()
            wildcard = "*" if len(icao) < 6 else ""
            number = message.source.get("number")
            self._subscriptions.subscribe(icao, number)
            logging.info("Subscribed %s to %s%s", number, icao, wildcard)
            return "subscribed to %s%s" % (icao, wildcard)

        @self._signal_client.chat_handler("")
        def catch_all(message, match):
            # This will only be sent if nothing else matches, because matching
            # stops by default on the first function that matches.
            logging.info(
                "Received message from %s: %s",
                message.source.get("number"),
                message.text,
            )
            return "usage: \n\t<subscribe|unsubscribe> <icao>"

        logging.info("Message Thread")
        self._signal_client.run_chat()


if __name__ == "__main__":
    format = "%(asctime)s: %(message)s"
    logging.basicConfig(format=format, level=logging.INFO, datefmt="%H:%M:%S")
    SigplaneDaemon(config="config.yml")
