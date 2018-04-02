class Application(object):
    """
    Singleton containing the current applications state.

    TODO: Singletons are a really bad idea.
    """

    STATE = None

    def __new__(cls):
        if cls.STATE is not None:
            return cls.STATE
        op = super(Application, cls).__new__(cls)
        cls.STATE = op
        return op

    @classmethod
    def reset(cls):
        cls.STATE = None
        return cls()
