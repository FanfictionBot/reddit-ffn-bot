import time
import re
import sys
import argparse

import praw

from ffn_bot import fanfiction_parser

USER_AGENT = "Python:FanfictionComment:v0.001a (by /u/tusing)"
r = praw.Reddit(USER_AGENT)
DEFAULT_SUBREDDITS = ['HPFanfiction']
SUBREDDIT_LIST = []
CHECKED_COMMENTS = []

#New regex shoul match more possible letter combinations, see creenshot below
#http://prntscr.com/7g0oeq

REGEXPS = {'[Ll][iI][nN][kK][fF]{2}[nN]\((.*?)\)': 'ffn'}
FOOTER = "\n*Read usage tips and tricks  [here](https://github.com/tusing/reddit-ffn-bot/blob/master/README.md). Brought to you by me - /u/tusing's bot, with improvements by /u/MikroMan.*"


def run_forever():
    try:
        main()
    except:
        pause(1, 0)
        run_forever()


def main():
    login_to_reddit()
    load_checked_comments()
    load_subreddits()

    while True:
        for SUBREDDIT in SUBREDDIT_LIST:
            parse_submissions(r.get_subreddit(SUBREDDIT))
            pause(1, 0)


def get_bot_parameters():
    # initialize parser and add options for username and password
    parser = argparse.ArgumentParser()
    parser.add_argument('-u', '--user', help='define Reddit login username')
    parser.add_argument('-p', '--password', help='define Reddit login password')
    parser.add_argument(
        '-s', '--subreddit', help='define target subreddit; can be used with -a')

    #can also add possibility with -s option to aquire comma separated list of subreddits
    #then do: subs = args.subreddit.split(',')
    #and return this list, then append/extend to Subreddit_list or default_subs
    #and possibl transform to set to avoid duplicates.

    parser.add_argument(
        '-d', '--default', action='store_true', help='add default subreddits')

    args = parser.parse_args()

    return {'user': args.user, 'password': args.password, 'subreddit': args.subreddit, 'default': args.default}


def login_to_reddit():
    bot_parameters = get_bot_parameters()
    print("Logging in...")
    r.login(bot_parameters['user'], bot_parameters['password'])
    print("Logged in.")


def load_subreddits():
    global SUBREDDIT_LIST
    user_name, user_pw, user_subreddit, use_default = get_bot_parameters()
    print("Loading subreddits...")
    if use_default is True:
        for subreddit in DEFAULT_SUBREDDITS:
            SUBREDDIT_LIST.append(subreddit)
    if user_subreddit is True:
        SUBREDDIT_LIST.append(user_subreddit)
    if len(SUBREDDIT_LIST) == 0:
        SUBREDDIT_LIST.append('tusingtestfield')
    print("LOADED SUBREDDITS: ", SUBREDDIT_LIST)


def check_comment(id):
    global CHECKED_COMMENTS
    CHECKED_COMMENTS.append(str(id))
    with open('CHECKED_COMMENTS.txt', 'w') as file:
        for id in CHECKED_COMMENTS:
            file.write(str(id) + '\n')


def load_checked_comments():
    global CHECKED_COMMENTS
    print('Loading CHECKED_COMMENTS...')
    with open('CHECKED_COMMENTS.txt', 'r') as file:
        CHECKED_COMMENTS = [str(line.rstrip('\n')) for line in file]
    print('Loaded CHECKED_COMMENTS. Contains:')
    print(CHECKED_COMMENTS)


def parse_submissions(SUBREDDIT):
    print("PARSING SUBMISSIONS ON SUBREDDIT ", SUBREDDIT)
    for submission in SUBREDDIT.get_hot(limit=10):
        print("Checking SUBMISSION: ", submission.id)
        flat_comments = praw.helpers.flatten_tree(submission.comments)
        for comment in flat_comments:
            print('Checking COMMENT: ' + comment.id + ' in submission ' + submission.id)
            if str(comment.id) in CHECKED_COMMENTS:
                print("Comment " + comment.id + " already parsed!")
            else:
                print("Parsing comment ", comment.id)
                make_reply(comment, comment.id)


def make_reply(comment, id):

    reply = formulate_reply(comment.body)

    if reply is None:
        check_comment(comment.id)
        print("Empty reply!")
    elif len(reply) > 10:
        print('Outgoing reply to ' + id + ':\n' + reply + FOOTER)
        comment.reply(reply + FOOTER)
        check_comment(comment.id)
        pause(1, 20)
    else:
        print("No reply conditions met.")
        check_comment(comment.id)


def formulate_reply(comment_body):

    requests = {}
    for expr in REGEXPS.keys():
        tofind = re.findall(expr, comment_body)
        requests[REGEXPS[expr]] = tofind
    print("FINDING: ", requests)
    return parse_comment_requests(requests)


def parse_comment_requests(requests):
    comments_from_sources = []
    ffn_requests = requests['ffn']
    print("FFN requests: ", ffn_requests)
    ffn_comment = fanfiction_parser.ffn_make_from_requests(ffn_requests)
    dlp_comment = ""
    ao3_comment = ""
    return ffn_comment + dlp_comment + ao3_comment


def pause(minutes, seconds):
    print("A countdown timer is beginning. You can skip it with Ctrl-C.")
    try:
        totaltime = minutes * 60 + seconds
        for remaining in range(totaltime, 0, -1):
            sys.stdout.write("\r")
            sys.stdout.write(
                "Paused: {:2d} seconds remaining.".format(remaining))
            sys.stdout.flush()
            time.sleep(1)
        sys.stdout.write("\rComplete!            \n")
    except KeyboardInterrupt:
        sys.stdout.flush()
        time.sleep(1)
        sys.stdout.write("\rCountdown bypassed!            \n")
        pass

