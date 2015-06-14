# colorama is not installed on
# the system, we will use a fake ANSI-Class that will
# return an empty string on all unknown variables.
try:
    from colorama import init
    from colorama import Fore, Back, Style
except ImportError:
    class FakeANSI(object):
        def __getattr__(self, name):
            try:
                return super(FakeANSI, self).__getattr__(name)
            except AttributeError:
                return ""
    Fore = FakeANSI()
    Back = FakeANSI()
    Style = FakeANSI()
else:
    init()
