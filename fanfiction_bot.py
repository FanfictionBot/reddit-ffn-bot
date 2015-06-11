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
    parser = argparse.ArgumentParser()
    parser.add_argument('-u', '--user',help='define Reddit login username')
    parser.add_argument('-p','--password', help='define Reddit login password')

    args = parser.parse_args()

    return args.user, args.password


def login():
    user_name, user_pw = parse_arguments()
    # Moved name and PW to local to prevent potential hack.

    print("Logging in...")
    r.login(user_name, user_pw)
    global SUBREDDIT
    print("Loading subreddit...")
    SUBREDDIT = r.get_subreddit('HPFanfiction')
    print('Loading DONE...')
    global DONE
    with open('done.txt', 'r') as file:
        DONE = [str(line.rstrip('\n')) for line in file]


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
    REGEXPS = {'linkffn\((.*?)\)': 'ffn'}
    requested = {}
    contents = comment.body
    for expr in REGEXPS.keys():
        tofind = re.findall(expr, contents)
        requested[REGEXPS[expr]] = tofind
    print("FINDING: ", requested)
    links = ffn_linkfinder(requested['ffn'])
    found_ffn = ffn_commentmaker(links)
    footer = "\n*Graciously brought to you by me - /u/tusing's bot.*"
    if len(found_ffn) > 10:
        print('Outgoing reply to ' + id + ':\n' + found_ffn + footer)
        comment.reply(found_ffn + footer)
        pause(9, 5)  # pause for 9 minutes and 5 seconds before new comment


def ffn_linkfinder(ficnames):
    links_found = []
    for ficname in ficnames:
        time.sleep(randint(1, 3))
        search_request = 'site:fanfiction.net/s/ ' + ficname
        print("SEARCHING: ", search_request)
        search_results = search(search_request, num=1, stop=1)
        links_found.append(next(search_results))
    return links_found


def ffn_commentmaker(links):
    comment = ''
    for link in links:
        comment += ffn_descriptionmaker(link)
        comment += '\n&nbsp;\n'
        comment += '\n'
    return comment


def ffn_descriptionmaker(link):
    current = Story(link)
    decodedTitle = current.title.decode('ascii', errors='replace')
    decodedAuthor = current.author.decode('ascii', errors='replace')
    decodedSummary = current.summary.decode('ascii', errors='replace')
    decodedData = current.data.decode('ascii', errors='replace')
    ws = '\n\n '

    header =   '[***{0}***]({1}) '.format(decodedTitle, link)   #'[***' +  decodedTitle + '***]' + '(' + link + ')' + ' '
    header += ' by [*{0}*]({1})'.format(decodedAuthor, current.authorlink) #'[*' + decodedAuthor + '*]' + '(' + current.authorlink + ')'
    summary = '> ' + decodedSummary
    data = '> ' + decodedData
    return '{0} {1} {2} {1} {3} {1}'.format(header, ws, summary, data)

main()
