#!/usr/bin/python3.8
# -*- coding: utf-8 -*-
# Author: Aure Séguier "Unuaiga"
# Date: 16 december 2018
# License: GNU GPL v2+

import re
import wikitextparser as wtp

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
    r"(?:\s*(?:\[\[(?:Category|Categoria):[^\]]+\]\]|{{clé de tri\|[^}]+}})?)*$",
    re.IGNORECASE,
)


class OcWiktionary(Wiktionary):

    def __init__(self, user, password):
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

    """
    Public methods
    """

    # Prepare the records to be added on the French Wiktionary:
    # - Fetch the needed language code map (Qid -> BCP 47, used by ocwiktionary)
    # - Get the labels of the speaker's location in French
    def prepare(self, records):
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

        return records

        # Try to use the given record on the Occitan Wiktionary

    def execute(self, record):
        pass
        # Check if the record's language has a BCP 47 code, stop here if not
        # if record["language"]["qid"] not in self.language_code_map:
        #     print(record["id"] + ": language code not found")
        #     return False
        #
        # lang = self.language_code_map[record["language"]["qid"]]
        #
        # motvar = re.search(r"^oc\-([^\-]*?)(\-|$)", lang)
        #
        # labelvar = False
        #
        # if motvar:
        #     codevar = motvar.group(1)
        #     if record["language"]["qid"] in self.language_label_map:
        #         labelvar = self.language_label_map[record["language"]["qid"]]
        #     lang = "oc"
        #
        #     # Whether there is no section for the current language
        # if "{=" + lang + "=}" not in wikicode:
        #     print(record["id"] + ": language section not found")
        #     return False
        #
        # motif = ""
        # stringlg = "{=" + lang + "=}"
        # for i in range(0, len(stringlg)):
        #     lettre = stringlg[i]
        #     if i > 0:
        #         motif = motif + "|"
        #     motif = motif + stringlg[0:i].replace("{", "\{")
        #     motif = motif + "[^" + stringlg[i].replace("{", "\{") + "]"
        #
        # motif = re.search(
        #     r"{{="
        #     + lang
        #     + "=}}(([^{]|{[^{]|{{[^\-=]|{{-[^p]|{{-p[^r]|{{-pr[^o]|{{-pro[^n]|{{-pron[^-]|{{-pron-[^}]|{{-pron-}[^}])*?)({{=([^\=]*?)=}}|$)",
        #     wikicode,
        # )
        #
        # if motif:
        #     wikicode = re.sub(
        #         r"{{="
        #         + lang
        #         + "=}}(([^{]|{[^{]|{{[^\-=]|{{-[^p]|{{-p[^r]|{{-pr[^o]|{{-pro[^n]|{{-pron[^-]|{{-pron-[^}]|{{-pron-}[^}])*?)({{=([^\=]*?)=}}|{{-sil-}}|{{-([^\-]*?)\-\|([a-z]+)}}|$)",
        #         "{{=" + lang + "=}}\g<1>{{-pron-}}\g<3>",
        #         wikicode,
        #     )
        #
        # loccode = ""
        # if record["speaker"]["residence"]:
        #
        #     sparql = Sparql(SPARQL_ENDPOINT)
        #
        #     self.location_map = {}
        #     raw_location_map = sparql.request(
        #         LOCATION_QUERY.replace("$1", " wd:" + record["speaker"]["residence"])
        #     )
        #     if len(raw_location_map) > 0:
        #         country = sparql.format_value(raw_location_map[0], "countryLabel")
        #         location = sparql.format_value(raw_location_map[0], "locationLabel")
        #
        #         if country:
        #             loccode = country
        #
        #             if location and location != country:
        #                 loccode = loccode + " (" + location + ")"
        #         elif location:
        #             loccode = location
        #         else:
        #             loccode = ""
        #
        #         if labelvar:
        #             loccode = loccode + " - " + labelvar
        #
        #         if loccode != "":
        #             loccode = loccode + " : "
        #
        # codefichier = (
        #     loccode
        #     + "escotar « "
        #     + record["transcription"]
        #     + " » [[Fichièr:"
        #     + record["file"]
        #     + "]]"
        # )
        #
        # wikicode = re.sub(
        #     r"\{="
        #     + lang
        #     + "=\}(([^\{]|\{[^=])*?)\{\{-pron-\}\}(([^\{]|\{[^\{]|\{\{[^\-])*?)(\{\{-|\{\{=|$)",
        #     "{=" + lang + "=}\g<1>{{-pron-}}\g<3>" + codefichier + "\n\g<5>",
        #     wikicode,
        # )
        #
        # return result
