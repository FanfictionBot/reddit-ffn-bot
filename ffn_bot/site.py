class Site(object):
    def __init__(self, regex, name=None):
        if name is None:
            # Automatically assign a name for the site.
            name = self.__class__.__module__ + "." + self.__class__.__name__
        self.regex = regex
        self.name = name
    def from_requests(self, requests):
        return ()
