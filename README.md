# Lingua-Libre-Bot
This is the source code of [Lingua Libre Bot](https://meta.wikimedia.org/wiki/User:Lingua_Libre_Bot), who's goal is to ease the resuse of all the records made on [Lingua Libre](https://lingualibre.fr) on as much wikis as possible.

### Dependencies
Lingua Libre Bot requires python3.5 to work, and the following packages in their latest version:
* configparser
* requests
* json
* argparse
* urllib
* re
* uuid


### Installation
Install the aforementioned packages: 
<pre>pip install -r requirements.txt</pre>

Copy the configuration file and edit it with your information:
<pre>
  cp config.ini.sample config.ini
  vi config.ini
</pre>


### Usage
<pre>usage: llbot.py [-h] [--item ITEM] [--startdate STARTDATE] [--enddate ENDDATE]
                [--user USER]
                [--lang LANG | --langiso LANGISO | --langwm LANGWM]

Reuse records made on Lingua Libre on some wikis.

optional arguments:
  -h, --help            show this help message and exit
  --item ITEM           run only on the given lingualibre item
  --startdate STARTDATE from which timestamp to start
  --enddate ENDDATE     at which timestamp to end
  --user USER           run only on records from the given user
  --wiki {wikidatawiki,frwiktionary}
                        run only on the selected wiki
  --lang LANG           run only on records from the given language,
                        identified by its lingua libre qid
  --langiso LANGISO     run only on records from the given language,
                        identified by its iso 693-3 code
  --langwm LANGWM       run only on records from the given language,
                        identified by its wikimedia language code
</pre>
