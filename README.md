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

```bash
    $ sudo apt-get install git python3.4 lxml libxml2-dev python3.4-dev
    $ sudo apt-get install python-pip
    $ git clone https://github.com/tusing/reddit-ffn-bot .
    $ pip install -r requirements.txt
```

## Set-Up
Change the following setting keys in `settings.yml`:
* `credentials.username`
* `credentials.password`

## Starting the bot
Use the following command to start the bot.
```bash
    $ python . 
```

### OAuth
Please use OAuth for production purposes.

Change to the following configuration in `settings.yml`
```yaml
    credentials:
        type: oauth2
        config: oauth2.ini
```

And change the appropriate values in `oauth2.ini`
More information under
* https://github.com/SmBe19/praw-OAuth2Util/blob/master/OAuth2Util/README.md#config
* https://github.com/reddit/reddit/wiki/OAuth2-Quick-Start-Example
* http://stackoverflow.com/a/24848076

### Memcached
Please note that we recommend using memcached for production
purposes. Set the configuration values in the `cache` section:
```yaml
    cache:
        type: memcached

        # The hosts the bot should connect to (host:port)
        hosts:
        - localhost:11211
        - 123.123.123.123:11211

        # The time in seconds a cache entry should be valid (max)
        expire: 10000
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
