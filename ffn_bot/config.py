import yaml
import argparse
from logging.config import dictConfig

SETTINGS = None
DEFAULT_SUBREDDITS = ['HPFanfiction']
# user, password
# user_subreddits
# comments
# footer
# itemage
def get_settings():
    return SETTINGS


def get_old_dict():
    settings = get_settings()
    return {
        "user_subreddits": settings["subreddits"],
        "comments": settings["comments"]["file"],
        "age": settings["comments"]["max-age"],

        "footer": settings["footer"]
    }


def get_bot_parameters():
    """Parse the command-line arguments."""
    global SETTINGS

    # initialize parser and add options for username and password
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-s", "--settings",
        default="settings.yml",
        help="The file where the settings are stored."
    )

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
    args = parser.parse_args()

    with open(args.settings, "r") as f:
        SETTINGS = yaml.safe_load(f.read())

    dictConfig(SETTINGS["logging"])

    result = {
        'dry': args.dry,
        'limit': args.limit,
    }
    result.update(get_old_dict())
    return result

