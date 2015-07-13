"""
This module stores the comment saving functionality.
"""
import contextlib
import logging


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

    def _load(self):
        self.clist = set()
        with contextlib.suppress(FileNotFoundError):
            self.logger.info("Loading comment list...")
            with open(self.filename, "r") as f:
                for line in f:
                    self.clist.add(line.strip())

    def save(self):
        if self.dry or self.clist is None:
            return

        self.logger.info("Saving comment list...")
        with open(self.filename, "w") as f:
            f.writelines(self.clist)

    def __contains__(self, cid):
        self._init_clist()
        return cid in self.clist

    def add(self, cid):
        self._init_clist()
        self.logger.debug("Adding comment to list: " + cid)
        self.clist.add(cid)
        self.save()

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

    def __len__(self):
        self._init_clist()
        return len(self.clist)

    def __iter__(self):
        self._init_clist()
        return iter(self.clist)
