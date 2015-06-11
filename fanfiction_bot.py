import praw
import time
import pickle
import re
import os
import sys
from fanfiction_backend import Story
from random import randint
from pprint import pprint
from google import search
import argparse


USER_AGENT = "Python:FanfictionComment:v0.001a (by /u/tusing)"
r = praw.Reddit(USER_AGENT)
SUBREDDIT = None
CHECKED_COMMENTS = []


def main():
    # CHECKED_COMMENTS = pickle.load(replies)
    login_to_reddit()

    while True:
        parse_submissions()
        pause(10, 0)


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


def parse_arguments():
    # initialize parser and add options for username and password
    parser = argparse.ArgumentParser()
    parser.add_argument('-u', '--user', help='define Reddit login username')
    parser.add_argument('-p', '--password', help='define Reddit login password')
    parser.add_argument('-s', '--subreddit', help='define target subreddit')

    args = parser.parse_args()

    return args.user, args.password, args.subreddit


def login_to_reddit():
    global SUBREDDIT
    user_name, user_pw, user_subreddit = parse_arguments()

    print("Logging in...")
    r.login(user_name, user_pw)
    print("Logged in.")

    print("Loading subreddit...")
    if user_subreddit is False:
        user_subreddit = 'tusingtestfield'
        SUBREDDIT = r.get_subreddit(user_subreddit)
    else:
        SUBREDDIT = r.get_subreddit(user_subreddit)
    print("Loaded subreddit " + user_subreddit)

    print('Loading CHECKED_COMMENTS...')
    global CHECKED_COMMENTS
    with open('CHECKED_COMMENTS.txt', 'r') as file:
        CHECKED_COMMENTS = [str(line.rstrip('\n')) for line in file]
    print('Loaded CHECKED_COMMENTS.')


def mark_as_done(id):
    global CHECKED_COMMENTS
    CHECKED_COMMENTS.append(str(id))

    with open('CHECKED_COMMENTS.txt', 'w') as file:
        for id in CHECKED_COMMENTS:
            file.write(str(id) + '\n')


def parse_submissions():
    print('CHECKED_COMMENTS contains:')
    print_comments = ""
    for id in CHECKED_COMMENTS:
        print_comments += id
    print(print_comments.replace('\n', ', '))

    for submission in SUBREDDIT.get_hot(limit=10):
        print("Checking SUBMISSION: ", submission.id)
        flat_comments = praw.helpers.flatten_tree(submission.comments)
        for comment in flat_comments:
            print('Checking COMMENT: ' + comment.id + ' in submission ' + submission.id)
            if str(comment.id) in CHECKED_COMMENTS:
                print("Comment " + comment.id + " already parsed!")
            else:
                print("Parsing comment ", comment.id)
                parse_comment(comment, comment.id)
                mark_as_done(comment.id)


def parse_comment(comment, id):
    footer = "\n*Graciously brought to you by me - /u/tusing's bot. Many improvements by /u/MikroMan.*"
    REGEXPS = {'linkffn\((.*?)\)': 'ffn'}
    requested = {}

    contents = comment.body
    for expr in REGEXPS.keys():
        tofind = re.findall(expr, contents)
        requested[REGEXPS[expr]] = tofind
    print("FINDING: ", requested)
    links = ffn_link_finder(requested['ffn'])
    found_ffn = ffn_comment_maker(links)
    if len(found_ffn) > 10:
        print('Outgoing reply to ' + id + ':\n' + found_ffn + footer)
        comment.reply(found_ffn + footer)
        pause(9, 5)  # pause for 9 minutes and 5 seconds before new comment


def ffn_link_finder(fic_names):
    links_found = []
    for fic_name in fic_names:

        # Obfuscation.
        time.sleep(randint(1, 3))
        sleep_milliseconds = randint(500, 3000)
        time.sleep(sleep_milliseconds / 1000)

        search_request = 'site:fanfiction.net/s/ ' + fic_name
        print("SEARCHING: ", search_request)

        search_results = search(search_request, num=1, stop=1)
        link_found = next(search_results)
        links_found.append(link_found)
        print("FOUND: " + link_found)

    return links_found


def ffn_comment_maker(links):
    comment = ''
    for link in links:
        comment += '{0}\n&nbsp;\n\n'.format(ffn_description_maker(link))
    return comment


def ffn_description_maker(link):
    current = Story(link)
    decoded_title = current.title.decode('ascii', errors='replace')
    decoded_author = current.author.decode('ascii', errors='replace')
    decoded_summary = current.summary.decode('ascii', errors='replace')
    decoded_data = current.data.decode('ascii', errors='replace')

    print("Making a description for " + decoded_title)

    # More pythonic string formatting.
    header = '[***{0}***]({1}) by [*{2}*]({3})'.format(decoded_title,
                                                       link, decoded_author, current.authorlink)

    formatted_description = '{0}\n\n>{1}\n\n>{2}\n\n'.format(
        header, decoded_summary, decoded_data)
    print("Description for " + decoded_title + ": \n" + formatted_description)
    return formatted_description

main()
