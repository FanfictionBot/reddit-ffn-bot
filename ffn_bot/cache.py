import time
import random
from google import search
from requests import get
from collections import OrderedDict


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
        argument_parser.add_argument(
            "--cache-type",
            dest="cachetype",
            default="local",
            action="store",
            choices = cls.CACHE_TYPES.keys()
        )
        ns, _ = argument_parser.parse_known_args(args)
        ctype = cls.CACHE_TYPES[ns.cachetype]
        return ctype(argument_parser, args)


@BaseCache.register_type("local")
class LocalCache(BaseCache):
    EMPTY_RESULT = []

    def __init__(self, argument_parser, args):
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
        ns, _ = argument_parser.parse_known_args(args)
        self.expire = ns.cacheexpire
        self.cache = LimitedSizeDict(size_limit=ns.cachesize)

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
    def __init__(self, argument_parser, args):
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
        ns, _ = argument_parser.parse_known_args(args)
        import memcache
        self.client = memcache.Client(ns.cachehosts)
        self.expire = ns.cacheexpire

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


def _google_throttler(factor=1.1, minwait=2):
    wait = minwait
    lsearch = 0

    resp = None
    while True:
        # Return the next response
        # Get the next request
        req = yield resp

        if lsearch != 0:
            # Determine how much wait time has passed.
            wait = wait - (time.time()-lsearch)
            if wait < 0:
                wait = minwait

            # Wait a little bit until we do the request.
            time.sleep(wait)

            # Grow the wait factor
            wait*=factor

        # Do the query
        try:
            resp = (next(search(req, num=1, stop=1), None),None)
        except BaseException as e:
            resp = (None, e)
        # Write the time of query end.
        lsearch = time.time()


def google_throttler(factor=1.1, minwait=2):
    res = _google_throttler(factor, minwait)
    next(res)
    return res


class RequestCache(object):

    """
    Cache for search requests and page-loads.
    """

    def __init__(self, args=None):
        self.cache = BaseCache.by_arguments(args)
        self.google = google_throttler()

    def hit_cache(self, type, query):
        """Check if the value is in the cache."""
        return self.cache.get("%s:%s" % (type, query))

    def push_cache(self, type, query, data):
        """Push a value into the cache."""
        return self.cache.set("%s:%s"%(type,query), data)

    def get_page(self, page, throttle=0, **kwargs):
        print("LOADING: " + str(page))
        try:
            return self.hit_cache("get", page)
        except KeyError:
            pass

        # Throtle only if we don't have a version cached.
        if throttle:
            time.sleep(throttle)
        result = get(page, **kwargs).text

        self.push_cache("get", page, result)
        return result

    def search(self, query):
        print("SEARCHING: " + str(query))
        try:
            return self.hit_cache("search", query)
        except KeyError:
            pass

        result, error = self.google.send(query)
        if not result and error:
            raise error

        print(result)
        self.push_cache("search", query, result)
        return result

default_cache = RequestCache(["--cache-type", "local"])
