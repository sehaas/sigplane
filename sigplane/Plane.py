class Plane:
    def __init__(self, icao):
        self._icao = icao
        self._reg = None
        self._call = None
        self.last_seen = None
        self.last_position = (None, None)

    @property
    def icao(self):
        return self._icao

    @property
    def last_seen(self):
        return self._last_seen

    @last_seen.setter
    def last_seen(self, value):
        self._last_seen = value

    @property
    def reg(self):
        return self._reg

    @reg.setter
    def reg(self, value):
        self._reg = value

    @property
    def call(self):
        return self._call

    @call.setter
    def call(self, value):
        self._call = value

    @property
    def last_position(self):
        return (self._last_lat, self._last_lon)

    @last_position.setter
    def last_position(self, value):
        self._last_lat = value[0]
        self._last_lon = value[1]
