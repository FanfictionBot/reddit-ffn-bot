import json
from collections import Counter


class FicCounter(Counter):
    """
    A very basic stat counter.
    Maybe we could expand a bit more on it. But until then, I think this
    is all we need for now.
    """

    def __init__(self, filename, autosave_interval=100):
        super(FicCounter, self).__init__(self._load(self.filename))
        self.filename = filename
        self.interval = autosave_interval
        self.count = 0

    @staticmethod
    def _load(filename):
        yield from json.load(open(filename, "r"))

    def save(self):
        json.dump(self.items(), open(filename, "w"))

    def count(self, story):
        self[story.get_url()] += 1
        self._autosave()

    def _autosave(self):
        if self.interval > 0:
            self.count = (self.count + 1)%self.interval
            if self.count == 0:
                self.save()
