import datetime
import logging

import yaml


class Config:
    def __init__(
        self,
        username=None,
        api_key=None,
        api_url="https://adsbexchange.com/api/aircraft/json/lat/47.75/lon/14.75/dist/120",
        plane_idle=10,
        poll_interval=1,
        planelist="planelist.yml",
        socket="/signald/signald.sock",
        **kwargs
    ):
        self._username = username
        self._api_key = api_key
        self._api_url = api_url
        self._plane_idle = datetime.timedelta(minutes=plane_idle)
        self._poll_interval = datetime.timedelta(minutes=poll_interval).seconds
        self._planelist = planelist
        if isinstance(socket, list):
            self._socket = tuple(socket)
        else:
            self._socket = socket

    @property
    def username(self):
        return self._username

    @property
    def api_key(self):
        return self._api_key

    @property
    def api_url(self):
        return self._api_url

    @property
    def plane_idle(self):
        return self._plane_idle

    @property
    def poll_interval(self):
        return self._poll_interval

    @property
    def planelist(self):
        return self._planelist

    @property
    def socket(self):
        return self._socket

    @classmethod
    def load(cls, filename="config.yml"):
        cfg = {}
        try:
            with open(filename, "r") as stream:
                cfg = yaml.load(stream, Loader=yaml.SafeLoader)
        except FileNotFoundError:
            logging.warn("could not read config file '%s'", filename)
            pass
        return cls(**cfg)
