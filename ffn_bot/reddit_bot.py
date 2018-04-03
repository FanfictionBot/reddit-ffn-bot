import argparse
import configparser
import datetime
import logging
import re
import sys
import time

import praw
from praw.models import Submission

from ffn_bot import bot_tools
from ffn_bot.commentparser import StoryLimitExceeded
from ffn_bot.commentparser import formulate_reply, parse_context_markers
from ffn_bot.reddit_markdown import remove_superscript
from ffn_bot.state import Application


def run_forever():
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
            bot_tools.print_exception()
            bot_tools.pause(0, 10)


def load_config():
    global config, cli_args, r
    global USER_AGENT, DEFAULT_SUBREDDITS, SUBREDDIT_LIST, FOOTER, APPLICATION, \
        COUNT_REPLIES, COUNT_REPLIES_LIMIT, TIME_TO_RESET, TIME_SINCE_RESET, DRY_RUN, \
        BOT_USERNAME, LAST_REPLY_TIME
    global __author__, __version__

    config = configparser.ConfigParser()
    cli_args = get_cli_args()
    config.read(cli_args['config_loc'])

    __author__ = config['Metadata']['authors']
    __version__ = config['Metadata']['version']
    USER_AGENT = config['Metadata']['user_agent']
    BOT_USERNAME = config['Oauth']['username']
    SUBREDDIT_LIST = set()
    DEFAULT_SUBREDDITS = config['Reddit']['subreddits'].split(',')
    FOOTER = config['Reddit']['footer']
    COUNT_REPLIES = {}  # Count replies per user
    COUNT_REPLIES_LIMIT = int(config['Reddit']['replies_limit'])
    TIME_TO_RESET = int(config['Reddit']['replies_reset'])
    TIME_SINCE_RESET = time.time()  # Time since the last dictionary reset
    APPLICATION = Application()

    DRY_RUN = bool(cli_args["dry"])
    if DRY_RUN:
        logging.warning("Dry run enabled. No comment will be sent.")

    level = getattr(logging, cli_args["verbosity"].upper())
    logging.getLogger().setLevel(level)

    r = get_authenticated_instance()
    LAST_REPLY_TIME = last_comment_time()


def get_authenticated_instance():
    return praw.Reddit(
        client_id=config['Oauth']['client_id'],
        client_secret=config['Oauth']['client_secret'],
        user_agent=config['Oauth']['user_agent'],
        username=config['Oauth']['username'],
        password=config['Oauth']['password']
    )


def main():
    """Basic main function."""
    load_config()
    Application.reset()
    load_subreddits()
    stream_strategy()
    sys.exit()


def get_cli_args():
    """Parse the command-line arguments."""
    # initialize parser and add options for username and password
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-s', '--subreddits',
        help='define target subreddits; separate with commas')

    parser.add_argument(
        '-d', '--default',
        action='store_true',
        help='add config file subreddits, can be in addition to -s')

    parser.add_argument(
        '-l', '--dry',
        action='store_true',
        help="do not send comments.")

    parser.add_argument(
        "-v", "--verbosity",
        default="INFO",
        help="The default log level. Using python level states.")

    parser.add_argument(
        "-c", "--config",
        default="config.ini",
        help="The location of your config.ini."
    )

    args = parser.parse_args()

    return {
        'user_subreddits': args.subreddits,
        'default': args.default,
        'dry': args.dry,
        'verbosity': args.verbosity,
        'config_loc': args.config
    }


def load_subreddits():
    """Loads the subreddits this bot operates on."""
    global SUBREDDIT_LIST
    logging.info("Loading subreddits...")

    if cli_args['default'] is True:
        logging.info("Adding default subreddits: {0}".format(DEFAULT_SUBREDDITS))
        for subreddit in DEFAULT_SUBREDDITS:
            SUBREDDIT_LIST.add(subreddit)

    if cli_args['user_subreddits'] is not None:
        user_subreddits = cli_args['user_subreddits'].split(',')
        logging.info("Adding user subreddits: {0}".format(user_subreddits))
        for subreddit in user_subreddits:
            SUBREDDIT_LIST.add(subreddit)

    if len(SUBREDDIT_LIST) == 0:
        logging.fatal("No subreddits specified.")
    logging.info("All loaded subreddits: {0}".format(SUBREDDIT_LIST))


