#!/usr/bin/python3.8
# -*- coding: utf-8 -*-
# Author: Aure Séguier "Unuaiga"
# Date: 16 december 2018
# License: GNU GPL v2+

import re
from typing import List

import wikitextparser as wtp

from record import Record
from sparql import Sparql
from wikis.wiktionary import Wiktionary

SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"
SUMMARY = "Ajust d'un fichèr audiò de prononciacion de Lingua Libre estant"

# Do not remove the $1, it is used to force the section to have a content
EMPTY_PRONUNCIATION_SECTION = "\n\n=== {{S|prononciacion}} ===\n$1"
PRONUNCIATION_LINE = "\n* {{escotar|lang=$2|$3|audio=$1}}"

# To be sure not to miss any title, they are normalized during comparaisons;
# those listed bellow must thereby be in lower case and without any space
FOLLOWING_SECTIONS = [
    "{{s|anagramas}}",
    "{{s|anagr}}",
    "{{s|vejatz}}",
    "{{s|vejatz tanben}}",
    "{{s|ref}}",
    "{{s|referéncias}}",
]

LANGUAGE_QUERY = """
SELECT ?item ?code ?itemLabel
WHERE {
    ?item wdt:P305 ?code.
      SERVICE wikibase:label { bd:serviceParam wikibase:language "oc, en" . }
}
"""
LOCATION_QUERY = """
SELECT ?location ?locationLabel ?countryLabel
WHERE {
  ?location wdt:P17 ?country.
  SERVICE wikibase:label { bd:serviceParam wikibase:language "oc, en" . }
  VALUES ?location { wd:$1 }
}
"""

BOTTOM_REGEX = re.compile(
    r"(?:\s*(?:\[\[(?:Category|Categoria):[^]+]]]clé de tri\|[^}]+}})?)*$",
    re.IGNORECASE,
)


