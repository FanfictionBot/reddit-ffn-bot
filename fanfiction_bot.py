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
global DONE
DONE = []


def main():
    # DONE = pickle.load(replies)
    login()

    while True:
        parse_submissions()
        pause(30, 0)


def pause(minutes, seconds):
    totaltime = minutes * 60 + seconds
    for remaining in range(totaltime, 0, -1):
        sys.stdout.write("\r")
        sys.stdout.write("Paused: {:2d} seconds remaining.".format(remaining))
        sys.stdout.flush()
        time.sleep(1)
    sys.stdout.write("\rComplete!            \n")


def parse_arguments():
    #initialize parser and add options for username and password
    parser = argparse.ArgumentParser()
    parser.add_argument('-u', '--user',help='define Reddit login username')
    parser.add_argument('-p','--password', help='define Reddit login password')

    args = parser.parse_args()

    return args.user, args.password


def login():
    global SUBREDDIT

    user_name, user_pw = parse_arguments()
    print("Logging in...")
    r.login(user_name, user_pw)

    print("Loading subreddit...")
    SUBREDDIT = r.get_subreddit('HPFanfiction')
    print('Loading DONE...')

    with open('done.txt', 'r') as file:
        DONE = [str(line.rstrip('\n')) for line in file]

 #Mark what as done? add more descriptive method name?
def markdone(id):
    DONE.append(str(id))

    with open('done.txt', 'w') as file:
        for id in DONE:
            file.write(str(id) + '\n')


def parse_submissions():
    print('DONE contains:')
    for id in DONE:
        print(id)
    for submission in SUBREDDIT.get_hot(limit=10):
        print("Checking SUBMISSION: ", submission.id)
        flat_comments = praw.helpers.flatten_tree(submission.comments)
        for comment in flat_comments:
            print('Checking COMMENT: ' + comment.id + ' in submission ' + submission.id)
            if str(comment.id) in DONE:
                print("Comment " + comment.id + " already parsed!")
            else:
                print("Parsing comment ", comment.id)
                parse_comment(comment, comment.id)
                markdone(comment.id)


def parse_comment(comment, id):
    footer = "\n*Graciously brought to you by me - /u/tusing's bot.*"
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
        time.sleep(randint(1, 3))

        search_request = 'site:fanfiction.net/s/ ' + fic_name
        print("SEARCHING: ", search_request)

        search_results = search(search_request, num=1, stop=1)
        links_found.append(next(search_results))

    return links_found


def ffn_comment_maker(links):
    comment = ''
    for link in links:
        comment = '{0}\n&nbsp;\n\n'.format(ffn_description_maker(link))
    return comment


def ffn_description_maker(link):
    current = Story(link)

    decoded_title = current.title.decode('ascii', errors='replace')
    decoded_author = current.author.decode('ascii', errors='replace')
    decoded_summary = current.summary.decode('ascii', errors='replace')
    decoded_data = current.data.decode('ascii', errors='replace')

    #more pythonic string formatting
    header =   '[***{0}***]({1}) by [*{2}*]({3})'.format(decoded_title, link, decoded_author, current.authorlink)
     #'[***' +  decodedTitle + '***]' + '(' + link + ')' + ' '
    #'[*' + decodedAuthor + '*]' + '(' + current.authorlink + ')'

    return '{0}\n\n>{1}\n\n>{1}\n\n'.format(header, decoded_summary, decoded_data)

main()
