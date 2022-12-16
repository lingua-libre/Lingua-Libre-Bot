#!/usr/bin/python3.8
# -*- coding: utf-8 -*-
# License: GNU GPL v2+

import argparse
import configparser
import os
import sys
from typing import Iterable

import lili
from wikis.wikidata import Wikidata, Lexeme
from wikis.wiktionaries.frwiktionary import FrWiktionary
from wikis.wiktionaries.kuwiktionary import KuWiktionary
from wikis.wiktionaries.ocwiktionary import OcWiktionary
from wikis.wiktionaries.orwiktionary import OrWiktionary
from wikis.wiktionaries.shywiktionary import ShyWiktionary

config = configparser.ConfigParser()
res = config.read(f"{os.path.dirname(os.path.realpath(__file__))}/config.ini")
if len(res) == 0:
    raise OSError("config.ini does not exist")


def main() -> None:
    wiki_classes = {
        "wikidatawiki": Wikidata,
        "lexemes": Lexeme,
        "frwiktionary": FrWiktionary,
        "kuwiktionary": KuWiktionary,
        "ocwiktionary": OcWiktionary,
        "orwiktionary": OrWiktionary,
        "shywiktionary": ShyWiktionary,
    }

    parser = create_parser(wiki_classes.keys())
    args = parser.parse_args()

    if args.wiki is not None:
        wiki_classes = {args.wiki: wiki_classes[args.wiki]}

    username = config.get("wiki", "user")
    password = config.get("wiki", "password")

    wikis = {
        wiki_name: wiki_class(username, password, bool(args.dryrun))
        for wiki_name, wiki_class in wiki_classes.items()
    }

    items = args.func(args, wikis)
    print(len(items))


def create_parser(supported_wikis: Iterable[str]) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Reuse records made on Lingua Libre on some wikis."
    )
    parser.add_argument(
        "--wiki",
        help="run only on the selected wiki",
        choices=list(supported_wikis),
    )
    parser.add_argument(
        "--dryrun",
        action='store_true',
        help="show the result without actually doing any edit"
    )
    subparsers = parser.add_subparsers(title="Execution modes", dest="mode")
    subparsers.required = True
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
    return parser


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print('\nStopping Lingua Libre Bot')
        sys.exit(0)
