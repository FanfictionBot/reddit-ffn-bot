import time
import queue
import logging
from threading import RLock, Thread

from praw.objects import RedditContentObject

from ffn_bot.reddit.commentlist import CommentList


class ThreadsafeUniqueQueue(object):
    """
    Represents a queue that only supports unique objects.
    """

    def __init__(self):
        self.queue = queue.Queue()
        self.items = set()
        self.converters = {}
        self.lock = RLock()

    def register(self, type, converter):
        with self.lock:
            self.converters[type] = converter

    def _convert(self, item):
        cls = type(item)
        with self.lock:
            for base in cls.mro():
                if base in self.converters:
                    return self.converters[base](item)
        return item

    def put(self, *items):
        with self.lock:
            for item in items:
                # Make sure we have something hashable.
                conv = self._convert(item)

                # Check if item is in queue
                if conv in items:
                    continue

                self.items.add(conv)
                self.queue.put(item)

    def get(self):
        res = self.queue.get()
        with self.lock:
            self.items.remove(self._convert(res))
        return res

    def __contains__(self, item):
        with self.lock:
            conv = self._convert(item)
            return conv in self.items


class QueueThread(Thread):

    def __init__(self, r, comments, logger):
        super(QueueThread, self).__init__()
        self.r = r
        self.daemon = True
        self.queue = ThreadsafeUniqueQueue()
        self.running = False
        self.comments = comments
        self.fetchers = []
        self.logger = logger

    def register_fetcher(self, fetcher):
        self.fetchers.append(fetcher)

    def register_converter(self, type, converter):
        self.queue.register(type, converter)

    def _fetch(self, fetcher):
        if not self.running:
            return
        fetcher(self)

    def add(self, *items):
        items = list(filter((lambda i: i not in self), items))
        if len(items)>0:
            self.logger.info("Adding %d items."%len(items))
        for item in items:
            self.queue.put(item)

    def run(self):
        self.running = True
        while self.running:
            self.logger.info("Querying Reddit...")
            for fetcher in self.fetchers:
                self.r._use_oauth = False
                self._fetch(fetcher)
            for i in range(10):
                if not self.running:
                    break

                time.sleep(1)

    def get(self):
        while True:
            res = self.queue.get()
            if res not in self.comments:
                return res

    def shutdown(self, wait=True):
        self.running = False
        if wait and self.isAlive():
            self.join()

    def __contains__(self, item):
        with self.queue.lock:
            if item in self.queue:
                return True
            return item in self.comments


class QueueStrategy(object):

    def __init__(self, r, subreddit, comments, handler, limit):
        self.r = r
        self.logger = logging.getLogger("Queue")
        self.queue = QueueThread(r, comments, self.logger)
        self.handler = handler
        self.subreddit = subreddit
        self.count = 0
        self.limit = limit
        self._get_submissions = self._stream(subreddit.get_new)
        self._get_comments = self._stream(subreddit.get_comments)

    def run(self):
        self.queue.register_converter(
            RedditContentObject, CommentList._convert_object
        )

        self.queue.register_fetcher(self._get_submissions)
        self.queue.register_fetcher(self._get_comments)

        self.queue.start()
        try:
            while True:
                item = self.queue.get()
                self.handler(item)
        finally:
            self.logger.info("Shutting down queue.")
            self.queue.shutdown()
            self.logger.debug("Queue closed.")

    def _stream(self, func):
        def _run(queue):
            self.count = (self.count+1) % 200

            params = {
                "count": self.count
            }

            self.r._use_oauth = False
            queue.add(*func(limit=self.limit, params=params))

        return _run
