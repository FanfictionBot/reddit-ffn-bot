import re
from urllib.parse import urlencode, unquote
from lxml.html import fromstring

from ffn_bot.searchengines.base import register, SearchEngine
from ffn_bot.searchengines.helpers import Throttled, Randomizing
from ffn_bot.searchengines.helpers import TagUsing


LINK_FINDER = re.compile("(?<=RU=).*?(?=/R.=)")


@register
class YahooScraper(TagUsing, Throttled, Randomizing, SearchEngine):
    def __init__(self):
        super(YahooScraper, self).__init__(
            requests=6,
            timeframe=self.MINUTE
        )

    def _get_page(self, request):
        from ffn_bot import cache
        return fromstring(cache.default_cache.get_page(request))

    def _search(self, query, site=None, limit=1):
        page = self._get_page("http://search.yahoo.com/search?" + urlencode({
            "p": query
        }))

        return list(
            LINK_FINDER.findall(unquote(tag.get("href")))[0]
            for tag in page.cssselect("#web h3 a")
        )[:limit]
