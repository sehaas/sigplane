class Subscription:
    def __init__(self, pattern):
        self._pattern = pattern
        self._subscribers = []

    @property
    def pattern(self):
        return self._pattern

    @property
    def subscribers(self):
        return tuple(self._subscribers)

    @property
    def has_subscribers(self):
        return len(self._subscribers) > 0

    def add_subscriber(self, number):
        if number not in self._subscribers:
            self._subscribers.append(number)

    def del_subscriber(self, number):
        try:
            self._subscribers.remove(number)
        except ValueError:
            pass  # do nothing!
        return len(self._subscribers)

    def contains(self, number):
        return number in self._subscribers
