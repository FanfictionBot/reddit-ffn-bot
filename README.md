[![Join the chat at https://gitter.im/tusing/reddit-ffn-bot](https://badges.gitter.im/Join%20Chat.svg)](https://gitter.im/tusing/reddit-ffn-bot?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge)

# FanFiction Bot for Reddit
This bot was made to allow reddit users to automatically get
their responses, requests and promotions linked with the title,
author and metadata of the story.

## Features
* Direct Parsing of Links
* Modification of bot behaviour for the users.
* Support for [fanfiction.net][ffn], [fictionpress.com][fp],
  [hpfanficarchive.com][ffa], [archiveofourown.org][ao3] and
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
    $ sudo apt-get install python3-pip
    $ git clone https://github.com/tusing/reddit-ffn-bot .
    $ pip3 install -r requirements.txt
```

## Starting the bot
Use the following command to start the bot
```
    $ python . -u <USERNAME> -p <PASSWORD> -s <SUBREDDIT/MULTIREDDIT>
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

[github:bleeding]:      https://github.com/tusing/reddit-ffn-bot/tree/bleeding
[github:issues]:        https://github.com/tusing/reddit-ffn-bot/issues
[github:pull-requests]: https://github.com/tusing/reddit-ffn-bot/pulls 