def last_comment_time():
    try:
        return time_created(r.redditor(BOT_USERNAME).comments.new(limit=1).next())
    except Exception as e:
        print(e)
        logging.fatal("Could not retrieve last bot comment! Please make a comment.")
        return datetime.datetime.min


def handle_submission(submission, markers=set()):
    logging.info("Handling new submission: {0}".format(submission.permalink))
    if ("ignore" not in markers) or ("force" in markers):
        try:
            parse_submission_text(submission, markers)
        except Exception as e:
            logging.error(e)


def handle_message(message, markers=set()):
    global COUNT_REPLIES, TIME_SINCE_RESET, TIME_TO_RESET, COUNT_REPLIES_LIMIT
    """What we're using to handle direct messages."""

    logging.info("Handling new message: {0}".format(message.id))

    markers |= parse_context_markers(message.body)
    # Mark message as read here so we don't loop over it in case of error.
    message.mark_read()

    # Check for message validity.
    try:
        if message.submission is not None:
            logging.info("Parsing message belonging to a submission!")
            return
    except AttributeError:
        pass

    # If enough time has elapsed, reset COUNT_REPLIES to an empty dict.
    if time.time() - TIME_SINCE_RESET >= TIME_TO_RESET:
        COUNT_REPLIES = {}

    # Count the number of requests in the body of the message, of format link...(...;...;...)
    request_count = message.body.count('link') + message.body.count(';')
    body = message.body

    sub_recs = None
    if 'linksub(' in body:
        sub_recs = get_submission_recommendations(body)
        markers.add('slim')

    # If the message author can not be found in the dict, add them.
    COUNT_REPLIES.setdefault(message.author.name, request_count)

    # Print a summary of the user's statistics.
    logging.info("{0} has requested {1} fics with {2} remaining requests for the next {3} seconds.".format(
        message.author.name, request_count, COUNT_REPLIES_LIMIT - COUNT_REPLIES[message.author.name],
                                            TIME_TO_RESET - (time.time() - TIME_SINCE_RESET)))

    # Block the request if the user has exceeded their quota of replies.
    if COUNT_REPLIES[message.author.name] + request_count > COUNT_REPLIES_LIMIT:
        logging.error("{0} has exceeded their available replies.", message.author.name)
        return

    # Otherwise, add the number of requests to the user's total number of requests.
    COUNT_REPLIES[message.author.name] += request_count

    # Print the current state of COUNT_REPLIES.
    logging.debug("The current state of DM requests: {0}".format(COUNT_REPLIES))

    # Make the reply and return.
    make_reply(body, message, markers=markers, sub_recs=sub_recs)
    return


def parent_handler(comment):
    if comment.is_root:
        item = comment.submission
    else:
        item = r.comment(id=comment.parent_id)
    handle(item, {"directlinks", "submissionlink", "force"})


def _refresh_get_requests_comment(comment):
    # Get the full comment or submission
    obj_with_requests = comment.parent()
    if not repliable(obj_with_requests) or obj_with_requests.author is None:
        logging.info("(Refresh) Parent of {0} is not repliable!".format(comment))
        return None
    if obj_with_requests.author.name == BOT_USERNAME:  # parent of bot comment has requests
        obj_with_requests = obj_with_requests.parent()
    logging.info("(Refresh) Refresh requested on comment {0}".format(obj_with_requests))
    return obj_with_requests


def _refresh_get_comments_to_delete(obj_with_requests):
    # Get our previous replies to a comment or submission with requests.
    logging.info("(Refresh) Finding bot replies of {0} to delete.".format(obj_with_requests.id))
    unfiltered_delete_list, delete_list = [], []

    if is_comment(obj_with_requests):
        obj_with_requests.refresh()
        unfiltered_delete_list = obj_with_requests.replies
    elif is_submission(obj_with_requests):
        unfiltered_delete_list = obj_with_requests.comments

    if unfiltered_delete_list is None:
        return []

    for comment in unfiltered_delete_list.list():
        if comment.author is not None and comment.author.name == BOT_USERNAME:
            delete_list.append(comment)
    logging.info("Deleting bot comments: {0}".format(delete_list))
    return delete_list


