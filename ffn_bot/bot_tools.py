import sys
import logging
import platform
import traceback
import time


if platform.system() == "Windows":
    def wait(timeout=1):
        import msvcrt
        time.sleep(timeout)
        if msvcrt.kbhit():
            msvcrt.getch()
            return True
        return False
else:
    def wait(timeout=1):
        import sys
        import select
        rlist, wlist, xlist = select.select([sys.stdin], [], [], timeout)
        return bool(rlist)


def pause(minutes, seconds):
    print("A countdown timer is beginning. You can skip it by pressing a key.")
    try:
        totaltime = minutes * 60 + seconds
        for remaining in range(totaltime, 0, -1):
            sys.stdout.write("\r")
            sys.stdout.write(
                "Paused: {:2d} seconds remaining.".format(remaining))
            sys.stdout.flush()
            if wait(1):
                output_message = "\rSkipped at " + str(remaining) + " seconds!        \n"
                sys.stdout.write(output_message)
                break
        sys.stdout.write("\rComplete!                                                 \n")
    except KeyboardInterrupt:
        sys.stdout.flush()
        time.sleep(1)
        sys.stdout.write("\rCountdown bypassed!            \n")
        pass


def print_exception():
    exc_type, exc_value, exc_traceback = sys.exc_info()
    lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
    logging.error(''.join('!! ' + line for line in lines))
