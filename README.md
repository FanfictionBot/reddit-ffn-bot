[![Join the chat at https://gitter.im/tusing/reddit-ffn-bot](https://badges.gitter.im/Join%20Chat.svg)](https://gitter.im/tusing/reddit-ffn-bot?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge)

# FanFiction Bot for Reddit
This bot was made to allow reddit users to automatically get
their responses, requests and promotions linked with the title,
author and metadata of the story.

## Features
* Direct Parsing of Links
* Modification of bot behaviour for the users.
* Support for [fanfiction.net][ffn], [fictionpress.com][fp],
  [hpfanficarchive.com][ffa], [archiveofourown.org][ao3], [siye.co.uk][siye] and
  [adultfanfiction.com][aff]

## Deployment and Installation
If you want to run your own bot or contribute to this project, make sure
you have the following dependencies installed on your machine:

* Python 3.4 or newer

Install bot as follows:
Adapt the commands for your linux distribution
We assume Ubuntu 14.04 and you are inside your desired installation
directory.

```
    $ sudo apt-get install git python3.4 lxml libxml2-dev python3.4-dev
    $ sudo apt-get install python-pip
    $ git clone https://github.com/tusing/reddit-ffn-bot .
    $ pip install -r requirements.txt
```


## Configuring the bot
On your Reddit account, create an app (Preferences > Apps > Create Another App). Enter `https://github.com/tusing/reddit-ffn-bot/wiki/Usage` as the *about url* and `http://127.0.0.1:65010/authorize_callback` as the *redirect uri*. Hit create.

The value under *personal use script* is your client ID; the value next to *secret* is your client secret. Open up `config.ini` and replace the `[REDACTED]`s with the appropriate values (including your own username and password).

Replace the `subreddits` value with a comma-separated list of the subreddits you'd like to run the bot on.


## Starting the bot
Use the following command to start the bot
```
    $ python . -d
```

Advanced usage:

```
usage: . [-h] [-s SUBREDDITS] [-d] [-l] [-v VERBOSITY] [-c CONFIG]

optional arguments:
  -h, --help            show this help message and exit
  -s SUBREDDITS, --subreddits SUBREDDITS
                        define target subreddits; separate with commas
  -d, --default         add config file subreddits, can be in addition to -s
  -l, --dry             do not send comments.
  -v VERBOSITY, --verbosity VERBOSITY
                        The default log level. Using python level states.
  -c CONFIG, --config CONFIG
                        The location of your config.ini.
```


## Contributing
We happily accept contributions. Please note, that we only accept pull
requests into the [bleeding][github:bleeding]-branch.
You can find our issue page here: [Issues][github:issues]
You can find our pull request page here: [Pull Requests][github:pull-requests]


[ffn]: https://www.fanfiction.net/
[fp]:  https://www.fictionpress.com/
[ffa]: http://hpfanficarchive.com/
[ao3]: http://archiveofown.org/
[aff]: http://www.adultfanfiction.net/
[siye]: http://www.siye.co.uk/

[github:bleeding]:      https://github.com/tusing/reddit-ffn-bot/tree/bleeding
[github:issues]:        https://github.com/tusing/reddit-ffn-bot/issues
[github:pull-requests]: https://github.com/tusing/reddit-ffn-bot/pulls 
