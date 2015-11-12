import yaml
import argparse
from logging.config import dictConfig

SETTINGS = None
def get_settings():
    return SETTINGS


def load_settings(path):
    global SETTINGS

    with open(path, "r") as f:
        SETTINGS = yaml.safe_load(f.read())

    dictConfig(get_settings()["logging"])

def construct_parser(help=True):
    parser = argparse.ArgumentParser(add_help=help)
    parser.add_argument(
        "-s", "--settings",
        default="settings.yml",
        help="The file where the settings are stored."
    )
    return parser
