import sys
import logging
import importlib

from ffn_bot.bot_tools import print_exception
from ffn_bot.config import construct_parser, load_settings, get_settings


def main(args):
    parser = construct_parser(False)
    result = parser.parse_known_args(args)[0]

    load_settings(result.settings)
    
    settings = get_settings()
    main_func = settings["bot"]["main"]
    *module, func = main_func.split(".")

    logging.debug("Fanfiction.Net Bot")
    logging.debug("Initializing Bot.")

    logging.info("Searching main-func: " + main_func)
    # Find module.
    module = ".".join(module)
    module = importlib.import_module(module)
    func = getattr(module, func)

    logging.debug("Starting bot...")
    logging.debug("=====================")
    try:
        sys.exit(func(args))
    except Exception as e:
        print_exception(e)
        logging.critical("Error detected. Stopping bot.")
        sys.exit(255)
