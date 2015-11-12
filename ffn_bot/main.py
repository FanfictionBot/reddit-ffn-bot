import importlib
from ffn_bot.config import construct_parser, load_settings, get_settings


def main(args):
    parser = construct_parser(False)
    result = parser.parse_known_args(args)[0]

    load_settings(result.settings)
    
    settings = get_settings()
    main_func = settings["bot"]["main"]
    *module, func = main_func.split(".")

    # Find module.
    module = ".".join(module)
    module = importlib.import_module(module)

    return getattr(module, func)(args)
