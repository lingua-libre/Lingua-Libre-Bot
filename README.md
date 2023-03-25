# Lingua Libre Bot
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

## Structure
```
├── requirements.txt — dependencies list (install only).
├── config.ini.sample — config sample (install only).
├── version.py — version number of the bot.
├── lili.py — 
├── llbot.py — 
├── pywiki.py — 
├── record.py — 
├── sparql.py — handles SPARQL queries response's errors and formating
└── wikis/
    ├── wiki.py — 
    ├── wikidata.py — 
    ├── wiktionary.py — 
    └── wiktionaries/
        ├── {iso}wiktionary.py — ... for wiktionary of language {iso}
        └── {iso}wiktionary.py — idem, etc.
```

## See also
- [Meta: User:Lingua_Libre_Bot](https://meta.wikimedia.org/wiki/User:Lingua_Libre_Bot) — main bot account on Wikimedia
  - [Special:CentralAuth](https://meta.wikimedia.org/wiki/Special:CentralAuth/Lingua_Libre_Bot) — userrights across projects
- [LinguaLibre:Bot](https://lingualibre.org/wiki/LinguaLibre:Bot) — forum (request, help)
- [Github: Lingua-libre/Lingua-Libre-Bot](https://github.com/lingua-libre/Lingua-Libre-Bot) — code (python)
- [Phabricator: Lingua-libre > Bots and data management](https://phabricator.wikimedia.org/tag/lingua_libre/) — tickets manager
- [Toolserver: lingua-libre-bot](https://toolsadmin.wikimedia.org/tools/id/lingua-libre-bot) — server (runs here)
