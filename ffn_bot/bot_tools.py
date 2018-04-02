import logging
import platform
import sys
import time
import traceback

# colorama is not installed on
# the system, we will use a fake ANSI-Class that will
# return an empty string on all unknown variables.
try:
    from colorama import init
    from colorama import Fore, Back, Style
except ImportError:
    class FakeANSI(object):

        def __getattr__(self, name):
            try:
                return super(FakeANSI, self).__getattr__(name)
            except AttributeError:
                return ""


    Fore = FakeANSI()
    Back = FakeANSI()
    Style = FakeANSI()
else:
    init()


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
    import os
    import select
    import termios
    import fcntl


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

        # Should be zero, but who knows what OS
        # we're actually in, so... yeah
        fd = sys.stdin.fileno()

        # Yeah, we have to rape the terminal settings
        # before we think of polling the damn thing.
        oldterm = termios.tcgetattr(fd)  # Store old state.
        newattr = termios.tcgetattr(fd)
        newattr[3] = newattr[3] & ~termios.ICANON & ~termios.ECHO
        termios.tcsetattr(fd, termios.TCSANOW, newattr)

        try:
            # Now wait for the user to press a key
            rlist, wlist, xlist = select.select([fd], [], [], timeout)

            # And if the user pressed a key, we have to catch them
            # before another call to this function will not be
            # returning immediately
            if rlist:

                # And now, we have to modify the IO-System Flags.
                # So we have a non-blocking IO and thus can read
                # incoming bytes one by one.
                oldflags = fcntl.fcntl(fd, fcntl.F_GETFL)
                fcntl.fcntl(fd, fcntl.F_SETFL, oldflags | os.O_NONBLOCK)

                # Read incoming bytes until there are no more.
                try:
                    while sys.stdin.read(1):
                        pass

                # Do only catch anything that is not
                # a python system exception like
                # SystemExit and KeyboardInterrupt
                except Exception:
                    pass
                finally:
                    # And reset the IO-System no matter what happens.
                    fcntl.fcntl(fd, fcntl.F_SETFL, oldflags)

                # And while we're at it, yeah I think, we did all
                # just to catch key presses.
                return True

            # And if we did nothing, we just return false.
            return False
        finally:
            # And don't forget resetting the terminal.
            termios.tcsetattr(fd, termios.TCSAFLUSH, oldterm)


def pause(minutes, seconds):
    """
    Pauses the script for the given amount of time. Skippable by keypress.

    :param minutes:  The amount of minutes that should be waited.
    :param seconds:  The amount of seconds we sould wait.
    """
    print("A countdown timer is beginning. You can skip it by pressing a key.")
    totaltime = minutes * 60 + seconds
    for remaining in range(totaltime, 0, -1):
        sys.stdout.write("\r")
        sys.stdout.write("Paused: {:2d} seconds remaining.".format(remaining))
        sys.stdout.flush()
        if wait(1):
            output_message = "\rSkipped at " + str(remaining) + " seconds!"
            sys.stdout.write(str.ljust(output_message, 55) + '\n')
            break
    sys.stdout.write(str.ljust("\rComplete!", 55) + '\n')


def print_exception(etype=None, evalue=None, etb=None, level=logging.ERROR):
    """
    Prints the exception. Defaults to the last exception that occured.
    If only `etype` is given, the function will try to extract the
    values from that argument.

    :param etype:  The type of the exception. (optional)
    :param evalue: The exception instance. (optional)
    :param etb:    The traceback. (optional)
    """
    # Try to parse the parameters.
    print(Fore.RED)
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
        exc_type, exc_value, exc_tb = sys.exc_info()

    # Format the exception
    lines = traceback.format_exception(exc_type, exc_value, exc_tb)
    logging.log(level, ''.join('!! ' + line for line in lines))
    print(Style.RESET_ALL)
