#!/usr/bin/python3.5
# -*- coding: utf-8 -*-
# Autor: Antoine "0x010C" Lamielle
# Date: 9 June 2018
# License: GNU GPL v2+

import configparser
import argparse
import time
import datetime
import requests
import json
import os

from sparql import Sparql

from wikis.wikidata import Wikidata
from wikis.frwiktionary import FrWiktionary
from wikis.ocwiktionary import OcWiktionary
from wikis.lexemes import Lexemes


config = configparser.ConfigParser()
config.read(os.path.dirname(os.path.realpath(__file__))+"/config.ini")

ENDPOINT = "https://lingualibre.fr/bigdata/namespace/wdq/sparql"
API = "https://lingualibre.fr/api.php"
BASEQUERY = """
SELECT DISTINCT
    ?record ?file ?speaker ?speakerLabel ?date ?transcription
    ?qualifier ?wikidataId ?lexemeId ?wikipediaTitle ?wiktionaryEntry
    ?languageIso ?languageQid ?languageWMCode ?linkeduser
    ?gender ?residence
WHERE {
  ?record prop:P2 entity:Q2 .
  ?record prop:P3 ?file .
  ?record prop:P4 ?language .
  ?record prop:P5 ?speaker .
  ?record prop:P6 ?date .
  ?record prop:P7 ?transcription .
  OPTIONAL { ?record prop:P18 ?qualifier . }
  OPTIONAL { ?record prop:P12 ?wikidataId . }
  OPTIONAL { ?record prop:P21 ?lexemeId . }
  OPTIONAL { ?record prop:P19 ?wikipediaTitle . }
  OPTIONAL { ?record prop:P20 ?wiktionaryEntry . }

  OPTIONAL { ?language prop:P13 ?languageIso . }
  OPTIONAL { ?language prop:P12 ?languageQid . }
  OPTIONAL { ?language prop:P17 ?languageWMCode . }

  ?speaker prop:P11 ?linkeduser .
  OPTIONAL { ?speaker prop:P8 ?gender . }
  OPTIONAL { ?speaker prop:P14 ?residence . }

  SERVICE wikibase:label {
    bd:serviceParam wikibase:language "en" .
  }

  #filters
}"""


def get_records(query):
    sparql = Sparql(ENDPOINT)
    raw_records = sparql.request(query)
    records = []
    for record in raw_records:
        records += [
            {
                "id": sparql.format_value(record, "record"),
                "file": sparql.format_value(record, "file"),
                "date": sparql.format_value(record, "date"),
                "transcription": sparql.format_value(record, "transcription"),
                "qualifier": sparql.format_value(record, "qualifier"),
                "user": sparql.format_value(record, "linkeduser"),
                "speaker": {
                    "id": sparql.format_value(record, "speaker"),
                    "name": sparql.format_value(record, "speakerLabel"),
                    "gender": sparql.format_value(record, "gender"),
                    "residence": sparql.format_value(record, "residence"),
                },
                "links": {
                    "wikidata": sparql.format_value(record, "wikidataId"),
                    "lexeme": sparql.format_value(record, "lexemeId"),
                    "wikipedia": sparql.format_value(record, "wikipediaTitle"),
                    "wiktionary": sparql.format_value(record, "wiktionaryEntry"),
                },
                "language": {
                    "iso": sparql.format_value(record, "languageIso"),
                    "qid": sparql.format_value(record, "languageQid"),
                    "wm": sparql.format_value(record, "languageWMCode"),
                },
            }
        ]

    return records


def live_mode(args, supported_wikis):
    delay = args.delay
    prev_timestamp = (
        datetime.datetime.utcnow() - datetime.timedelta(seconds=args.backcheck)
    ).replace(microsecond=0).isoformat() + "Z"
    prev_items = set()
    items = set()
    while True:
        start_time = time.time()

        r = requests.get(
            API,
            {
                "action": "query",
                "format": "json",
                "list": "recentchanges",
                "rcstart": prev_timestamp,
                "rcdir": "newer",
                "rcnamespace": "0",
                "rcprop": "title|timestamp|ids",
                "rclimit": "500",
                "rctype": "new|edit",
            },
        )
        data = json.loads(r.text)["query"]["recentchanges"]

        for rc in data:
            items.add(rc["title"])
            prev_timestamp = rc["timestamp"]

        if len(items - prev_items) > 0:
            args.item = ",".join(items - prev_items)
            prev_items = set(simple_mode(args, supported_wikis))
            print(len(prev_items))

        items = items - prev_items

        if len(items) > 0:
            print("Remaining items: " + ",".join(items))

        # Pause the bot if we've not already spend too much time
        time_to_wait = delay - (time.time() - start_time)
        if time_to_wait > 0:
            time.sleep(time_to_wait)


