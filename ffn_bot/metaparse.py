"""
I want a nicer implementation of some parsers.
"""
import collections

class MetaparserMeta(type):
    """
    Metaclass for the Metadata-Parser class.

    This is very sophisticated magic and very, very
    advanced stuff.
    """

    def __prepare__(cls, bases, **kwds):
        return collections.OrderedDict()

    def __new__(cls, name, bases, what):
        result = super(MetaparserMeta, cls).__new__(cls, name, bases, what)

        # Find all parsers
        parsers = []
        for base in result.mro():
            for parser in getattr(base, "_parser", ()):
                if parser not in parsers:
                    parsers.append(parser)

        # Add all newly implemented parsers.
        for k, v in what.items():
            if hasattr(v, "_parser") and v._parser:
                parsers.append(getattr(result, k))
        result._parsers = parsers

        # Return the new class.
        return result


class Metaparser(metaclass=MetaparserMeta):
    """
    What wonderful magic is happening here...
    :)
    """

    def __new__(cls, url, tree):
        result = collections.OrderedDict()

        for parser in cls._parsers:
            actual_name = parser.__name__.replace("_", " ")
            result[actual_name] = parser(url, tree)

        return result

def parser(func):
    """
    Decorator to stick into the metaparser class.
    """
    func._parser = True
    return func
