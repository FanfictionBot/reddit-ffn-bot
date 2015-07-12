import re
import sys
import atexit
import argparse
import itertools
import logging
import praw

from ffn_bot.fetchers import SITES

from ffn_bot import bot_tools

# For pretty text
from ffn_bot.bot_tools import Fore, Back, Style

__author__ = 'tusing, MikroMan, StuxSoftware'

USER_AGENT = "Python:FanfictionComment:v0.5 (by tusing, StuxSoftware, and MikroMan)"
r = praw.Reddit(USER_AGENT)
DEFAULT_SUBREDDITS = ['HPFanfiction', 'fanfiction', 'HPMOR']
SUBREDDIT_LIST = set()
CHECKED_COMMENTS = set()

# Allow to modify the behaviour of the comments
# by adding a special function into the system
#
# Currently the following markers are supported:
# ffnbot!ignore              Ignore the comment entirely
# ffnbot!noreformat          Fix FFN formatting by not reformatting.
# ffnbot!nodistinct          Don't make sure that we get distinct requests
# ffnbot!directlinks         Also extract story requests from direct links
# ffnbot!submissionlink      Direct-Links just for the submission-url
CONTEXT_MARKER_REGEX = re.compile(r"ffnbot!([^ ]+)")

FOOTER = "\n\nSupporting fanfiction.net (*linkffn*), AO3 (buggy) (*linkao3*), HPFanficArchive (*linkffa*), FictionPress (*linkfp*), AdultFanFiction (linkaff) (story ID only)" + \
    "\n\nRead usage tips and tricks  [**here**](https://github.com/tusing/reddit-ffn-bot/blob/master/README.md).\n\n" + \
    "^(**New Feature:** Parse multiple fics in a single call with;semicolons;like;this!)\n\n" + \
    "^(**New Feature:** Type 'ffnbot!directlinks' in any comment to have the bot **automatically parse fanfiction links** and make a reply, without even calling the bot! Added AdultFanFiction support!)" + \
    "\n\n^^**Update** ^^**7/11/2015:** ^^More ^^formatting ^^bugs ^^fixed. ^^Feature ^^added!\n\n^^^^^^^^^^^^^^^^^ffnbot!ignore"

# For testing purposes
DRY_RUN = False

# This is a experimental feature of the program
# Please use with caution
USE_GET_COMMENTS = False

logging.getLogger().setLevel(logging.DEBUG)


def get_regexps():
    """Returns the regular expressions for the sites."""
    global SITES
    return {site.name: re.compile(site.regex, re.IGNORECASE) for site in SITES}


def get_sites():
    """Returns a dictionary of all sites."""
    global SITES
    return {site.name: site for site in SITES}


def run_forever():
    atexit.register(save_comments)
    sys.exit(_run_forever())


def _run_forever():
    """Run-Forever"""
    while True:
        try:
            main()
        # Exit on sys.exit and keyboard interrupts.
        except KeyboardInterrupt:
            raise
        except SystemExit as e:
            return e.code
        except:
            logging.error("MAIN: AN EXCEPTION HAS OCCURED!")
            bot_tools.print_exception()
            bot_tools.pause(1, 0)


def main():
    """Basic main function."""
    # moved call for agruments to avoid double calling
    bot_parameters = get_bot_parameters()
    login_to_reddit(bot_parameters)
    load_checked_comments()
    load_subreddits(bot_parameters)
    init_global_flags(bot_parameters)

    while True:
        single_pass()


def init_global_flags(bot_parameters):
    global USE_GET_COMMENTS, DRY_RUN

    if bot_parameters["experimental"]["getcomments"]:
        print("You are using the experimental comment parsing")
        print("strategy. It may not immidiately work.")
        USE_GET_COMMENTS = True

    DRY_RUN = bool(bot_parameters["dry"])
    if DRY_RUN:
        print("Dry run enabled. No comment will be sent.")


