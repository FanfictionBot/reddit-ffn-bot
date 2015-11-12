import time
import logging
import threading

from praw.errors import InvalidUserPass

from ffn_bot.bot_tools import print_exception

class Authenticator(object):

    def __init__(self, reddit):
        self.reddit = reddit
        self.logger = logging.getLogger("auth")
        self._previous_method = None

    def authenticate(self, settings):
        self.stop()

        self.logger.info("Authenticating with method: " + settings["type"])
        self._previous_method = getattr(
            self, "login_" + settings["type"], self._unknown
        )(settings)

    def stop(self):
        if self._previous_method:
            self.logger.info("Stopping previous authentication method.")
            self._previous_method.stop()

    def _unknown(self, _, settings):
        raise ValueError("Unknown authentication type.")


def authenticator(name):
    def _decorator(cls):
        def runner(self, settings):
            result = cls(self)
            result.login(settings)
            return result
        setattr(Authenticator, "login_"+name, runner)
        return cls
    return _decorator


class BaseAuthenticator(object):

    def __init__(self, authenticator):
        self.reddit = authenticator.reddit
        self.logger = authenticator.logger
        super(BaseAuthenticator, self).__init__()
        self.load()

    def load(self):
        pass

    def login(self, settings):
        pass

    def stop(self):
        pass


@authenticator("password")
class PasswordAuthenticator(BaseAuthenticator):
    def login(self, settings):
        self.logger.warning("Deprecated authentication method.")
        self.logger.warning("Use OAuth2 instead.")
        try:
            self.reddit.login(
                settings["username"],
                settings["password"],

                # We already warn the users that the authentication method
                # is deprecated.
                disable_warning=True
            )
        except InvalidUserPass as e:
            raise ValueError("Invalid login credentials") from e


@authenticator("oauth2")
class OAuthAuthenticator(BaseAuthenticator, threading.Thread):
    def load(self):
        self.stopped = threading.Event()
        self.oauth = None

    def login(self, settings):
        try:
            import OAuth2Util
        except ImportError:
            raise ValueError("praw-oauth2util not installed...")
        self.oauth = OAuth2Util.OAuth2Util(
            self.reddit,
            configfile=settings["config"]
        )
        self.logger.info("Got refresh token...")
        self.oauth.refresh()
        self.refresh_time = settings.get("refresh-time", 45*60)
        self.start()

    def stop(self):
        self.logger.info("Stopping refresh mechanism.")
        self.stopped.set()
        self.join()

    def run(self):
        while not self.stopped.is_set():
            for i in range(self.refresh_time):
                time.sleep(1)
                if self.stopped.is_set():
                    return

            self.logger.info("Refreshing token.")
            self.oauth.refresh()


_authenticator = None


def login_to_reddit(r, settings):
    global _authenticator
    if not _authenticator:
        _authenticator = Authenticator(r)
    try:
        _authenticator.authenticate(settings)
    except ValueError as e:
        logging.critical("Failed to login:")
        logging.critical(str(e))
        return False
    except Exception as e:
        logging.critical("Failed to perform login.")
        print_exception(e)
        return False
    return True
