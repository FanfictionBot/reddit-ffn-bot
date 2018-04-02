import collections
import os.path
from pkgutil import iter_modules

from ffn_bot.site import Site


# This bit of complexity allows the
# Module to automatically discover its own fetchers
# Just drop the python file in the directory and it will be loaded.
def _try_caller(func):
    try:
        return func()
    except Exception:
        return None


def _load_sites():
    for loader, name, _ in iter_modules([os.path.dirname(__file__)]):
        module = loader.find_module(name).load_module(name)
        for var_name in dir(module):
            item = getattr(module, var_name)
            if isinstance(item, type) and issubclass(item, Site):
                try:
                    yield item()
                except TypeError:
                    pass


def get_site(name):
    """Returns the site by name"""
    for site in SITES:
        if site.name == name:
            return site.name
    return None


def get_sites():
    """Returns a dictionary of all sites."""
    return collections.OrderedDict((site.name, site) for site in SITES)


SITES = list(_load_sites())

__all__ = ["SITES"]