class OcWiktionary(Wiktionary):

    def __init__(self, user: str, password: str):
        """
        Constructor.

        Parameters
        ----------
        user
            Username to login to the wiki.
        password
            Password to log into the account.
        """
        super().__init__(user, password, "oc", SUMMARY)
        self.language_code_map = {}
        self.language_label_map = {}

    # Prepare the records to be added on the French Wiktionary:
    # - Fetch the needed language code map (Qid -> BCP 47, used by ocwiktionary)
    # - Get the labels of the speaker's location in French
    def prepare(self, records: List[Record]) -> List[Record]:
        sparql = Sparql(SPARQL_ENDPOINT)

        # Get BCP 47 language code map
        self.language_code_map = {}
        self.language_label_map = {}
        raw_language_code_map = sparql.request(LANGUAGE_QUERY)

        for line in raw_language_code_map:
            self.language_code_map[
                sparql.format_value(line, "item")
            ] = sparql.format_value(line, "code")
            self.language_label_map[
                sparql.format_value(line, "item")
            ] = sparql.format_value(line, "itemLabel")

            # Extract all different locations
        locations = set()
        for record in records:
            if record.language["learning"] is not None:
                locations.add(record.language["learning"])
            elif record.speaker.residence is not None:
                locations.add(record.speaker.residence)

        self.location_map = {}
        raw_location_map = sparql.request(
            LOCATION_QUERY.replace("$1", " wd:".join(locations))
        )
        for line in raw_location_map:
            country = sparql.format_value(line, "countryLabel")
            location = sparql.format_value(line, "locationLabel")
            self.location_map[sparql.format_value(line, "location")] = country
            if country != location:
                self.location_map[sparql.format_value(line, "location")] += (
                        " (" + location + ")"
                )

        return records

    def execute(self, record: Record) -> bool:
        """
        Try to use the given record on the Occitan Wiktionary.
        @param record:
        @return:
        """
        # Normalize the record using ocwiktionary's titles conventions
        transcription = self.__normalize(record.transcription)

        # Fetch the content of the page having the transcription for title
        (is_already_present, wikicode, basetimestamp) = self.get_entry(transcription, record.file)

        # Whether there is no entry for this record on ocwiktionary
        if not wikicode:
            return False

            # Whether the record is already inside the entry
        if is_already_present:
            print(f"{record.id}: already on ocwiktionary")
            return False

            # Check if the record's language has a BCP 47 code, stop here if not
        if record.language["qid"] not in self.language_code_map:
            print(f"{record.id}: language code not found")
            return False

        lang = self.language_code_map[record.language["qid"]]

        motvar = re.search(r"^oc-([^\-]*?)(-|$)", lang)

        labelvar = False

        if motvar:
            if record.language["qid"] in self.language_label_map:
                labelvar = self.language_label_map[record.language["qid"]]
            lang = "oc"

        # Whether there is no section for the current language
        if "{=" + lang + "=}" not in wikicode:
            print(f"{record.id}: language section not found")
            return False

        motif = ""
        stringlg = "{=" + lang + "=}"
        for i in range(len(stringlg)):
            if i > 0:
                motif += "|"
            motif += stringlg[:i].replace("{", "\{")
            motif += "[^" + stringlg[i].replace("{", "\{") + "]"

        motif = re.search(
            r"{{="
            + str(lang)
            + r"=}}(([^{]|{[^{]|{{[^\-=]|{{-[^p]|{{-p[^r]|{{-pr[^o]|{{-pro[^n]|{{-pron[^-]|{{-pron-[^}]|{{-pron-}[^}])*?)({{=([^=]*?)=}}|$)",
            str(wikicode),
        )

        if motif:
            wikicode = re.sub(
                r"{{="
                + str(lang)
                + r"=}}(([^{]|{[^{]|{{[^\-=]|{{-[^p]|{{-p[^r]|{{-pr[^o]|{{-pro[^n]|{{-pron[^-]|{{-pron-[^}]|{{-pron-}[^}])*?)({{=([^=]*?)=}}|{{-sil-}}|{{-([^\-]*?)-\|([a-z]+)}}|$)",
                "{{=" + lang + r"=}}\g<1>{{-pron-}}\g<3>",
                str(wikicode),
            )

        learning_or_residence = record.language["learning"] or record.speaker.residence
        loccode = ""
        if learning_or_residence:
            sparql = Sparql(SPARQL_ENDPOINT)

            self.location_map = {}
            raw_location_map = sparql.request(
                LOCATION_QUERY.replace("$1", " wd:" + learning_or_residence)
            )
            if len(raw_location_map) > 0:
                country = sparql.format_value(raw_location_map[0], "countryLabel")
                location = sparql.format_value(raw_location_map[0], "locationLabel")

                if country:
                    loccode = country

                    if location and location != country:
                        loccode = loccode + " (" + location + ")"
                elif location:
                    loccode = location
                else:
                    loccode = ""

                if labelvar:
                    loccode = loccode + " - " + labelvar

                if loccode != "":
                    loccode = loccode + " : "

        codefichier = f"{loccode}escotar « {record.transcription} » [[Fichièr:{record.file}]]"

        wikicode = re.sub(
            r"{="
            + str(lang)
            + r"=}(([^{]|{[^=])*?){{-pron-}}(([^{]|{[^{]|{{[^\-])*?)({{-|{{=|$)",
            "{=" + lang + r"=}\g<1>{{-pron-}}\g<3>" + codefichier + r"\n\g<5>",
            str(wikicode),
        )

        # Save the result
        try:
            result = self.do_edit(transcription, wtp.parse(wikicode), basetimestamp)
        except Exception as e:
            # If we got an editconflict, just restart from the beginning
            if "editconflict" in str(e):
                self.execute(record)
            else:
                raise e

        if result:
            print(
                record.id
                + ": added to ocwiktionary - https://oc.wiktionary.org/wiki/"
                + transcription
            )

        return result