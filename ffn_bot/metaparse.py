"""
I want a nicer implementation of some parsers.
"""
import collections
import inspect

basestring = (str, bytes)
MetadataItem = collections.namedtuple("MetadataItem", "name value")


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
            for parser in getattr(base, "_parsers", ()):
                if parser not in parsers:
                    parsers.append(parser)

        # Add all newly implemented parsers.
        for k, v in what.items():
            if hasattr(v, "_parser") and v._parser:
                parsers.append(getattr(result, k))
        result._parsers = parsers

        # Return the new class.
        return result


def _apply_generator(func, *args, **kwargs):
    result = func(*args, **kwargs)
    if inspect.isgenerator(result):
        for item in result:
            yield item
    elif (
            (not isinstance(result, collections.Sequence))
            or len(result) != 2
            or (isinstance(result, basestring))
    ):
        yield func.__name__, result
    else:
        yield result


class Metaparser(metaclass=MetaparserMeta):
    """
    What wonderful magic is happening here...
    :)
    """

    def __new__(cls, id, tree):
        result = collections.OrderedDict()

        for parser in cls._parsers:
            for name, value in _apply_generator(parser, id, tree):
                result[name] = value

        return result

    @classmethod
    def parse_to_string(
            cls,
            id, tree,

            # Pass a function that will join the two strings
            join=" **|** ".join,

            # Pass a function that will format each item
            itemfmt="*{0}*: {1}".format
    ):
        return join(map((lambda i: itemfmt(*i)), cls(id, tree).items()))


def parser(func):
    func._parser = True
    return func
