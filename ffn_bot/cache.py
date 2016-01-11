import time
import string
import logging
import hashlib
from requests import Session
from collections import OrderedDict

from ffn_bot.searchengines import Searcher
from ffn_bot import config

CACHED_SEARCHER = Searcher()
USER_AGENT = "Lynx/2.8.8dev.3 libwww-FM/2.14 SSL-MM/1.4.1"


class LimitedSizeDict(OrderedDict):

    """The actual cache implementation."""

    def __init__(self, *args, **kwds):
        self.size_limit = kwds.pop("size_limit", None)
        OrderedDict.__init__(self, *args, **kwds)
        self._check_size_limit()

    def __setitem__(self, key, value):
        OrderedDict.__setitem__(self, key, value)
        self._check_size_limit()

    def _check_size_limit(self):
        if self.size_limit is not None:
            while len(self) > self.size_limit:
                self.popitem(last=False)


class BaseCache(object):
    CACHE_TYPES = {}

    def get(self, key):
        return 0
    def set(self, key, value, expire=0):
        pass

    @classmethod
    def register_type(cls, name):
        def _decorator(subcls):
            cls.CACHE_TYPES[name] = subcls
            return subcls
        return _decorator

    @classmethod
    def by_arguments(cls, settings):
        import argparse
        ctype = cls.CACHE_TYPES[settings["type"]]
        return ctype(settings)


@BaseCache.register_type("local")
class LocalCache(BaseCache):
    EMPTY_RESULT = []

    def __init__(self, ns):
        self.expire = ns.get("expire", 30*60)
        self.cache = LimitedSizeDict(size_limit=ns.get("size", 10000))

    def get(self, key):
        result = self.cache.get(key, self.EMPTY_RESULT)
        if result is not self.EMPTY_RESULT:
            if result[2] == 0 or time.time() - result[1] <= result[2]:
                self._push_cache(key, *result)
                return result[0]
            del self.cache[key]
        raise KeyError("Not cached")

    def set(self, key, value, expire=-1):
        if expire == -1:
            expire = self.expire
        self._push_cache(key, value, time.time(), expire)

    def _push_cache(self, key, value, insert, expire):
        self.cache[key] = (value, insert, expire*1000)


@BaseCache.register_type("memcached")
class MemcachedCache(BaseCache):
    def __init__(self, ns):
        import memcache
        self.client = memcache.Client(ns["hosts"])
        self.expire = ns["expire"]

    def get(self, key):
        key = self.enforce_ascii(key)
        result = self.client.get(key)
        if result is None:
            raise KeyError
        return result

    def set(self, key, value, expire=-1):
        key = self.enforce_ascii(key)
        if expire == -1:
            expire = self.expire
        self.client.set(key, value, time=expire)

    @staticmethod
    def enforce_ascii(stri):
        if len(stri)>250 or not stri.isalnum():
            return hashlib.sha256(stri.encode("utf-8")).hexdigest()
        return stri.encode("utf-7")


class RequestCache(object):

    """
    Cache for search requests and page-loads.
    """

    def __init__(self, args=None):
        if args is None:
            args = config.get_settings()["cache"]

        self.cache = BaseCache.by_arguments(args)
        self.logger = logging.getLogger("RequestCache")
        self.session = Session()

    def hit_cache(self, type, query):
        """Check if the value is in the cache."""
        self.logger.info("Hitting cache: " + "%s:%s" % (type, query))
        return self.cache.get("%s:%s" % (type, query))

    def push_cache(self, type, query, data):
        """Push a value into the cache."""
        self.logger.info("Inserting cache: " + "%s:%s" % (type, query))
        return self.cache.set("%s:%s"%(type,query), data)

    def get_page(self, page, throttle=0, **kwargs):
        self.logger.info("LOADING: " + str(page))
        try:
            return self.hit_cache("get", page)
        except KeyError:
            pass

        # Throtle only if we don't have a version cached.
        if throttle:
            time.sleep(throttle)

        # Set our own user-agent.
        headers = kwargs.pop("headers", {})
        if "User-Agent" not in headers:
            headers["User-Agent"] = USER_AGENT
        kwargs["headers"] = headers

        result = self.session.get(page, **kwargs).text

        self.push_cache("get", page, result)
        return result

    def search(self, query, site=None):
        self.logger.info("SEARCHING: " + str(query))
        try:
            return self.hit_cache("search", query)
        except KeyError:
            pass

        result = CACHED_SEARCHER.search(query, site, limit=1)
        if result:
            result = result[0]

        self.push_cache("search", query, result)
        return result


default_cache = None
def get_default_cache():
    return default_cache
