import sys
import logging
import platform
import traceback
import time

from ffn_bot import logger
from ffn_bot.colors import Fore, Back, Style

def safe_int(value, default=None, converter=int):
    """
    Tries to convert the given value to another type.
    If a ValueError is raised, return the specified default value.

    :param value      The value to convert
    :param default    The default value. Defaults to `None`
    :param converter  The function that converts the value. Defaults to `int`
    """

    try:
        return converter(value)
    except ValueError:
        return default

# Waiting for a keypress is platform dependent.
# We will define the function determined by the platform.
if platform.system() == "Windows":
    import msvcrt

    def wait(timeout=1, precision=1):
        """
        Wait for a keypress.

        If `timeout` is 0, the function will wait
        indefinitely.

        :param timeout:   The timeout before the function returns
                          0 means indefinitely.
        :param precision: The time we should be waiting between the
                          polls.
        :returns:  True if at least one key was hit. False otherwise.
        """
        # If we have no timeout given,
        # do not check if a key was hit.
        if timeout == 0:
            msvcrt.getch()
            return True

        # Use a loop so we can exit the function
        # before the timeout has been reached.
        for i in range(int(timeout / precision)):
            time.sleep(precision)

            # Handle all keypresses that have occured
            # in this time.
            kbhit = False
            while msvcrt.kbhit():
                msvcrt.getch()
                kbhit = True

            # If there was at least one keypress,
            # Exit function.
            if kbhit:
                return True

        # If there was no keypress before the timeout
        # return False.
        return False
else:
    def wait(timeout=1, precision=None):
        """
        Wait for a keypress.

        If `timeout` is 0, the function will wait
        indefinitely.

        :param timeout:   The timeout before the function returns
                          0 means indefinitely.
        :param precision: The time we should be waiting between the
                          polls (means nothing for this operating system)
        :returns:  True if at least one key was hit. False otherwise.
        """
        import sys
        import select

        rlist, wlist, xlist = select.select([sys.stdin], [], [], timeout)
        return bool(rlist)


def pause(minutes, seconds):
    """
    Pauses the script for the given amount of time. Skippable by keypress.

    :param minutes:  The amount of minutes that should be waited.
    :param seconds:  The amount of seconds we sould wait.
    """
    print("A countdown timer is beginning. You can skip it by pressing a key.")
    try:
        totaltime = minutes * 60 + seconds
        for remaining in range(totaltime, 0, -1):
            sys.stdout.write("\r")
            sys.stdout.write("Paused: {:2d} seconds remaining.".format(remaining))
            sys.stdout.flush()
            if wait(1):
                output_message = "\rSkipped at " + str(remaining) + " seconds!"
                sys.stdout.write(str.ljust(output_message, 55) + '\n')
                sys.stdout.flush()
                break
        sys.stdout.write(str.ljust("\rComplete!", 55) + '\n')
        sys.stdout.flush()
    except KeyboardInterrupt:
        sys.stdout.flush()
        time.sleep(1)
        sys.stdout.write(str.ljust("\rCountdown bypassed!", 55) + "\n")


def print_exception(etype=None, evalue=None, etb=None):
    """
    Prints the exception. Defaults to the last exception that occured.
    If only `etype` is given, the function will try to extract the
    values from that argument.

    :param etype:  The type of the exception. (optional)
    :param evalue: The exception instance. (optional)
    :param etb:    The traceback. (optional)
    """
    if etype is not None:
        if evalue is None:
            exc_type = type(etype)
            exc_value = etype
            try:
                exc_tb = etype.__traceback__
            except AttributeError:
                raise RuntimeError("Python version too old.")
        else:
            exc_type, exc_value, exc_tb = etype, evalue, etb
    else:
        exc_type, exc_value, exc_traceback = sys.exc_info()

    # Format the exception
    lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
    for line in lines:
       for subline in line.split("\n"):
           logging.error("!! " + subline)
