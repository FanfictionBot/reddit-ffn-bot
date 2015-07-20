from concurrent.futures import ThreadPoolExecutor
from queue import Queue, Empty
from threading import Lock
import logging

from praw.helpers import comment_stream, submission_stream

from ffn_bot.bot_tools import print_exception


def mutlistream(*iterators):
    queue = Queue()
    active = {id(iterator): None for iterator in iterators}
    executor = ThreadPoolExecutor(len(iterators))
    lock = Lock()

    def _next(iterator):
        try:
            value = next(iterator)
            error = False
        except BaseException as e:
            error = True
            value = e

        with lock:
            if error:
                # Since the exception will propagate up the stack
                # we will just print the execption with debug level.
                logging.debug("Error occured")
                print_exception(e, level=logging.DEBUG)

                if isinstance(e, StopIteration):
                    del active[id(iterator)]
                else:
                    queue.put((False, value))
                    active.clear()
            else:
                logging.debug("Result of %r: %r"%(iterator, value))
                queue.put((True, value))

    def _submit(iterator):
        with lock:
            if id(iterator) not in active:
                return

            future = active[id(iterator)]
            if future is not None and not future.done():
                return

            logging.debug("Submitting new item to executor: %r"%iterator)
            active[id(iterator)] = executor.submit(_next, iterator)
    try:
        while True:
            with lock:
                if len(active) == 0:
                    break

            if queue.empty():
                for iterator in iterators:
                    _submit(iterator)
            try:
                success, res = queue.get(timeout = 1)
            except Empty:
                continue

            if not success:
                raise res
            else:
                # Interesting behaviour:
                # If you close the generator, we will
                # actually be able to stop the executor.
                try:
                    yield res
                except GeneratorExit:
                    logging.info("Exiting iterator gracefully.")
                    return

        while not queue.empty():
            success, res = queue.get_nowait()
            if not success:
                raise res
    finally:
        executor.shutdown(wait=False)


class queuestream(object):
    def __init__(self):
        self.queue = Queue()

    def __next__(self):
        return self.queue.get()

    def add(self, value):
        self.queue.put(value)


def full_reddit_stream(r, subreddit, *, additional=(), **kwargs):
    cstream = comment_stream(r, subreddit, **kwargs)
    sstream = submission_stream(r, subreddit, **kwargs)

    yield from mutlistream(cstream, sstream, *additional)
