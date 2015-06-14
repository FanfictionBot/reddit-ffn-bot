import re
import sys
import argparse
import logging
import praw

from ffn_bot import fanfiction_parser
from ffn_bot import ao3
from ffn_bot import bot_tools


__author__ = 'tusing, MikroMan, StuxSoftware'

USER_AGENT = "Python:FanfictionComment:v0.1 (by /u/tusing)"
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

FOOTER = "\n*Read usage tips and tricks  [here](https://github.com/tusing/reddit-ffn-bot/blob/master/README.md).*"


def get_regexps():
    global SITES
    return {site.name: re.compile(site.regex, re.IGNORECASE) for site in SITES}


def get_sites():
    global SITES
    return {site.name: site for site in SITES}


def __main__():
    while True:
        try:
            initialize()
        except:
            logging.error("MAIN: AN EXCEPTION HAS OCCURED!")
            bot_tools.print_exception()
            bot_tools.pause(1, 0)


def initialize():
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

    parser.add_argument(
        '-d', '--default', action='store_true', help='add default subreddits, can be in addition to -s')

    args = parser.parse_args()

    return {'user': args.user, 'password': args.password, 'user_subreddits': args.subreddits, 'default': args.default}


def login_to_reddit(bot_parameters):
    print("Logging in...")
    r.login(bot_parameters['user'], bot_parameters['password'])
    print("Logged in.")


def load_subreddits(bot_parameters):
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


def check_comment(id):
    global CHECKED_COMMENTS
    CHECKED_COMMENTS.add(str(id))
    with open('CHECKED_COMMENTS.txt', 'w') as file:
        for id in CHECKED_COMMENTS:
            file.write(str(id) + '\n')


def load_checked_comments():
    global CHECKED_COMMENTS
    logging.info('Loading CHECKED_COMMENTS...')
    with open('CHECKED_COMMENTS.txt', 'r') as file:
        CHECKED_COMMENTS = {str(line.rstrip('\n')) for line in file}
    print('Loaded CHECKED_COMMENTS.')
    logging.info(CHECKED_COMMENTS)


def parse_submissions(SUBREDDIT):
    print("==================================================")
    print("Parsing submissions on SUBREDDIT", SUBREDDIT)
    for submission in SUBREDDIT.get_hot(limit=25):
        logging.info("Checking SUBMISSION: ", submission.id)
        flat_comments = praw.helpers.flatten_tree(submission.comments)
        for comment in flat_comments:
            logging.info(
                'Checking COMMENT: ' + comment.id + ' in submission ' + submission.id)
            if str(comment.id) in CHECKED_COMMENTS:
                logging.info("Comment " + comment.id + " already parsed!")
            else:
                print("Parsing comment ", comment.id, ' in submission ', submission.id)
                print(comment.body)
                make_reply(comment, comment.id)
    print("Parsing on SUBREDDIT ", SUBREDDIT, " complete.")
    print("==================================================")


def make_reply(comment, id):

    reply = formulate_reply(comment.body)

    if reply is None:
        check_comment(comment.id)
        print("Empty reply!")
    elif len(reply) > 10:
        print('Outgoing reply to ' + id + ':\n' + reply + FOOTER)
        comment.reply(reply + "\n\n" + FOOTER)
        check_comment(comment.id)
        bot_tools.pause(1, 20)
        print('Continuing to parse submissions...')
    else:
        print("No reply conditions met.")
        check_comment(comment.id)


def formulate_reply(comment_body):
    REGEXPS = get_regexps()
    requests = {}
    for name, regexp in REGEXPS.items():
        tofind = regexp.findall(comment_body)
        requests[name] = tofind
    print("FINDING: ", requests)
    return parse_comment_requests(requests)


def parse_comment_requests(requests):
    return "".join(_parse_comment_requests(requests))


def _parse_comment_requests(requests):
    sites = get_sites()

    for site, queries in requests.items():
        print("Requests for '%s': %r" % (site, queries))
        for comment in sites[site].from_requests(queries):
            yield comment

    # ffn_requests = requests['ffn']
    # print("FFN requests: ", ffn_requests)
    # ffn_comment = fanfiction_parser.ffn_make_from_requests(ffn_requests)
    # dlp_comment = ""
    # ao3_comment = ""
    # return ffn_comment + dlp_comment + ao3_comment
