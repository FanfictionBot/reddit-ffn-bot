import time
from urllib.error import HTTPError

import google

from ffn_bot.searchengines.base import SearchEngine, register
from ffn_bot.searchengines.helpers import TagUsing, Throttled, BanHandling
from ffn_bot.searchengines.helpers import Randomizing

@register
class GoogleScraper(TagUsing, BanHandling, Throttled, Randomizing, SearchEngine):

    # We're trying 3 hours ban time
    BAN_TIME = 3*Throttled.HOUR

    def __init__(self):
        super(GoogleScraper, self).__init__(
            requests=3, timeframe=Throttled.MINUTE
        )
    def _search(self, query, site=None, limit=1):
        try:
            search = google.search("".join(query), num=limit, stop=limit)
            return list(search)
        except HTTPError as e:
            # We don't expect this error.
            # Throw it.
            if e.code != 503:
                raise

            # Notify the mixin of the ban.
            self.was_banned()

            # Return None on HTTP 503 as we expect that we are
            # banned from using google.
            return None
