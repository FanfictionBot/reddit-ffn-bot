import time
import logging
from requests import get
from collections import OrderedDict


from ffn_bot.searchengines import Searcher


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
    def by_arguments(cls, args):
        import argparse
        argument_parser = argparse.ArgumentParser()
        cls.prepare_parser(argument_parser)

        ns, _ = argument_parser.parse_known_args(args)
        ctype = cls.CACHE_TYPES[ns.cachetype]
        return ctype(ns)

    @classmethod
    def prepare_parser(cls, argument_parser):
        argument_parser_group = argument_parser.add_argument_group("caches")
        argument_parser_group.conflict_handler = "resolve"

        argument_parser_group.add_argument(
            "--cache-type",
            dest="cachetype",
            default="local",
            action="store",
            choices = cls.CACHE_TYPES.keys()
        )

        part_group = argument_parser_group.add_mutually_exclusive_group()

        for n, t in cls.CACHE_TYPES.items():
            group = part_group.add_argument_group(n)
            t.prepare_parser(group)


@BaseCache.register_type("local")
class LocalCache(BaseCache):
    EMPTY_RESULT = []

    def __init__(self, ns):
        self.expire = ns.cacheexpire
        self.cache = LimitedSizeDict(size_limit=ns.cachesize)

    @classmethod
    def prepare_parser(cls, argument_parser):
        argument_parser.add_argument(
            "--cache-size",
            dest="cachesize",
            default=10000,
            type=int
        )
        argument_parser.add_argument(
            "--cache-expire",
            dest="cacheexpire",
            default=30*60,
            type=int
        )

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
        self.client = memcache.Client(ns.cachehosts)
        self.expire = ns.cacheexpire

    @classmethod
    def prepare_parser(cls, argument_parser):
        argument_parser.add_argument(
            "--cache-host",
            dest="cachehosts",
            default=["127.0.0.1:11211"],
            action="append"
        )

        argument_parser.add_argument(
            "--cache-expire",
            dest="cacheexpire",
            default=30*60,
            type=int
        )

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
    def enforce_ascii(string):
        # We expect humanreadable keys, so we use utf-7
        # instead of base64 to have smaller keys.
        return string.encode("utf-7", "replace").decode("ascii")


class RequestCache(object):

    """
    Cache for search requests and page-loads.
    """

    def __init__(self, args=None):
        self.cache = BaseCache.by_arguments(args)
        self.logger = logging.getLogger("RequestCache")

    def hit_cache(self, type, query):
        """Check if the value is in the cache."""
        self.logger.debug("Hitting cache: " + "%s:%s" % (type, query))
        return self.cache.get("%s:%s" % (type, query))

    def push_cache(self, type, query, data):
        """Push a value into the cache."""
        self.logger.debug("Inserting cache: " + "%s:%s" % (type, query))
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

        result = get(page, **kwargs).text

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

default_cache = RequestCache(["--cache-type", "local"])
