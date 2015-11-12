from logging.config import dictConfig
from ffn_bot.config import load_settings, get_settings, construct_parser

DEFAULT_SUBREDDITS = ['HPFanfiction']

def get_old_dict():
    settings = get_settings()["bot"]
    return {
        "user_subreddits": settings["subreddits"],
        "comments": settings["comments"]["file"],
        "age": settings["comments"]["max-age"],

        "footer": settings["footer"]
    }


def get_bot_parameters(args):
    """Parse the command-line arguments."""
    parser = construct_parser()

    # initialize parser and add options for username and password
    parser.add_argument(
        '-l', '--dry',
        action='store_true',
        help="do not send comments.")

    parser.add_argument(
        "-q", "--limit",
        default=100,
        type=int,
        help="How many items should we query at once?"
    )
    args = parser.parse_args(args)

    result = {
        'dry': args.dry,
        'limit': args.limit,
    }
    result.update(get_old_dict())
    return result

