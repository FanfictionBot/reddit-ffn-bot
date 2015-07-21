class SearchEngine(object):
    """
    This class abstracts the search engine away,
    so you can have mutliple search engines searching for
    you raising the overall rate-limit for requests.
    """

    def search(self, query, site=None, limit=1):
        """
        Search the web.

        :param query:   The search query.
        :param site: Limit the search to the following site.
        """
        pass

    @property
    def is_serving_rate_limit(self):
        """Checks if we currently save rate limits."""
        return False

    @property
    def current_wait_time(self):
        """Returns the current expected wait time."""
        return 0

    @property
    def working(self):
        """Returns if the bot is currently working."""
        return True

SEARCH_ENGINES = []


def register(cls):
    SEARCH_ENGINES.append(cls)
    return cls


class _Searcher(object):
    def __init__(self):
        self.engines = [engine() for engine in SEARCH_ENGINES]

    @property
    def _engine_order(self):
        engines = filter(lambda engine: engine.working, self.engines[:])
        engines = sorted(engines, key=lambda e: e.current_wait_time)
        return engines

    def search(self, query, site=None, limit=1):
        engines = self._engine_order
        for engine in engines:
            res = engine.search(query, site, limit)
            if res:
                return res
        return None
