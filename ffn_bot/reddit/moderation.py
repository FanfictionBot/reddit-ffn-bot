import collections
import logging
import praw
from ffn_bot.reddit.utils import get_full, get_parent, valid_comment


MESSAGES = {
    "AUTH_FAIL": """*Failed to authorize request.*
> The bot was unable to make sure that you are allowed to delete
> the reply.""",

    "NO_AUTH": """*You are not authorized to remove this post.*
> Only the commenter of the original comment can remove a reply.
""",

    "FOOTER": "\n\n**If you still think the request is inappropriate\
, contact a moderator to remove the reply for you.**"
}


def construct_message(id):
    return MESSAGES[id] + MESSAGES["FOOTER"]


class ModerativeCommandsMeta(type):
    def __prepare__(cls, bases, **kwds):
        return collections.OrderedDict()

    def __new__(cls, name, bases, what):
        result = super(ModerativeCommandsMeta, cls).__new__(
            cls, name, bases, what)

        result._commands = getattr(result, "_commands", {}).copy()
        if None in result._commands:
            result._commands[None] = result._commands[None][:]

        for name, value in what.items():
            if hasattr(value, "_commandname"):
                # We may add anti-spam functions into our
                # moderation class.
                if value._commandname is None:
                    if None not in result._commands:
                        result._commands[None] = []
                    result._commands[None].append(value)

                result._commands[value._commandname] = value

        return result


def command(func_or_name, allow_on_force=False):
    def _decorator(func):
        func._commandname = name
        func._on_force = allow_on_force
        return func

    if callable(func_or_name):
        name = func_or_name.__name__
        return _decorator(func_or_name)
    else:
        name = func_or_name
        return _decorator


class ModerativeCommands(object, metaclass=ModerativeCommandsMeta):

    @classmethod
    def get_metavars(cls):
        return tuple((k for k in cls._commands.keys() if k))

    def __init__(self, reddit, commentlist, reply_func, handle):
        self.reddit = reddit
        self.commentlist = commentlist
        self._logger = logging.getLogger("moderation")
        self.reply = reply_func
        self.handle = handle

        self.logger = self._logger

    def handle_moderation(self, comment, markers):
        forced = comment in self.commentlist

        for key, func in self._commands.items():
            if key is None or key in markers:
                if not func._on_force and forced:
                    continue

                self.logger.info("Moderation: " + repr(func))
                logger = logging.getLogger("moderation." + str(key))

                # Make sure we have a list.
                if key is not None:
                    funcs = (func,)
                else:
                    funcs = func

                for func in funcs:
                    # Set logger to method logger.
                    self.logger = logger
                    try:
                        # Execute function
                        result = func(self, comment, markers)
                    except:
                        raise
                    else:
                        if result is not None:
                            return result
                    finally:
                        # Reset logger.
                        self.logger = self._logger
        return True

    @command("parent", allow_on_force=True)
    def on_parent(self, comment, markers):
        self.on_refresh(comment, markers,
                        {"directlinks", "submissionlink"})

    @command("refresh")
    def on_refresh(self, comment, markers, additional=frozenset()):
        self.logger.info("Refresh requested by " + comment.id)

        # Get the full comment or submission
        comment_with_requests = get_full(
            self.reddit, get_parent(self.reddit, comment, True))
        self.logger.info("Refreshing on " + comment_with_requests.fullname)

        if comment_with_requests.author is not None:
            if comment_with_requests.author.name == self.reddit.user.name:
                self.logger.info(
                    "Refresh requested on a bot comment (" + comment_with_requests.id + ").")
                # Retrieve the requesting parent submission or comment
                comment_with_requests = get_full(self.reddit,
                                                 get_parent(
                                                     self.reddit, comment_with_requests, True)
                                                 )

                # If the requesting comment has been deleted, abort
                if not valid_comment(comment_with_requests):
                    self.logger.warning("Parent of bot comment is invalid.")
                    return

                self.logger.info(
                    "Refresh request pushed to parent " + comment_with_requests.fullname)

        self.logger.info(
            "Running refresh on:" + comment_with_requests.fullname)
        if isinstance(comment_with_requests, praw.objects.Comment):
            delete_list = comment_with_requests.replies
        elif isinstance(comment_with_requests, praw.objects.Submission):
            delete_list = comment_with_requests.comments
        else:
            self.logger.warning(
                "Unsupported message type: " + comment_with_requests.fullname)
            return

        if delete_list:
            self.logger.info("Finding replies to delete.")
            for reply in delete_list:
                if valid_comment(reply) and reply.author.name == self.reddit.user.name:
                    self.logger.info("Deleting bot comment " + reply.id)
                    reply.delete()
        else:
            self.logger.info("No bot replies have been deleted. Continuing...")

        # Since parent redirects to this method now, modify the force marker
        # before doing anything.
        parent_markers = {'force'}
        parent_markers |= additional
        self.handle(comment_with_requests, parent_markers)

    @command("delete")
    def on_delete(self, comment, markers):
        self.logger.info("Delete requested by " + comment.id)
        if not comment.is_root:
            parent_comment = get_parent(self.reddit, comment)

            # Make sure we don't delete submissions.
            if not valid_comment(parent_comment):
                self.logger.info("Cannot delete deleted comments :)")
                return

            # Make sure the delete comment is actually authorized
            # We will inform the user that we ignored the comment
            # if we think he was not authorized to use the function.
            #
            # Make sure that the users know that they still have the
            # option of contacting a mod to remove the post.
            grand_parent = get_parent(self.reddit, parent_comment, True)
            if not valid_comment(grand_parent):
                self.logger.info("Cannot verify authorization.")
                self.reply(comment, construct_message("AUTH_FAIL"))
                return

            if grand_parent.author.name != comment.author.name:
                self.logger.info("Comment not authorized.")
                self.reply(comment, construct_message("NO_AUTH"))
                return

            # Make sure we don't try to delete foreign posts.
            if parent_comment.author.name != self.reddit.user.name:
                self.logger.error("Delete requested on non-bot comment.")
                return

            # And only then, we will try to delete the comment.
            self.logger.info("Deleting comment " + parent_comment.id)
            parent_comment.delete()
