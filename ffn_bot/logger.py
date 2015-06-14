import sys
import logging

from ffn_bot.colors import Fore, Back, Style

# Configure the root logger.
logging.basicConfig(
    stream=sys.stdout,
    # %(asctime)s %(name)-12s %(levelname)-8s %(message)s
    format="".join([
        # Set colors
        Style.RESET_ALL,
        
        # Time
        # Fore.RED,
        # Style.NORMAL,
        # "[%(asctime)s] ",
        
        Fore.YELLOW,
        "%(name)-12s ",
        
        Fore.CYAN,
        "%(levelname)-8s ",
        
        Fore.RESET,
        Style.BRIGHT,
        "%(message)s",
        
        # Reset everything
        Style.RESET_ALL,
    ]),
    level=logging.DEBUG
)
