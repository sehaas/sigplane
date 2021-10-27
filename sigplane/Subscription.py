class Subscription:
    def __init__(self, pattern):
        self._pattern = pattern
        self._subscribers = []
        self._groups = []

    def __setstate__(self, state):
        self.__dict__.update(state)
        # fallback for already persisted Subscription
        self._groups = getattr(self, "_groups", [])

    @property
    def pattern(self):
        return self._pattern

    @property
    def subscribers(self):
        return tuple(self._subscribers)

    @property
    def groups(self):
        return tuple(self._groups)

    def add_subscriber(self, number, group):
        if group is not None:
            if group not in self._groups:
                self._groups.append(group)
        else:
            if number not in self._subscribers:
                self._subscribers.append(number)

    def del_subscriber(self, number, group):
        try:
            if group is not None:
                self._groups.remove(number)
            else:
                self._subscribers.remove(number)
        except ValueError:
            pass  # do nothing!
        return len(self._subscribers) + len(self._groups)

    def contains(self, number, group):
        return (
            group in self._groups if group is not None else number in self._subscribers
        )
