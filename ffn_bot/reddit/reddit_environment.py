from collections import OrderedDict

from ffn_bot.environment import BotEnvironment
from ffn_bot.reddit import reddit_markdown


class RedditBotEnvironment(BotEnvironment):

    def __init__(self, tracker):
        self.tracker = tracker

    def stats(self, story, markers):
        if "nostats" in markers or "force" in markers:
            return

        self.tracker.update_stats(story)

    def to_string(self, story, markers):
        """Generates the response string."""
        result = ["\n\n"]
        result.append(
            reddit_markdown.link(
                reddit_markdown.bold(
                    reddit_markdown.italics(
                        reddit_markdown.escape(story.get_title())
                    )
                ), reddit_markdown.escape(story.get_url())
            ) + " by " +
            reddit_markdown.link(
                reddit_markdown.italics(
                    reddit_markdown.escape(story.get_author())
                ), reddit_markdown.escape(story.get_author_link())
            )
        )

        result.append("\n\n")
        result.extend(
            reddit_markdown.quote(
                reddit_markdown.escape(story.get_summary())
            ).split("\n")
        )

        result.append("")
        _lnks = []
        result.append(
            reddit_markdown.exponentiate(self.format_stats(story, _lnks))
        )
        for name, link in _lnks:
            result.append("[%s:%s]: %s" % (str(id(story)), name, link))

        result.append("\n\n" + reddit_markdown.linebreak + "\n\n")

        return "\n".join(result)

    def format_stats(self, story, links):
        stats = OrderedDict()
        site = story.get_site()
        if site is not None:
            _site = iter(site)
            site = "[" + next(_site) + "][" + str(id(story)) + ":site]"
            links.append(("site", next(_site)))
            stats["Site"] = site

        for k, v in story.get_stats().items():
            stats[self.super_escape(k)] = self.super_escape(v)

        res = []
        for key, value in stats.items():
            res.append(reddit_markdown.italics(key) + ": " + value)

        download = story.get_download()
        if download is not None:
            res.append("*Download*: [EPUB][%s:epub]" % (str(id(story))))
            links.append(("epub", download))
        return (" " + reddit_markdown.bold("|") + " ").join(res)

    @staticmethod
    def super_escape(string):
        string = str(string)
        for c in "([{":
            string = string.replace(c, "<")
        for c in ")]}":
            string = string.replace(c, ">")
        return string
        pass