def get_bot_parameters():
    """Parse the command-line arguments."""
    # initialize parser and add options for username and password
    parser = argparse.ArgumentParser()
    parser.add_argument('-u', '--user', help='define Reddit login username')
    parser.add_argument(
        '-p', '--password',
        help='define Reddit login password')

    parser.add_argument(
        '-s', '--subreddits',
        help='define target subreddits; seperate with commas')

    parser.add_argument(
        '-d', '--default',
        action='store_true',
        help='add default subreddits, can be in addition to -s')

    parser.add_argument(
        '-l', '--dry',
        action='store_true',
        help="do not send comments.")

    parser.add_argument(
        "--getcomments",
        action="store_true",
        help="Experimental feature. Makes a more reliable bot.")

    args = parser.parse_args()

    return {
        'user': args.user,
        'password': args.password,
        'user_subreddits': args.subreddits,
        'default': args.default,
        'dry': args.dry,
        # Switches for experimental features
        'experimental': {
            "getcomments": args.getcomments
        }
    }


def login_to_reddit(bot_parameters):
    """Performs the login for reddit."""
    print("Logging in...")
    r.login(bot_parameters['user'], bot_parameters['password'])
    print(Fore.GREEN, "Logged in.", Style.RESET_ALL)


def load_subreddits(bot_parameters):
    """Loads the subreddits this bot operates on."""
    global SUBREDDIT_LIST
    print("Loading subreddits...")

    if bot_parameters['default'] is True:
        print("Adding default subreddits: ", DEFAULT_SUBREDDITS)
        for subreddit in DEFAULT_SUBREDDITS:
            SUBREDDIT_LIST.add(subreddit)

    if bot_parameters['user_subreddits'] is not None:
        user_subreddits = bot_parameters['user_subreddits'].split(',')
        print("Adding user subreddits: ", user_subreddits)
        for subreddit in user_subreddits:
            SUBREDDIT_LIST.add(subreddit)

    if len(SUBREDDIT_LIST) == 0:
        print("No subreddit specified. Adding test subreddit.")
        SUBREDDIT_LIST.add('tusingtestfield')
    print("LOADED SUBREDDITS: ", SUBREDDIT_LIST)


def handle_submission(submission):
    if not is_submission_checked(submission):
        logging.info("Found new submission: " + submission.id)
        try:
            parse_submission_text(submission)
        finally:
            check_submission(submission)


def handle_comment(comment):
    logging.debug("Handling comment: " + comment.id)
    if str(comment.id) not in CHECKED_COMMENTS:
        logging.info("Found new comment: " + comment.id)
        try:
            make_reply(comment.body, comment.id, comment.reply)
        finally:
            check_comment(comment.id)


def single_pass():
    try:
        if USE_GET_COMMENTS:
            single_pass_experimental()
        else:
            single_pass_normal()
    except Exception:
        bot_tools.print_exception()
    bot_tools.pause(1, 0)


def single_pass_normal():
    for subreddit in SUBREDDIT_LIST:
        logging.info("Handling Subreddit: " + subreddit)
        for submission in r.get_subreddit(subreddit).get_hot(limit=50):
            handle_submission(submission)

            logging.info("Checking SUBMISSION: " + submission.id)
            flat_comments = praw.helpers.flatten_tree(submission.comments)
            for comment in flat_comments:
                handle_comment(comment)


def single_pass_experimental():
    # We actually use a multireddit to acieve our goal
    # of watching multiple reddits.
    subreddit = r.get_subreddit("+".join(SUBREDDIT_LIST))

    print(subreddit)

    logging.info("Parsing new submissions.")
    for submission in subreddit.get_new(limit=50):
        handle_submission(submission)

    logging.info("Parsing new comments.")
    for comment in subreddit.get_comments(limit=100):
        handle_comment(comment)


def save_comments():
    """Saves all comments"""
    if DRY_RUN:
        return

    with open("CHECKED_COMMENTS.txt", "w") as file:
        for id in CHECKED_COMMENTS:
            file.write(id)


