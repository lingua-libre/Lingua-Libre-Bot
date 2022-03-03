import datetime
import json
import time
from typing import List

import requests

import sparql

from record import Record

ENDPOINT = "https://lingualibre.org/bigdata/namespace/wdq/sparql"
API = "https://lingualibre.org/api.php"
BASEQUERY = """
SELECT DISTINCT
    ?record ?file ?transcription
    ?wikidataId ?lexemeId ?wikipediaTitle ?wiktionaryEntry
    ?languageIso ?languageQid ?languageWMCode
    ?residence ?learningPlace ?languageLevel
WHERE {
  ?record prop:P2 entity:Q2 .
  ?record prop:P3 ?file .
  ?record prop:P4 ?language .
  ?record prop:P5 ?speaker .
  ?record prop:P7 ?transcription .
  OPTIONAL { ?record prop:P12 ?wikidataId . }
  OPTIONAL { ?record prop:P21 ?lexemeId . }
  OPTIONAL { ?record prop:P19 ?wikipediaTitle . }
  OPTIONAL { ?record prop:P20 ?wiktionaryEntry . }

  OPTIONAL { ?language prop:P12 ?languageQid . }

  OPTIONAL { ?speaker prop:P14 ?residence . }

  ?speaker llp:P4 ?speakerLanguagesStatement .
  ?speakerLanguagesStatement llv:P4 ?speakerLanguages .
  OPTIONAL { ?speakerLanguagesStatement llq:P15 ?learningPlace . }
  OPTIONAL { ?speakerLanguagesStatement llq:P16 ?languageLevel . }

  FILTER( ?speakerLanguages = ?language) .

  SERVICE wikibase:label {
    bd:serviceParam wikibase:language "en" .
  }

  #filters
}"""


def get_records(query: str) -> List[Record]:
    print("Requesting data")
    raw_records = sparql.request(ENDPOINT, query)
    print("Request done")
    records = [Record(
        id=sparql.format_value(record, "record"),
        file=sparql.format_value(record, "file"),
        transcription=sparql.format_value(record, "transcription"),
        speaker_residence=sparql.format_value(record, "residence"),
        links={
            "wikidata": sparql.format_value(record, "wikidataId"),
            "lexeme": sparql.format_value(record, "lexemeId"),
            "wikipedia": sparql.format_value(record, "wikipediaTitle"),
            "wiktionary": sparql.format_value(record, "wiktionaryEntry"),
        },
        language={
            "qid": sparql.format_value(record, "languageQid"),
            "learning": sparql.format_value(record, "learningPlace"),
            "level": sparql.format_value(record, "languageLevel"),
        })
        for record in raw_records]
    print(f"Found {len(records)} records.")
    return records


def live_mode(args, supported_wikis):
    delay = args.delay
    time_delta = datetime.datetime.utcnow() - datetime.timedelta(seconds=args.backcheck)
    prev_timestamp = f'{time_delta.replace(microsecond=0).isoformat()}Z'
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
                "rcprop": "title|ids",
                "rclimit": "500",
                "rctype": "new|edit",
            },
        )
        data = json.loads(r.text)["query"]["recentchanges"]

        prev_timestamp = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
        print("Current time:", prev_timestamp)

        for rc in data:
            items.add(rc["title"])
            print("found:", rc["title"])

        if len(items.difference(prev_items)) > 0:
            args.item = ",".join(items.difference(prev_items))
            prev_items = set(simple_mode(args, supported_wikis))
            print(len(prev_items))

        items = items.difference(prev_items)

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
        filters = "VALUES ?record {entity:" + " entity:".join(args.item.split(",")) + "}."

    else:
        if args.startdate or args.enddate:
            filters += ' ?record prop:P6 ?date .'
            if args.startdate is not None:
                filters += 'FILTER( ?date > "' + args.startdate + '"^^xsd:dateTime ).'
            if args.enddate is not None:
                filters += 'FILTER( ?date < "' + args.enddate + '"^^xsd:dateTime ).'
        if args.user is not None:
            filters += '?speaker prop:P11 ?linkeduser. FILTER( ?linkeduser = "' + args.user + '" ).'
        if args.lang is not None:
            filters += f"BIND( entity:{args.lang} as ?language )."
        elif args.langiso is not None:
            filters += 'OPTIONAL { ?language prop:P13 ?languageIso.} FILTER( ?languageIso = "' + args.langiso + '" ).'
        elif args.langwm is not None:
            filters += 'OPTIONAL { ?language prop:P17 ?languageWMCode.} FILTER( ?languageWMCode="' + args.langwm + '").'

            # Get the informations of all the records
    records = get_records(BASEQUERY.replace("#filters", filters))

    # Prepare the records (fetch extra infos, clean some datas,...)
    for dbname in supported_wikis:
        records = supported_wikis[dbname].prepare(records)

    total = len(records)
    for counter, record in enumerate(records, start=1):
        for dbname in supported_wikis:
            if supported_wikis[dbname].execute(record):
                time.sleep(1)
        if counter % 10 == 0:
            print(f"[{counter}/{total}]")
    # TODO: better handling of the KeyboardInterrupt
    # TODO: rapport on LinguaLibre:Bot/Reports avec exécution, dates début/fin,
    #  nombre d'enregistrements traités, combien ajoutés, combien déjà présents...

    return [record["id"] for record in records]
