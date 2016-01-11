"""
This module stores the comment saving functionality.
"""
import contextlib
import logging
from threading import RLock

import praw.objects


class CommentSet(object):

    def __init__(self, max_age=4):
        self._stored_items = set()
        self.current_generation = set()
        self.last_generations = [set() for i in range(max_age)]

    def add_to_generation(self, genid, item):
        if genid == 0:
            generation = self.current_generation
        elif genid > len(self.last_generations):
            return
        else:
            generation = self.last_generations[genid - 1]

        generation.add(item)
        self._stored_items.add(item)

    def clean_up(self):
        seen = self.current_generation.copy()
        for generation in self.last_generations:
            # Remove seen objects from the current generation.
            generation -= seen

            # Add current generation to seen objects.
            seen |= generation

    def __contains__(self, item):
        return item in self._stored_items

    def __iter__(self):
        def _generation_iterator():
            seen = set()
            for item in self.current_generation:
                yield 0, item
                seen.add(item)
            for genid, generation in enumerate(self.last_generations, 1):
                for item in generation:
                    if item in seen:
                        continue
                    yield genid, item
                    seen.add(item)
        return _generation_iterator()


class CommentList(object):
    """
    Stores the comment list.

    It will not load the comment list until needed.
    """

    COMMENT_STORAGE = 10

    def __init__(self, filename, dry=False, age=4):
        self.clist = None

        self.save_rotation = 0
        self.age = 4

        self.filename = filename
        self.dry = dry
        self.logger = logging.getLogger("CommentList")
        self.lock = RLock()

    def _load(self):
        with self.lock:
            self.clist = CommentSet(max_age=self.age)
            self.logger.debug("Loading comment list...")
            with contextlib.suppress(FileNotFoundError):
                with open(self.filename, "r") as f:
                    for line in f:
                        data = line.strip()
                        data = self.convert_v1_v2(data)
                        gen, data = data.split(" ")
                        self.clist.add_to_generation(int(gen) + 1, data)

    def convert_v1_v2(self, data):
        data = data.split(" ")
        if len(data) == 1:
            gen = 0
            data = data[0]
        else:
            gen, data = data

        # Convert from old format into the new format.
        if data.startswith("SUBMISSION"):
            self.logger.debug("Converting %s into new format" % data)
            data = data.replace("SUBMISSION_", "t3_", 1)
        elif not data.startswith("t") and data[2] != "_":
            self.logger.debug("Converting %s into new format" % data)
            data = "t1_" + data

        return str(gen) + " " + data

    def _save(self):
        try:
            if ((self.save_rotation + 1) % self.COMMENT_STORAGE) == 0:
                self.save()
        finally:
            self.save_rotation = (
                self.save_rotation + 1) % self.COMMENT_STORAGE

    def save(self):
        with self.lock:
            if self.dry or self.clist is None:
                return

            self.clist.clean_up()

            self.logger.debug("Saving comment list...")
            with open(self.filename, "w") as f:
                for genid, item in self.clist:
                    f.write(str(genid) + " " + item + "\n")

    def __contains__(self, cid):
        with self.lock:
            self._init_clist()
            cid = self._convert_object(cid)
            self.logger.debug("Querying: " + cid)
            result = cid in self.clist
            if result:
                # Push item back to first generation as it is
                # obviously needed now.
                self.add(cid)
            return result

    def add(self, cid):
        with self.lock:
            self._init_clist()
            cid = self._convert_object(cid)
            self.logger.debug("Adding comment to list: " + cid)
            self.clist.add_to_generation(0, cid)
            self._save()

    def __del__(self):
        """
        Do not rely on this function.
        The GC is known for not calling the deconstructor
        in certain cases.
        """
        self.save()

    def _init_clist(self):
        if self.clist is None:
            self._load()

    @staticmethod
    def _convert_object(cid):
        if isinstance(cid, praw.objects.RedditContentObject):
            cid = cid.fullname
        return cid

    def __len__(self):
        with self.lock:
            self._init_clist()
            return len(self.clist)

    def __iter__(self):
        with self.lock:
            self._init_clist()
            return iter(self.clist.copy())
