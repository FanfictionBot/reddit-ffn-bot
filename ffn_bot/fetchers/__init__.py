import os.path
from itertools import chain
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


SITES = list(filter(
    lambda x: x is not None, chain.from_iterable(
        (
            (
                # Find and instantiate all Sites
                _try_caller(getattr(module, name)) for name in dir(module)
                if isinstance(getattr(module, name), type) and issubclass(
                    getattr(module, name), Site))  # Import Submodules
            for module in (
                loader.find_module(module).load_module(module) for loader,
                module, ispkg in iter_modules(
                    [os.path.dirname(__file__)]))
        ))))

__all__ = ["SITES"]
