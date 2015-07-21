"""
This module stores the comment saving functionality.
"""
import contextlib
import logging
from threading import RLock

import praw.objects


class CommentList(object):
    """
    Stores the comment list.

    It will not load the comment list until needed.
    """

    def __init__(self, filename, dry=False):
        self.clist = None
        self.filename = filename
        self.dry = dry
        self.logger = logging.getLogger("CommmentList")
        self.lock = RLock()

    def _load(self):
        with self.lock:
            self.clist = set()
            self.logger.info("Loading comment list...")
            with contextlib.suppress(FileNotFoundError):
                with open(self.filename, "r") as f:
                    for line in f:
                        data = line.strip()
                        data = self.convert_v1_v2(data)
                        self.clist.add(data)

    def convert_v1_v2(self, data):
        # Convert from old format into the new format.
        if data.startswith("SUBMISSION"):
            self.logger.debug("Converting %s into new format"%data)
            data = data.replace("SUBMISSION_", "t3_", 1)
        elif not data.startswith("t") and data[2] != "_":
            self.logger.debug("Converting %s into new format"%data)
            data = "t1_" + data
        return data

    def _save(self):
        self.save()

    def save(self):
        with self.lock:
            if self.dry or self.clist is None:
                return

            self.logger.info("Saving comment list...")
            with open(self.filename, "w") as f:
                for item in self.clist:
                    f.write(item + "\n")

    def __contains__(self, cid):
        with self.lock:
            self._init_clist()
            cid = self._convert_object(cid)
            self.logger.debug("Querying: " + cid)
            return cid in self.clist

    def add(self, cid):
        with self.lock:
            self._init_clist()
            cid = self._convert_object(cid)
            self.logger.debug("Adding comment to list: " + cid)
            if cid not in self:
                self.clist.add(cid)
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
