import threading

import yaml

from sigplane.Plane import Plane
from sigplane.Subscription import Subscription


class PlaneList:
    def __init__(self):
        self._lock = threading.RLock()
        self._planes = {}
        self._subscriptions = {}
        self._blocklist = {}

    def __getstate__(self):
        state = self.__dict__.copy()
        del state["_lock"]
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)
        self._lock = threading.RLock()

    @classmethod
    def load(cls, filename):
        try:
            with open(filename, "r") as f:
                return yaml.load(f, Loader=yaml.Loader) or PlaneList()
        except FileNotFoundError:
            return PlaneList()

    def save(self, filename):
        with self._lock:
            with open(filename, "w") as f:
                yaml.dump(self, f)

    @property
    def pattern(self):
        return tuple(self._subscriptions.keys())

    def get_plane(self, icao):
        with self._lock:
            return self._planes.setdefault(icao, Plane(icao))

    def subscribe(self, icao, number):
        with self._lock:
            self._subscriptions.setdefault(icao, Subscription(icao)).add_subscriber(
                number
            )
            self.unblock(icao, number)  # overrule previous block

    def unsubscribe(self, icao, number):
        with self._lock:
            if icao in self._subscriptions:
                if self._subscriptions.get(icao).del_subscriber(number) == 0:
                    self._subscriptions.pop(icao)

    def block(self, icao, number):
        with self._lock:
            self._blocklist.setdefault(icao, Subscription(icao)).add_subscriber(number)
            self.unsubscribe(icao, number)  # overrule previous subscription

    def unblock(self, icao, number):
        with self._lock:
            if icao in self._blocklist:
                if self._blocklist.get(icao).del_subscriber(number) == 0:
                    self._blocklist.pop(icao)

    def check_icao(self, icao):
        with self._lock:
            numbers = set()
            for sub in self._subscriptions.values():
                if icao.startswith(sub.pattern):
                    numbers.update(sub.subscribers)

            for block in self._blocklist.values():
                if icao.startswith(block.pattern):
                    numbers.difference_update(block.subscribers)

            if len(numbers) == 0:
                if icao in self._planes:
                    self._planes.pop(icao)
                return (None, None)

            plane = self._planes.setdefault(icao, Plane(icao))
            return (numbers, plane)
