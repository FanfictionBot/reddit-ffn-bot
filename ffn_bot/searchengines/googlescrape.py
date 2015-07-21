import time
from urllib.error import HTTPError

import google

from ffn_bot.searchengines.base import SearchEngine, register
from ffn_bot.searchengines.helpers import TagUsing, Throttled


@register
class GoogleScraper(TagUsing, Throttled, SearchEngine):

    # We're trying 3 hours ban time
    BAN_TIME = 3*Throttled.HOUR

    def __init__(self):
        super(GoogleScraper, self).__init__(
            requests=6, timeframe=Throttled.MINUTE
        )
        self.banned = 0

    @property
    def _ban_timedelta(self):
        return time.time() - self.banned


    @property
    def is_serving_rate_limit(self):
        if self.banned:
            return self._ban_timedelta < self.BAN_TIME
        return super(GoogleScraper, self).is_serving_rate_limit

    @property
    def current_wait_time(self):
        pre_result = super(GoogleScraper, self).current_wait_time
        if self.banned:
            return max(self.BAN_TIME - self._ban_timedelta, pre_result)
        return pre_result

    @property
    def working(self):
        if not self.banned:
            return True
        return self._ban_timedelta > self.BAN_TIME

    def _search(self, query, site=None, limit=1):
        # Handle the ban.
        if self.banned:
            # Check if we assume that we are still banned.
            if self._ban_timedelta < self.BAN_TIME:
                # Consider ourselves deactivated.
                return None

            # If we don't assume it anymore, we set it to 0
            # and continue the query.
            self.banned = 0

        try:
            search = google.search("".join(query), num=limit, stop=limit)
            return list(search)
        except HTTPError as e:
            # We don't expect this error.
            # Throw it.
            if e.code != 503:
                raise

            # Declare ourselves banned from google for a day.
            self.banned = time.time()

            # Return None on HTTP 503 as we expect that we are
            # banned from using google.
            return None