def _refresh_delete_comments(delete_list):
    for reply in delete_list:
        if repliable(reply) and reply.author.name == BOT_USERNAME:
            logging.info("(Refresh) Deleting bot comment {0}".format(reply.id))
            reply.delete()


def refresh_handler(comment):
    logging.info("(Refresh) Refresh requested by {0}".format(comment.id))

    obj_with_requests = _refresh_get_requests_comment(comment)
    if not repliable(obj_with_requests):
        logging.error("(Refresh) Refresh request on {0} is invalid.".format(comment.id))
        return

    delete_list = _refresh_get_comments_to_delete(obj_with_requests)
    _refresh_delete_comments(delete_list)

    logging.info("(Refresh) Re-handling {0}".format(obj_with_requests.id))
    handle(obj_with_requests, set(["force"]))
    return


def handle_comment(comment, extra_markers=set()):
    logging.info("Handling new comment: {0}".format(getattr(comment, 'permalink', comment)))

    markers = parse_context_markers(comment.body)
    markers |= extra_markers

    if "ignore" in markers:
        logging.info("Ignoring {0}".format(comment.id))
        return

    if "parent" in markers:
        parent_handler(comment)

    if "refresh" in markers:
        refresh_handler(comment)

    body = comment.body
    sub_recs = None
    if 'linksub(' in body:
        sub_recs = get_submission_recommendations(body)
        markers.add('slim')

    try:
        make_reply(body, comment, markers, sub_recs=sub_recs)
    except Exception as e:
        logging.error(e)


def _single_submission_recommendations(submission_id):  # Get the full text for one submission
    # Get the submission's subreddit. It must be a subreddit the bot runs on.
    submission = r.submission(id=submission_id)
    subreddit_name = submission.subreddit.display_name
    if subreddit_name.lower() in [subreddit.lower() for subreddit in SUBREDDIT_LIST]:
        # Return a list of all bot comments in this submission.
        return [comment.body for comment in submission.comments.list()
                if repliable(comment) and comment.author is not None and comment.author.name == BOT_USERNAME]
    else:
        logging.error("(Submission Rec.) Received request to parse invalid submission in /r/" + subreddit_name)
        return []


def get_submission_recommendations(request_body):
    """
    Recommend multiple submissions, using linksub(...)
    Output: A slim-ified version of bot recommendations in the requested threads.
    """
    sub_ids = []  # A list of all requested submission IDs.

    # Capture everything inside linksub(...)
    sub_requests = re.findall('linksub\((.*)\)', request_body)

    for sub_request in sub_requests:  # For every linksub(...),
        # Add the submission ID for every Reddit thread linked, and
        sub_ids += re.findall('redd\.it\/(\S{6})', sub_request)
        sub_ids += re.findall('\/comments\/(\S{6})', sub_request)
        # Add the submission ID if it is explicitly defined.
        sub_request = sub_request.replace(" ", "")  # Remove whitespace
        sub_ids += [sub_id for sub_id in sub_request.split(';') if len(sub_id) == 6]

    logging.info("(Submission Rec.) Handling the following submission IDs: {0}".format(" ".join(sub_ids)))
    replies = []  # A list of bot replies.

    # We build replies[] by calling single_sub_reccomendations on every requested submission.
    for sub_id in sub_ids:
        try:
            reply = _single_submission_recommendations(sub_id)
            replies.append("\n ".join(reply))
            logging.info("(Submission Rec.) Handled submission ID: {0}".format(str(sub_id)))
        except Exception as e:
            logging.error("(Submission Rec.) Failed to get sub recommendations for sub_id " + str(sub_id))
            logging.error(e)

    all_recommended_stories = []
    for bot_comment in replies:
        if 'p0ody-files' in bot_comment:  # Download site moved to new domain.
            bot_comment = bot_comment.replace('p0ody-files', 'ff2ebook')
            bot_comment = bot_comment.replace('ff_to_ebook', 'old')
        all_recommended_stories += slimify_comment(bot_comment)
    return all_recommended_stories


