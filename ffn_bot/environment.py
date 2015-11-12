class BotEnvironment(object):
    """
    This bot stores function about how messages are
    counted and converted to a suitable string format.
    """

    def stats(self, story):
        """
        Count a story towards the stats.
        """
        pass

    def to_string(self, story, markers=frozenset()):
        """
        Converts a story to string.
        """
        return "Not Implemented"
