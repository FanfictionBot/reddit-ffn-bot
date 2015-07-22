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
        super(Throttled, self).__init__()
        self.wait_time = timeframe/requests
        self.last_search = 0

    def search(self, *args, **kwargs):
        timedelta = self._timedelta
        if timedelta < self.wait_time:
            time.sleep(self.wait_time - timedelta)

        try:
            return super(Throttled, self).search(*args, **kwargs)
        finally:
            self.last_search = time.time()

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
            query += " " + self.TAG + site
        return super(TagUsing, self).search(query, None, limit)


class BanHandling(SearchEngine):

    BAN_TIME = Throttled.HOUR

    def __init__(self, *args, **kwargs):
        super(BanHandling, self).__init__(*args, **kwargs)
        self.banned = 0

    @property
    def _ban_delta(self):
        return time.time() - self.banned

    @property
    def working(self):
        if self.banned:
            if self._ban_delta < self.BAN_TIME:
                return False
        return super(BanHandling, self).working

    @property
    def is_serving_rate_limit(self):
        if self.banned:
            return not self.working
        return super(BanHandling, self).is_serving_rate_limit

    @property
    def current_wait_time(self):
        s_wait_time = super(BanHandling, self).current_wait_time
        if self.banned:
            return max(self.BAN_TIME - self._ban_delta, s_wait_time)
        return s_wait_time

    def search(self, *args, **kwargs):
        if not self.working:
            return None

        self.banned = 0
        return super(BanHandling, self).search(*args, **kwargs)

    def was_banned(self):
        self.banned = time.time()