def slimify_comment(bot_comment):
    """
    Slims down a bot comment into essential information: fic name, author, and description.
    Returns a list of stories.
    TODO: Find a less hacky way to do this.
    """
    find_key = lambda slim_story: re.findall('(\[(\ |\S)+\) by)', slim_story)[0][0]
    if 'slim!FanfictionBot' in bot_comment:
        slimmed_stories = [story[0] for story in re.findall('((\n(.+)by(.+)(\s|\S)+?)\n+\>(\ |\S)+\n)', bot_comment)]
        slimmed_stories_dict = {}
        for story in slimmed_stories:
            try:
                slimmed_stories_dict[find_key(story)] = story
            except:
                pass
        slimmed_stories = slimmed_stories_dict
    else:
        all_metadata = re.findall('(\^(\s|\S)*?\-{3})', bot_comment)  # Get metadata
        titles_authors = re.findall('((\n(.+)by(.+))\n+\>)', bot_comment)
        titles_authors = [title_author[1] for title_author in titles_authors]
        summaries = re.findall('(\>(.*))\n+\^', bot_comment)
        summaries = [summary[0] for summary in summaries]
        wordcounts = re.findall('(Word(\D)+((\d{1,3})+(,|\d{1,3})+)+)', str(all_metadata))
        wordcounts = [wordcount[2] for wordcount in wordcounts]
        downloads = [re.findall(r"(\*Download\*([^\\]*))", str(story_metadata)) for story_metadata in all_metadata]
        downloads_fixed = []  # Not all sites have downloads. We'll take care of this:
        for download in downloads:
            try:
                downloads_fixed.append(download[0][0])
            except:
                downloads_fixed.append("No download available)")

        slimmed_stories = {}
        for i in range(len(all_metadata)):
            complete = ''
            if str(all_metadata[i]).__contains__('*Status*: Complete'):
                complete = ', complete'
            story = '\n\n' + titles_authors[i]
            story += ' (' + wordcounts[i] + ' words' + complete + '; ' + downloads_fixed[i] + ')'
            story += '\n\n' + summaries[i] + '\n\n'
            story = story.replace('\\n', '\n')
            story = story.replace('---', '')
            story = remove_superscript(story)
            try:
                slimmed_stories.update({find_key(story): story})
            except:
                pass
    return list(slimmed_stories.values())


def is_comment(obj):
    return isinstance(obj, praw.models.Comment)


def is_submission(obj):
    if isinstance(obj, praw.models.Submission):
        try:
            return True
        except:
            logging.info("Submission {0} has no selftext".format(obj.id))
    return False


def is_message(obj):
    return isinstance(obj, praw.models.Message)


def time_created(obj):
    return datetime.datetime.fromtimestamp(obj.created)


def repliable(obj):
    """
    Checks if valid comment or submission.
    """

    if is_comment(obj) or is_message(obj) or is_submission(obj):
        return True

    logging.error("Found invalid object ".format(obj))
    return False


def handle(obj, markers=set()):
    if not repliable(obj):
        return
    logging.info("Handling object {0}".format(obj.id))

    if ("refresh" not in markers and "force" not in markers) and \
            (time_created(obj) < LAST_REPLY_TIME):
        logging.info("Skipping object " + obj.id + " - object too old!")
        return False

    if is_submission(obj):
        handle_submission(obj, set(markers))
    elif is_comment(obj):
        handle_comment(obj, set(markers))
    else:
        handle_message(obj, set(markers))


def stream_handler(queue, iterator, handler):
    def _raise(exc):
        raise exc

    try:
        for post in iterator:
            if post is not None:
                logging.info("Queueing Post: " + str(post) + '\n')
                queue.put_nowait((handler, post))
    except BaseException as e:
        # Send the actual exception to the main thread
        queue.put_nowait((_raise, e))