def simple_mode(args, supported_wikis):
    # Add some filters depending on the fetched arguments
    filters = ""
    if args.item is not None:
        filters = (
            "VALUES ?record {entity:" + " entity:".join(args.item.split(",")) + "}."
        )
    else:
        if args.startdate is not None:
            filters = 'FILTER( ?date > "' + args.startdate + '"^^xsd:dateTime ).'
        if args.enddate is not None:
            filters += 'FILTER( ?date < "' + args.enddate + '"^^xsd:dateTime ).'
        if args.user is not None:
            filters += 'FILTER( ?linkeduser = "' + args.user + '" ).'
        if args.lang is not None:
            filters += "BIND( entity:" + args.lang + " as ?language )."
        elif args.langiso is not None:
            filters += 'FILTER( ?languageIso = "' + args.langiso + '" ).'
        elif args.langwm is not None:
            filters += 'FILTER( ?languageWMCode = "' + args.langwm + '" ).'

            # Get the informations of all the records
    records = get_records(BASEQUERY.replace("#filters", filters))

    # Prepare the records (fetch extra infos, clean some datas,...)
    for dbname in supported_wikis:
        records = supported_wikis[dbname].prepare(records)

        # Try to reuse each listed records on each supported wikis
    for record in records:
        for dbname in supported_wikis:
            if supported_wikis[dbname].execute(record):
                time.sleep(1)

    return [record["id"] for record in records]


# Main
def main():
    # Create an object for each supported wiki
    supported_wikis = {
        "wikidatawiki": Wikidata(
            config.get("wiki", "user"), config.get("wiki", "password")
        ),
        "lexemes": Lexemes(config.get("wiki", "user"), config.get("wiki", "password")),
        "frwiktionary": FrWiktionary(
            config.get("wiki", "user"), config.get("wiki", "password")
        ),
        "ocwiktionary": OcWiktionary(
            config.get("wiki", "user"), config.get("wiki", "password")
        ),
    }

    # Declare the command-line arguments
    parser = argparse.ArgumentParser(
        description="Reuse records made on Lingua Libre on some wikis."
    )
    parser.add_argument(
        "--wiki",
        help="run only on the selected wiki",
        choices=list(supported_wikis.keys()),
    )
    parser.add_argument(
        "--dryrun",
        action='store_true',
        help="show the result without actually doing any edit"
    )
    subparsers = parser.add_subparsers(title="Execution modes")

    simpleparser = subparsers.add_parser(
        "simple", help="Run llbot on (a subset of) all items"
    )
    simpleparser.set_defaults(func=simple_mode)
    simpleparser.add_argument("--item", help="run only on the given item")
    simpleparser.add_argument("--startdate", help="from which timestamp to start")
    simpleparser.add_argument("--enddate", help="at which timestamp to end")
    simpleparser.add_argument("--user", help="run only on records from the given user")
    langgroup = simpleparser.add_mutually_exclusive_group()
    langgroup.add_argument(
        "--lang",
        help="run only on records from the given language, identified by its lingua libre qid",
    )
    langgroup.add_argument(
        "--langiso",
        help="run only on records from the given language, identified by its iso 693-3 code",
    )
    langgroup.add_argument(
        "--langwm",
        help="run only on records from the given language, identified by its wikimedia code",
    )

    liveparser = subparsers.add_parser(
        "live", help="Run llbot in (hardly) real time based on Recent Changes"
    )
    liveparser.set_defaults(func=live_mode)
    liveparser.add_argument(
        "--delay",
        help="duration in seconds to wait between 2 recent changes check (default: 10)",
        type=int,
        default=10,
    )
    liveparser.add_argument(
        "--backcheck",
        help="check at launch recent changes in the last BACKCHECK seconds (default: 0)",
        type=int,
        default=0,
    )

    # Parse the command-line arguments
    args = parser.parse_args()

    # Filter the wikis depending on the fetched arguments
    if args.wiki is not None:
        tmp = supported_wikis[args.wiki]
        supported_wikis = {args.wiki: tmp}

    if args.dryrun is not None:
        for dbname in supported_wikis:
            supported_wikis[dbname].set_dry_run()

    # Start the bot in the selected mode (simple or live)
    items = args.func(args, supported_wikis)
    print(len(items))


if __name__ == "__main__":
    main()
