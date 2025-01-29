# Lingua Libre Bot
<a href="https://commons.wikimedia.org/wiki/File:Lingua_Libre_Bot_icon.svg" target="_blank"><img src="https://upload.wikimedia.org/wikipedia/commons/e/e3/Lingua_Libre_Bot_icon.svg" height="250"/></a>

This is the source code of [Lingua Libre Bot](https://meta.wikimedia.org/wiki/User:Lingua_Libre_Bot), whose goal is to ease the reuse of all the records made on [Lingua Libre](https://lingualibre.org) on as much wikis as possible.

## Wikimedia coverage
See [CentralAuth](https://meta.wikimedia.org/wiki/Special:CentralAuth/Lingua_Libre_Bot).
* Wikidata
* Wikidata Lexemes
* French Wiktionary
* Kurdish Wiktionary
* Occitan Wiktionary
* Odia Wiktionary
* Shawiya Wiktionary

## Operational documentation

### Dependencies
* Python 3.6
* wikitextparser (latest)
* requests (latest)
* argparse (latest)
* uuid (latest)
* backoff (latest)

### Installation

```
pip install -r requirements.txt     # Install packages
cp config.ini.sample config.ini     # Copy the configuration file
vi config.ini                       # Edit it with your information
```

### Usage

```
usage: llbot.py {simple, live} [-h] [--dryrun] [--wiki WIKI]

Reuse records made on Lingua Libre on some wikis.

optional arguments:
  -h, --help            show this help message and exit
  --dryrun              run without applying any changes to the wiki
  --wiki {wikidatawiki,frwiktionary}
                        run only on the selected wiki
  
simple mode
  --item ITEM           run only on the given lingualibre item
  --startdate STARTDATE from which timestamp to start
  --enddate ENDDATE     at which timestamp to end
  --user USER           run only on records from the given user
  --lang LANG           run only on records from the given language,
                        identified by its lingua libre qid
  --langiso LANGISO     run only on records from the given language,
                        identified by its iso 693-3 code
  --langwm LANGWM       run only on records from the given language,
                        identified by its wikimedia language code
  
live mode
  --delay DELAY         duration in seconds to wait between
                        2 recent changes check (default: 10 s)
  --backcheck BACKCHECK check at launch recent changes in the 
                        last BACKCHECK seconds (default: 0)
                        
```

#### Preferred date format

```
%Y-%m-%dT01:00:00.000+00:00
```

If you need to automate the bot running a few times a week, you can use the following Linux command :
```
> date -d "-2 days" +'%Y-%m-%dT01:00:00.000+00:00'
2021-06-30T01:00:00.000+00:00
```

## Run
### Wikimedia deployment
Lingua Libre Bot runs on Wikimedia cloud service **[Toolforge.org](https://admin.toolforge.org)**.

Become a maintainer on Tooladmins.wikimedia.org ([Quickstart](https://wikitech.wikimedia.org/wiki/Help:Toolforge/Quickstart)):
* Use your Wikimedia account to [create a Wikimedia developer account](https://toolsadmin.wikimedia.org/register/)
* [Add an SSH public key](https://toolsadmin.wikimedia.org/profile/settings/ssh-keys), you will need it to connect
* [Request Toolforge's membership](https://toolsadmin.wikimedia.org/tools/membership/apply)
* Request [active lingua-libre-bot maintainers](https://toolsadmin.wikimedia.org/tools/id/lingua-libre-bot) for membership
* Please note [your username and link up your accounts](https://toolsadmin.wikimedia.org/profile/settings/accounts/)

Sysadmin the tool via your terminal :
```bash
$ ssh -i <path-to-ssh-private-key> <shell-username>@login.toolforge.org`    # now on WM's server
# ssh -i ~/.ssh/id_ed25519 yug@login.toolforge.org                          # example for User:Yug
$ become lingua-libre-bot                                                   # now in tool's directory.
$ exit                                                                      # return to WM's server
```

### Local test
Git clone repository, then run with `--dryrun`.

## Structure
```
├── requirements.txt — dependencies list (install only).
├── config.ini.sample — config sample (install only).
├── version.py — version number of the bot.
├── lili.py — 
├── llbot.py — abstraction and help documentation
├── pywiki.py — 
├── record.py — data formating
├── sparql.py — handles SPARQL queries response's errors and formating
└── wikis/
    ├── wiki.py — 
    ├── wikidata.py — wikidata specific
    ├── wiktionary.py — abstraction for wiktionaries
    └── wiktionaries/
        ├── {iso}wiktionary.py — ... for wiktionary of language {iso}
        └── {iso}wiktionary.py — idem, etc.
```
## Contribute
- [Phabricator: Lingua-libre > Bots and data management](https://phabricator.wikimedia.org/tag/lingua_libre/) — tickets manager
- [Github: Lingua-libre/Lingua-Libre-Bot](https://github.com/lingua-libre/Lingua-Libre-Bot) — code (python)

## See also
- [Meta: User:Lingua_Libre_Bot](https://meta.wikimedia.org/wiki/User:Lingua_Libre_Bot) — main bot account on Wikimedia
  - [Special:CentralAuth](https://meta.wikimedia.org/wiki/Special:CentralAuth/Lingua_Libre_Bot) — userrights across projects
- [LinguaLibre:Bot](https://lingualibre.org/wiki/LinguaLibre:Bot) — forum (request, help)
- [Toolserver: lingua-libre-bot](https://toolsadmin.wikimedia.org/tools/id/lingua-libre-bot) — server (runs here)
