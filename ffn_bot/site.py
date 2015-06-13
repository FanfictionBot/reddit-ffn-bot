class Site(object):
    def __init__(self, regex, name):
        self.regex = regex
        self.name = name
    def from_requests(self, requests):
        return ()
