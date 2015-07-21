import argparse
from ffn_bot import cache

DEFAULT_SUBREDDITS = ['HPFanfiction']

def get_bot_parameters():
    """Parse the command-line arguments."""
    # initialize parser and add options for username and password
    parser = argparse.ArgumentParser()
    parser.add_argument('-u', '--user',
                        help='define Reddit login username')

    parser.add_argument(
        '-p', '--password',
        help='define Reddit login password')

    parser.add_argument(
        '-s', '--subreddits',
        action="append",
        default=[],
        help='define target subreddit')

    parser.add_argument(
        '-c', '--comments',
        help="Filename where comments are stored",
        default="CHECKED_COMMENTS.txt")

    parser.add_argument(
        '-l', '--dry',
        action='store_true',
        help="do not send comments.")

    parser.add_argument(
        "-v", "--verbosity",
        default="INFO",
        help="The default log level. Using python level states.")

    parser.add_argument(
        "-f", "--footer",
        default="FOOTER.txt",
        help="The actual footer."
    )

    parser.add_argument(
        "-q", "--limit",
        default=100,
        type=int,
        help="How many items should we query at once?"
    )

    cache.BaseCache.prepare_parser(parser)

    args = parser.parse_args()
    print(repr(args))
    return {
        'user': args.user,
        'password': args.password,
        'user_subreddits': args.subreddits or DEFAULT_SUBREDDITS,
        'dry': args.dry,
        'comments': args.comments,
        'verbosity': args.verbosity,
        'footer': args.footer,
        'limit', args.limit
    }

