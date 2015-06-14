import time
import logging
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


class RequestCache(object):
    """
    Cache for search requests and page-loads.
    """
    
    # Marker for non cached objects.
    EMPTY_RESULT = []
    
    def __init__(self, max_size=10000, expire_time=30*60*1000):
        self.cache = LimitedSizeDict(size_limit=max_size)
        self.expire_time = expire_time
        
    def hit_cache(self, type, query):
        """Check if the value is in the cache."""
        
        result = self.cache.get("%s:%s"%(type, query), self.EMPTY_RESULT)
        if result is not self.EMPTY_RESULT:
            # Let values expire.
            if time.time() - result[1] <= self.expire_time:
                self.push_cache(type, query, result[0])
                return result[0]
        raise KeyError("Not cached")
        
    def push_cache(self, type, query, data):
        """Push a value into the cache."""
        cache_id = "%s:%s"%(type, query)
        if cache_id in self.cache:
            del self.cache[cache_id]
        self.cache[cache_id] = (data, time.time())
        
    def get_page(self, page):
        logging.debug("LOADING: " + str(page))
        try:
            return self.hit_cache("get", page)
        except KeyError:
            pass
            
        result = get(page).text
        self.push_cache("get", page, result)
        return result
        
    def search(self, query):
        logging.debug("SEARCHING: " + str(query))
        try:
            return self.hit_cache("search", query)
        except KeyError:
            pass
        
        result = next(search(query, num=1, stop=1), None)
        self.push_cache("search", query, result)
        return result
        
default_cache = RequestCache()
