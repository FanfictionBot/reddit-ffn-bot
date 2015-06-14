import re
import sys
import argparse
import logging
import praw

from ffn_bot import fanfiction_parser
from ffn_bot import ao3
from ffn_bot import bot_tools

# For pretty text
from ffn_bot.bot_tools import Fore, Back, Style 

__author__ = 'tusing, MikroMan, StuxSoftware'

USER_AGENT = "Python:FanfictionComment:v0.5 (by tusing, StuxSoftware, and MikroMan)"
r = praw.Reddit(USER_AGENT)
DEFAULT_SUBREDDITS = ['HPFanfiction', 'fanfiction', 'HPMOR']
SUBREDDIT_LIST = set()
CHECKED_COMMENTS = set()

# New regex shoul match more possible letter combinations, see screenshot below
# http://prntscr.com/7g0oeq

# REGEXPS = {'[Ll][iI][nN][kK][fF]{2}[nN]\((.*?)\)': 'ffn'}
SITES = [
    fanfiction_parser.FanfictionNetSite(),
    fanfiction_parser.FictionPressSite(),
    ao3.ArchiveOfOurOwn()
]

FOOTER = "\n\n*NOW WITH AO3 (linkao3) and FICTIONPRESS (linkfp) support! Read usage tips and tricks  [here](https://github.com/tusing/reddit-ffn-bot/blob/master/README.md).*"


def get_regexps():
    """Returns the regular expressions for the sites."""
    global SITES
    return {site.name: re.compile(site.regex, re.IGNORECASE) for site in SITES}


def get_sites():
    """Returns a dictionary of all sites."""
    global SITES
    return {site.name: site for site in SITES}


def run_forever():
    """Run-Forever"""
    while True:
        try:
            main()
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

    while True:
        for SUBREDDIT in SUBREDDIT_LIST:
            parse_submissions(r.get_subreddit(SUBREDDIT))
            bot_tools.pause(1, 0)


def get_bot_parameters():
    """Parse the command-line arguments."""
    # initialize parser and add options for username and password
    parser = argparse.ArgumentParser()
    parser.add_argument('-u', '--user', help='define Reddit login username')
    parser.add_argument('-p', '--password', help='define Reddit login password')
    parser.add_argument(
        '-s', '--subreddits', help='define target subreddits; seperate with commas')

    # Can also add possibility with -s option to aquire comma separated list of subreddits
    # then do: subs = args.subreddit.split(',')
    # and return this list, then append/extend to Subreddit_list or default_subs
    # and possibl transform to set to avoid duplicates.

    # Alternatively we can just use docopt. (See http://docopt.org/)

    parser.add_argument(
        '-d', '--default', action='store_true', help='add default subreddits, can be in addition to -s')

    args = parser.parse_args()

    return {'user': args.user, 'password': args.password, 'user_subreddits': args.subreddits, 'default': args.default}


def login_to_reddit(bot_parameters):
    """Performs the login for reddit."""
    logging.info("Logging in...")
    r.login(bot_parameters['user'], bot_parameters['password'])
    logging.info("Login successful")


def load_subreddits(bot_parameters):
    """Loads the subreddits this bot operates on."""
    global SUBREDDIT_LIST
    logging.info("Loading subreddits...")

    if bot_parameters['default'] is True:
        print("Adding default subreddits: %r" % DEFAULT_SUBREDDITS)
        for subreddit in DEFAULT_SUBREDDITS:
            SUBREDDIT_LIST.add(subreddit)

    if bot_parameters['user_subreddits'] is not None:
        user_subreddits = bot_parameters['user_subreddits'].split(',')
        logging.info("Adding user subreddits: "+ str(user_subreddits))
        for subreddit in user_subreddits:
            SUBREDDIT_LIST.add(subreddit)

    if len(SUBREDDIT_LIST) == 0:
        logging.info("No subreddit specified. Adding test subreddit.")
        SUBREDDIT_LIST.add('tusingtestfield')
    logging.info("LOADED SUBREDDITS: "+ str(SUBREDDIT_LIST))


def check_comment(id):
    """Marks a comment as checked."""
    global CHECKED_COMMENTS
    CHECKED_COMMENTS.add(str(id))
    with open('CHECKED_COMMENTS.txt', 'w') as file:
        for id in CHECKED_COMMENTS:
            file.write(str(id) + '\n')


def load_checked_comments():
    """Loads all comments that have been checked."""
    global CHECKED_COMMENTS
    logging.info('Loading CHECKED_COMMENTS...')
    with open('CHECKED_COMMENTS.txt', 'r') as file:
        CHECKED_COMMENTS = {str(line.rstrip('\n')) for line in file}
    logging.info('Loaded CHECKED_COMMENTS.')
    # logging.info(CHECKED_COMMENTS)


def check_submission(submission):
    """Mark the submission as checked."""
    check_comment("SUBMISSION_" + str(submission.id))


def is_submission_checked(submission):
    """Check if the submission was checked."""
    global CHECKED_COMMENTS
    return "SUBMISSION_" + str(submission.id) in CHECKED_COMMENTS


def parse_submissions(SUBREDDIT):
    """Parses all user-submissions."""
    # FIXME: Also parse submission-text itself.
    logging.info("==================================================")
    logging.info("Parsing submissions on SUBREDDIT: %s" + str(SUBREDDIT))
    for submission in SUBREDDIT.get_hot(limit=25):
        # Also parse the submission text.
        if not is_submission_checked(submission):
            make_reply(submission.selftext, None, submission.id, submission.add_comment)
            check_submission(submission)

        logging.info("Checking SUBMISSION: %r" % submission.id)
        flat_comments = praw.helpers.flatten_tree(submission.comments)
        for comment in flat_comments:
            logging.info(
                'Checking COMMENT: %r in submission %r' % (comment.id, submission.id)
            )
            if str(comment.id) in CHECKED_COMMENTS:
                logging.info("Comment " + comment.id + " already parsed!")
            else:
                logging.info("Parsing comment %r in submission %r" % (comment.id, submission.id))
                make_reply(comment.body, comment.id, comment.id, comment.reply)
    logging.info("".join(("Parsing on SUBREDDIT ", SUBREDDIT, " complete.")))
    logging.info("==================================================")


def make_reply(body, cid, id, reply_func):
    """Makes a reply for the given comment."""
    reply = formulate_reply(body)

    if reply is None:
        logging.info("Empty reply!")
    elif len(reply) > 10:
        # ('--------------------------------------------------')
        logging.info('Outgoing reply to ' + id + ':\n' + reply + FOOTER)
        # print('--------------------------------------------------')
        reply_func(reply + FOOTER)
        # bot_tools.pause(1, 20)
        # print('Continuing to parse submissions...')
    else:
        logging.info("No reply conditions met.")

    if cid is not None:
        check_comment(cid)


def formulate_reply(comment_body):
    """Creates the reply for the given comment."""
    REGEXPS = get_regexps()
    requests = {}
    for name, regexp in REGEXPS.items():
        tofind = regexp.findall(comment_body)
        requests[name] = tofind
    return parse_comment_requests(requests)


def parse_comment_requests(requests):
    """
    Executes the queries and return the
    generated story strings as a single string
    """
    return "".join(_parse_comment_requests(requests))


def _parse_comment_requests(requests):
    sites = get_sites()

    for site, queries in requests.items():
        if queries:
            logging.info("Requests for '%s': %r" % (site, queries))
        for comment in sites[site].from_requests(queries):
            if comment is None:
                continue
            yield str(comment)
