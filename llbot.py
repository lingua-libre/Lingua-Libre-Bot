#!/usr/bin/python3.8
# -*- coding: utf-8 -*-
# License: GNU GPL v2+

import argparse
import configparser
import os
import sys

import lili
from wikis.wikidata import Wikidata, Lexemes
from wikis.wiktionaries.frwiktionary import FrWiktionary
from wikis.wiktionaries.kuwiktionary import KuWiktionary
from wikis.wiktionaries.ocwiktionary import OcWiktionary
from wikis.wiktionaries.shywiktionary import ShyWiktionary

config = configparser.ConfigParser()
res = config.read(os.path.dirname(os.path.realpath(__file__)) + "/config.ini")
if len(res) == 0:
    raise OSError("config.ini does not exist")


# Main
def main():
    # Create an object for each supported wiki
    user = config.get("wiki", "user")
    password = config.get("wiki", "password")
    supported_wikis = {
        "wikidatawiki": Wikidata(user, password),
        "lexemes": Lexemes(user, password),
        "frwiktionary": FrWiktionary(user, password),
        "kuwiktionary": KuWiktionary(user, password),
        "ocwiktionary": OcWiktionary(user, password),
        "shywiktionary": ShyWiktionary(user, password),
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
    simpleparser.set_defaults(func=lili.simple_mode)
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
    liveparser.set_defaults(func=lili.live_mode)
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

    # Make sure a mode has been selected
    if 'func' not in args:
        parser.error("Please provide a mode (either \"simple\" or \"live\")")

    # Filter the wikis depending on the fetched arguments
    if args.wiki is not None:
        tmp = supported_wikis[args.wiki]
        supported_wikis = {args.wiki: tmp}

    if args.dryrun:
        for dbname in supported_wikis:
            supported_wikis[dbname].set_dry_run()

    # Start the bot in the selected mode (simple or live)
    items = args.func(args, supported_wikis)
    print(len(items))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print('\nStopping Lingua Libre Bot')
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)
