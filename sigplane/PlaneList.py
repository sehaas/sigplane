import logging
import threading

import yaml

from sigplane.Plane import Plane
from sigplane.Subscription import Subscription


def constructor(loader, node):
    fields = loader.construct_mapping(node)
    return PlaneList(**fields)


yaml.add_constructor("!!python/object:sigplane.PlaneList.PlaneList", constructor)


class PlaneList:
    def __init__(self):
        self._lock = threading.Lock()
        self._planes = {}
        self._subscriptions = {}

    def __getstate__(self):
        state = self.__dict__.copy()
        del state["_lock"]
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)
        self._lock = threading.Lock()

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

    # def init_locking(self):
    #     self._lock = threading.Lock()

    # @property
    # def planes(self):
    #     return tuple(self._planes.values())

    @property
    def pattern(self):
        return tuple(self._subscriptions.keys())

    def get_plane(self, icao):
        with self._lock:
            return self._planes.setdefault(icao, Plane(icao))

    def subscribe(self, icao, number):
        with self._lock:
            try:
                self._subscriptions.setdefault(icao, Subscription(icao)).add_subscriber(
                    number
                )
            except Exception as e:
                logging.error(e)

    def unsubscribe(self, icao, number):
        with self._lock:
            if icao in self._planes:
                self._subscriptions.get(icao).del_subscriber(number)

    def check_icao(self, icao):
        with self._lock:
            numbers = set()
            for sub in self._subscriptions.values():
                if icao.startswith(sub.pattern):
                    numbers.update(sub.subscribers)
            if len(numbers) == 0:
                if icao in self._planes:
                    self._planes.pop(icao)
                return (None, None)

            plane = self._planes.setdefault(icao, Plane(icao))
            return (numbers, plane)
