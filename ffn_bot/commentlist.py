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
        self._transaction_stack = []

    def __enter__(self):
        self._init_clist()
        self._transaction_stack.append(self.clist.copy())
        return self

    def __exit__(self, exc, val, tb):
        last_transaction = self._transaction_stack.pop()
        if exc:
            self.clist = last_transaction
        self.save()

    def _load(self):
        self.clist = set()
        self.logger.info("Loading comment list...")
        with contextlib.suppress(FileNotFoundError):
            with open(self.filename, "r") as f:
                for line in f:
                    self.clist.add(line.strip())

    def _save(self):
        if not len(self._transaction_stack):
            self.save()

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

    def __len__(self):
        self._init_clist()
        return len(self.clist)

    def __iter__(self):
        self._init_clist()
        return iter(self.clist)