def post_receiver(queue):
    while True:
        handler, post = queue.get()
        handler(post)


def stream_strategy():
    from queue import Queue
    from threading import Thread

    post_queue = Queue()
    threads = []
    multireddit = "+".join(SUBREDDIT_LIST)

    threads.append(Thread(target=lambda: stream_handler(
        post_queue,
        r.subreddit(multireddit).stream.comments(pause_after=0),
        handle)))
    threads.append(Thread(target=lambda: stream_handler(
        post_queue,
        r.subreddit(multireddit).stream.submissions(pause_after=0),
        handle)))
    threads.append(Thread(target=lambda: stream_handler(
        post_queue,
        r.inbox.stream(pause_after=0),
        handle)))

    for thread in threads:
        thread.daemon = True
        thread.start()

    while True:
        try:
            post_receiver(post_queue)
        except Exception as e:
            for thread in threads:
                if not thread.isAlive():
                    raise Exception("Streaming thread dead! Are you logged in correctly?")
            bot_tools.print_exception(e)


def parse_submission_text(submission, markers):
    body = submission.selftext

    markers |= parse_context_markers(body)

    additions = []

    sub_recs = None
    if 'linksub(' in body:
        sub_recs = get_submission_recommendations(body)
        markers.add('slim')

    make_reply(
        body, submission,
        markers, additions, sub_recs=sub_recs)


def make_reply(body, obj, markers=None, additions=(), sub_recs=None):
    """Makes a reply for the given comment."""
    id = obj.id

    def send_reply(message):
        obj.reply(message)
        bot_tools.pause(0, 10)

    try:
        reply = list(formulate_reply(body, markers, additions))
    except StoryLimitExceeded:
        if not DRY_RUN:
            send_reply("You requested too many fics.\n"
                       "\nWe allow a maximum of {0} stories".format(COUNT_REPLIES_LIMIT))
        logging.info("{0} exceeded story limit.".format(id))
        return

    logging.info("Markers on reply to {0} consist of {1}".format(id, markers))

    raw_reply = "".join(reply)
    if 'slim' not in markers and len(raw_reply) > 0:
        logging.info("Writing reply to {0} ({1} characters in {2} messages)".format(id, len(raw_reply), len(reply)))
        # Do not send the comment.
        if not DRY_RUN:
            for part in reply:
                send_reply(part + FOOTER)

    elif 'slim' in markers and (len(raw_reply) > 0 or sum([len(rec) for rec in sub_recs]) > 0):
        # This is CRITICAL until we find a cleaner way to do this. slim!FanfictionBot is to be used
        # when parsing threads that already have slim stories.
        slim_footer = "\n\n---\n\n*slim!{0}*^({1})".format(BOT_USERNAME, __version__)
        slim_stories = []
        # Submission recs (if they exist) are already slimmed.
        if sub_recs is not None:
            slim_stories += sub_recs
            slim_footer += " Note that some story data has been sourced from older threads, and may be out of date."
        slim_stories += slimify_comment(raw_reply)

        # Deal with any remaining duplicates.
        find_key = lambda slim_story: re.findall('(\[(\ |\S)+\) by)', slim_story)[0][0]
        slim_stories = list({find_key(story): story for story in slim_stories}.values())

        total_character_count = sum([len(story) for story in slim_stories])
        logging.info("Writing reply to {0} ({1} characters in {2} messages)".format(
            id, total_character_count, total_character_count / (10000 - len(slim_footer))
        ))

        current_reply = []
        while len(slim_stories) is not 0:  # We use slim_stories as a queue.
            current_story = slim_stories.pop(0)
            # Comments can be up to 10,000 characters:
            if sum([len(story) for story in current_reply]) + len(current_story) > 10000 - len(slim_footer):
                send_reply("".join(current_reply) + slim_footer)
                current_reply = []
            else:
                current_reply += current_story
        if len(current_reply) is not 0:
            send_reply("".join(current_reply) + slim_footer)
    else:
        logging.info("No reply conditions met.")
    logging.info('Continuing to parse submissions...')
