import sys
import time
from ffn_bot.searchengines.base import SearchEngine


class Throttled(SearchEngine):
    """
    Implements a simple throttle.
    """

    SECOND = 1
    MINUTE = SECOND*60
    HOUR = MINUTE*60
    DAY = HOUR*24
    MONTH = DAY*30
    YEAR = 365*DAY

    def __init__(self, requests, timeframe=60*60):
        self.wait_time = timeframe/requests
        self.last_search = 0

    def search(self, *args, **kwargs):
        timedelta = self._timedelta
        if timedelta < self.wait_time:
            time.sleep(self.wait_time - timedelta)

        try:
            super(Throttled, self).search(*args, **kwargs)
            return self._search(*args, **kwargs)
        finally:
            self.last_search = time.time()

    def _search(self, *args, **kwargs):
        pass

    @property
    def _timedelta(self):
        return time.time() - self.last_search

    @property
    def is_serving_rate_limit(self):
        return self._timedelta < self.wait_time

    @property
    def current_wait_time(self):
        return max(self.wait_time - self._timedelta, 0)


class Randomizing(SearchEngine):
    def search(self, *args, **kwargs):
        if self.working:
            import random
            time.sleep(random.randint(0, 3000)/3000.0)
        super(Randomizing, self).search(*args, **kwargs)


class TagUsing(SearchEngine):
    TAG = "site:"

    def search(self, query, site=None, limit=1):
        if site is not None:
            query+=" "+self.TAG+site
        return super(TagUsing, self).search(query, None, limit)
