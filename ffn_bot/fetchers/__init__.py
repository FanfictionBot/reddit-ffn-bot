from ffn_bot.fetchers import aff
from ffn_bot.fetchers import ao3
from ffn_bot.fetchers import ffn
from ffn_bot.fetchers import ffa

SITES = [
    aff.AdultFanfiction(),
    ao3.ArchiveOfOurOwn(),
    ffn.FictionPressSite(),
    ffn.FanfictionNetSite(),
    ffa.HPFanfictionArchive(),
]

__all__ = ["SITES"]
