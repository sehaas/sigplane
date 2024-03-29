import datetime
import gzip
import json
import logging
import re
import threading
import time
import urllib.request

from signald import Signal

from .Config import Config
from .PlaneList import PlaneList


class SigplaneDaemon:
    DOMAIN = "https://globe.adsbexchange.com/"

    def __init__(self, config="config.yml"):
        self._config = Config.load(filename=config)
        self._subscriptions = PlaneList.load(self._config.planelist)

        self._signal_client = Signal(
            self._config.username, socket_path=self._config.socket
        )

        self._signald_thread = threading.Thread(
            target=self._message_thread, daemon=True
        )
        self._planes_thread = threading.Thread(
            target=self._airplanes_thread, daemon=True
        )

    def start(self):
        self._signald_thread.start()
        self._planes_thread.start()

    def save(self):
        self._subscriptions.save(self._config.planelist)

    def _airplanes_thread(self):
        url = self._config.api_url
        logging.info("Fetch airplanes from %s", url)
        while True:
            try:
                request = urllib.request.Request(url)
                request.add_header("api-auth", self._config.api_key)
                request.add_header("Accept-Encoding", "gzip")
                response = urllib.request.urlopen(request)
                data = response.read()
                if response.info().get("Content-Encoding") == "gzip":
                    data = gzip.decompress(data)
                data = json.loads(data)

                logging.info("%s available planes", data.get("total"))
                for ac in data.get("ac"):
                    subscribers, groups, plane = self._subscriptions.check_icao(
                        ac.get("icao")
                    )
                    if plane is not None:
                        self._handle_plane(ac, subscribers, groups, plane)
                self._subscriptions.save(self._config.planelist)
            except Exception as e:
                logging.error("Error fetching airplanes: %s" % e)
            time.sleep(self._config.poll_interval)

    def _handle_plane(self, ac, subscribers, groups, plane):
        icao = plane.icao
        last_seen = datetime.datetime.fromtimestamp(float(ac.get("postime")) / 1000.0)
        plane.last_position = (float(ac.get("lat")), float(ac.get("lon")))
        plane.reg = ac.get("reg")
        plane.call = ac.get("call")
        if (
            plane.last_seen is None
            or (last_seen - plane.last_seen) > self._config.plane_idle
        ):
            text = "Found plane %s (%s) at %s, %s\n%s?icao=%s&showTrace=%s" % (
                plane.call,
                plane.reg,
                ac.get("lat"),
                ac.get("lon"),
                self.DOMAIN,
                icao,
                last_seen.strftime("%Y-%m-%d"),
            )
            for n in subscribers:
                try:
                    self._signal_client.send(
                        recipient=n,
                        text=text,
                        block=True,
                    )
                except Exception as e:
                    logging.error("Error while sending direct message: %s", e)

            for g in groups:
                try:
                    self._signal_client.send(
                        recipient_group_id=g,
                        text=text,
                        block=True,
                    )
                except Exception as e:
                    logging.error("Error while sending group message: %s", e)

            logging.info(
                "Plane found: %s (%s / %s). Notified %d subscibers and %d groups",
                plane.call,
                plane.reg,
                icao,
                len(subscribers),
                len(groups),
            )
        else:
            logging.info(
                "Plane still available: %s (%s / %s). Skipping notifications.",
                plane.call,
                plane.reg,
                icao,
            )
        plane.last_seen = last_seen

    def _message_thread(self):
        @self._signal_client.chat_handler(
            re.compile(
                "((?:un)?(?:block|subscribe))\\s+([0-9A-F]{6}|[0-9A-F]{1,5}(?=\\*))",
                re.I,
            ),
            order=10,
        )
        def _message_common_handler(message, match):
            command = match.group(1).lower()
            icao = match.group(2).upper()
            wildcard = "*" if len(icao) < 6 else ""
            number = message.source.get("number")
            group_id = message.group_v2.get("id")
            getattr(self._subscriptions, command)(icao, number, group_id)
            msg = "%sd ICAO %s%s for %s (%s)" % (
                command,
                icao,
                wildcard,
                number,
                group_id,
            )
            logging.info(msg)
            return True, None, "👍"

        @self._signal_client.chat_handler("status")
        def _message_status_handler(message, match):
            number = message.source.get("number")
            group_id = message.group_v2.get("id")
            logging.info("Querying status for %s (%s)", number, group_id)
            subscribed, blocked = self._subscriptions.fetch_status(number, group_id)
            result = "Subscribed:\n  "
            if len(subscribed) > 0:
                result += "\n  ".join(subscribed)
            else:
                result += "  -"
            result += "\nBlocked:\n  "
            if len(blocked) > 0:
                result += "\n  ".join(blocked)
            else:
                result += "  -"
            return result

        @self._signal_client.chat_handler("")
        def _message_catch_all(message, match):
            # This will only be sent if nothing else matches, because matching
            # stops by default on the first function that matches.
            logging.info(
                "Received message from %s: %s",
                message.source.get("number"),
                message.text,
            )
            return (
                "possible commands:\n"
                "\tsubscribe <icao>\n"
                "\tunsubscribe <icao>\n"
                "\tblock <icao>\n"
                "\tunblock <icao>\n"
                "\tstatus"
            )

        while True:
            try:
                self._signal_client.run_chat()
            except Exception as e:
                logging.error("Error connecting to singald: %s" % e)
            time.sleep(self._config.poll_interval)
