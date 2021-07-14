# Lingua Libre Bot
This is the source code of [Lingua Libre Bot](https://meta.wikimedia.org/wiki/User:Lingua_Libre_Bot), whose goal is to ease the reuse of all the records made on [Lingua Libre](https://lingualibre.org) on as much wikis as possible.

## Wikimedia projects

Lingua Libre Bot is able to contribute on the following Wikimedia projects:
* Wikidata
* Wikidata Lexemes
* French Wiktionary
* Occitan Wiktionary

## Operational documentation

### Dependencies

Lingua Libre Bot requires Python 3.6 to work, and the following packages in their latest version:
* wikitextparser
* requests
* argparse
* uuid
* backoff

### Installation

Install the aforementioned packages:
```
pip install -r requirements.txt
```

Copy the configuration file and edit it with your information:
```
cp config.ini.sample config.ini
vi config.ini
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