def check_comment(id):
    """Marks a comment as checked."""
    global CHECKED_COMMENTS, DRY_RUN
    CHECKED_COMMENTS.add(str(id))
    save_comments()


def load_checked_comments():
    """Loads all comments that have been checked."""
    global CHECKED_COMMENTS
    logging.info('Loading CHECKED_COMMENTS...')
    try:
        with open('CHECKED_COMMENTS.txt', 'r') as file:
            CHECKED_COMMENTS = {str(line.rstrip('\n')) for line in file}
    except IOError:
        bot_tools.print_exception()
        CHECKED_COMMENTS = set()
    print('Loaded CHECKED_COMMENTS.')
    logging.info(CHECKED_COMMENTS)


def check_submission(submission):
    """Mark the submission as checked."""
    check_comment("SUBMISSION_" + str(submission.id))


def is_submission_checked(submission):
    """Check if the submission was checked."""
    global CHECKED_COMMENTS
    return "SUBMISSION_" + str(submission.id) in CHECKED_COMMENTS


def parse_submission_text(submission):
    body = submission.selftext

    markers = parse_context_markers(body)

    # Since the bot would start downloading the stories
    # here, we add the ignore option here
    if "ignore" in markers:
        return

    additions = []
    if "submissionlink" in markers:
        additions.extend(get_direct_links(submission.url, markers))

    make_reply(
        submission.selftext, submission.id, submission.add_comment, markers,
        additions)


def make_reply(body, id, reply_func, markers=None, additions=()):
    """Makes a reply for the given comment."""
    reply = formulate_reply(body, markers, additions)

    if not reply:
        print("Empty reply!")
    elif len(reply) > 10:
        print(Fore.GREEN)
        print('--------------------------------------------------')
        print('Outgoing reply to ' + id + ':\n' + reply + FOOTER)
        print('--------------------------------------------------')
        print(Style.RESET_ALL)

        # Do not send the comment.
        if not DRY_RUN:
            reply_func(reply + FOOTER)

        bot_tools.pause(1, 20)
        print('Continuing to parse submissions...')
    else:
        logging.info("No reply conditions met.")


def parse_context_markers(comment_body):
    """
    Changes the context of the story subsystem.
    """
    # The power of generators, harnessed in this
    # oneliner.
    return set(
        s.lower() for s in itertools.chain.from_iterable(
            v.split(",") for v in CONTEXT_MARKER_REGEX.findall(comment_body)))


def get_direct_links(string, markers):
    direct_links = []
    for site in SITES:
        direct_links.append(site.extract_direct_links(string, markers))
    # Flatten the story-list
    return itertools.chain.from_iterable(direct_links)


def formulate_reply(comment_body, markers=None, additions=()):
    """Creates the reply for the given comment."""
    if markers is None:
        # Parse the context markers as some may be required here
        markers = parse_context_markers(comment_body)

    # Ignore this message if we hit this marker
    if "ignore" in markers:
        return None

    # Just parse normally of nothing other turns up.
    REGEXPS = get_regexps()
    requests = {}
    for name, regexp in REGEXPS.items():
        tofind = regexp.findall(comment_body)
        requests[name] = tofind

    direct_links = additions
    if "directlinks" in markers:
        direct_links = itertools.chain(
            direct_links, get_direct_links(comment_body, markers))

    return parse_comment_requests(requests, markers, direct_links)


def parse_comment_requests(requests, context, additions):
    """
    Executes the queries and return the
    generated story strings as a single string
    """
    # Merge the story-list
    results = itertools.chain(
        _parse_comment_requests(requests, context), additions)

    if "nodistinct" not in context:
        results = set(results)
    return "".join(str(result) for result in results if result)


def _parse_comment_requests(requests, context):
    sites = get_sites()
    for site, queries in requests.items():
        if len(queries) > 0:
            print("Requests for '%s': %r" % (site, queries))
        for query in queries:
            for comment in sites[site].from_requests(query.split(";"),
                                                     context):
                if comment is None:
                    continue
                yield comment
