import time
from urllib.error import HTTPError
from urllib.parse import urlencode, urlparse, parse_qs

from lxml.html import fromstring

from ffn_bot.searchengines.base import SearchEngine, register
from ffn_bot.searchengines.helpers import TagUsing, Throttled, BanHandling
from ffn_bot.searchengines.helpers import Randomizing

@register
class GoogleScraper(TagUsing, BanHandling, Throttled, Randomizing, SearchEngine):

    # We're trying 3 hours ban time
    BAN_TIME = 3*Throttled.HOUR

    def __init__(self):
        super(GoogleScraper, self).__init__(
            requests=1, timeframe=Throttled.MINUTE
        )

    def _get_page(self, request):
        from ffn_bot import cache
        return fromstring(cache.default_cache.get_page(request))

    def _parse_url(self, url):
        if not url.startswith("/url?"):
            return url
        res = parse_qs(urlparse(url).query)['q']
        return self._parse_url(res[0])

    def _execute(self, query):
        self.pg = pg = self._get_page("https://google.com/search?" + urlencode({'q':query}))
        return [
            self._parse_url(result.get("href"))
            for result in pg.cssselect(".r a, p a")
        ]

    def _search(self, query, site=None, limit=1):
        try:
            return self._execute(query)[:limit]
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
