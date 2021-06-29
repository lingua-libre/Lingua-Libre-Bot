#!/usr/bin/python3.8
# -*- coding: utf-8 -*-
# Author: Florian "Poslovitch" Cuny
# Date: 5 June 2021
# License: GNU GPL v2+

import abc
import re

import wikitextparser as wtp
from sparql import Sparql
from wikis.wikifamily import WikiFamily

SANITIZE_REGEX = re.compile(r"== +\n")

SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"

LOCATION_QUERY = """
SELECT ?location ?locationLabel ?countryLabel
WHERE {
  ?location wdt:P17 ?country.
  SERVICE wikibase:label { bd:serviceParam wikibase:language "$0, en" . }
  VALUES ?location { wd:$1 }
}
"""


# Normalize the transcription to fit frwiktionary's/ocwiktionary title conventions
def normalize(transcription):
    return transcription.replace("'", "’")


class Wiktionary(WikiFamily, abc.ABC):

    def __init__(self, user, password, language_domain: str, summary: str, sanitize: bool = False):
        """
        Constructor.

        Parameters
        ----------
        user
            Username to login to the wiki.
        password
            Password to log into the account.
        language_domain:
            The "language" of the wiki (e.g. 'fr', 'en' or even 'www').
        """
        super().__init__(user, password, "wiktionary", language_domain)
        self.sanitize = sanitize
        self.summary = summary
        self.location_map = {}

    """
    Abstract
    """
    @abc.abstractmethod
    def format_location(self, sparql: Sparql, location_data) -> str:
        # Move to proper thing?
        country = sparql.format_value(location_data, "countryLabel")
        location = sparql.format_value(location_data, "locationLabel")
        result = country
        if country != location:
            result += " (" + location + ")"
        return result

    """
    Methods
    """

    # Prepare the records to be added on the French Wiktionary:
    # - Get the labels of the speaker's location in French
    def prepare(self, records):
        sparql = Sparql(SPARQL_ENDPOINT)

        # Extract all different locations
        locations = set()
        for record in records:
            if record["speaker"]["residence"] is not None:
                locations.add(record["speaker"]["residence"])

        self.location_map = {}
        raw_location_map = sparql.request(
            LOCATION_QUERY.replace("$0", self.language_domain).replace("$1", " wd:".join(locations))
        )
        for line in raw_location_map:
            self.location_map[sparql.format_value(line, "location")] = self.format_location(sparql, line)

    def do_edit(self, page_name: str, wikicode: wtp.WikiText, base_timestamp, summary: str) -> bool:
        """
        Applies the change to
        """
        result = self.api.request(
            {
                "action": "edit",
                "format": "json",
                "formatversion": "2",
                "title": page_name,
                "summary": summary,
                "basetimestamp": base_timestamp,
                "text": str(wikicode),
                "token": self.api.get_csrf_token(),
                "nocreate": 1,
                "bot": 1,
            }
        )

        if "edit" in result:
            return True

        return False

    def get_entry(self, page_name, file_name):
        """
        Fetches the contents of the given page on Wiktionary and also checks if the file is in the page.

        Parameters
        ----------
        page_name: str
            Name of the page on the Wiktionary.
        file_name: str
            Name of the file to find if it is present or not (without File:).
        """
        response = self.api.request(
            {
                "action": "query",
                "format": "json",
                "formatversion": "2",
                "prop": "images|revisions",
                "rvprop": "content|timestamp",
                "titles": page_name,
                "imimages": "File:" + file_name,
            }
        )
        page = response["query"]["pages"][0]

        # If no pages have been found on this wiki for the given title
        if "missing" in page:
            return False, False, 0

        # If there is the 'images' key, this means that the API has found
        # the file at least once in the page, see [[:mw:API:Images]]
        is_already_present = "images" in page

        # Extract the needed infos from the response and return them
        wikicode = page["revisions"][0]["content"]
        base_timestamp = page["revisions"][0]["timestamp"]

        # TODO: Is it needed for all wiktionaries ?
        if self.sanitize:
            # Sanitize the wikicode to avoid edge cases later on
            wikicode = SANITIZE_REGEX.sub('==\n', wikicode)

        return is_already_present, wtp.parse(wikicode), base_timestamp

    def execute(self, record) -> bool:
        # Normalize the record using ocwiktionary's titles conventions
        transcription = normalize(record["transcription"])

        # Fetch the content of the page having the transcription for title
        (is_already_present, wikicode, base_timestamp) = self.get_entry(transcription, record["file"])

        # Whether there is no entry for this record on wiktionary
        if not wikicode:
            return False

        # Whether the record is already inside the entry
        if is_already_present:
            print(record["id"] + ": already on ocwiktionary")  # TODO: better log msgs
            return False

        # TODO: blabla

        # Save the result
        try:
            result = self.do_edit(transcription, wikicode, base_timestamp, self.summary)
        except Exception as e:
            # If we got an editconflict, just restart from the beginning
            if str(e).find("editconflict") > -1:
                self.execute(record)
            else:
                raise e

        if result is True:  # TODO: better log
            print(
                record["id"] + "//" + transcription
                + ": added to frwiktionary - https://fr.wiktionary.org/wiki/"
                + transcription
            )

        return result
