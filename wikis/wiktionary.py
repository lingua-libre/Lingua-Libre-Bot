#!/usr/bin/python3.8
# -*- coding: utf-8 -*-
# Author: Florian "Poslovitch" Cuny
# Date: 7 July 2021
# License: GNU GPL v2+

import abc
import re
from typing import Tuple, Optional, List, Set

import wikitextparser as wtp

import sparql
from request.record import Record
from sparql import SPARQL_ENDPOINT
from wikis.wikifamily import WikiFamily
from abc import abstractmethod

SANITIZE_REGEX = re.compile(r"== +\n")


def replace_apostrophe(text: str) -> str:
    """
    Replace straight apostrophes with typographic apostrophes.
    @param text:
    @return:
    """
    return text.replace("'", "’")


def safe_append_text(content, text, pattern: re.Pattern):
    """
    Append a string to a wikitext string, but before any category
    @param content:
    @param text:
    @param pattern:
    @return:
    """
    content = str(content)

    search = pattern.search(content)
    index = search.start() if search else len(content)
    return content[:index] + text + content[index:]


def get_locations_from_records(query: str, records: List[Record]) -> Set[str]:
    locations = set()
    for record in records:
        if record.language["learning"] is not None:
            locations.add(record.language["learning"])
        if record.speaker_residence is not None:
            locations.add(record.speaker_residence)

    return sparql.request(SPARQL_ENDPOINT, query.replace("$1", " wd:".join(locations)))


def get_pronunciation_section(wikicode: wtp.WikiText, section_title: str) -> Optional[wtp.Section]:
    """
    Try to extract the pronunciation subsection
    @param wikicode:
    @param section_title:
    @return:
    """
    for section in wikicode.sections:
        if section.title is None:
            continue

        if section.title.replace(" ", "").lower() == section_title.lower():
            return section

    return None


class Wiktionary(WikiFamily, abc.ABC):

    def __init__(self, user: str, password: str, language_domain: str, summary: str, dry_run: bool,
                 location_query) -> None:
        """
        Constructor.
        @param user: Username to login to the wiki
        @param password: Password to log into the account
        @param language_domain: The "language" of the wiki (e.g. 'fr', 'en', etc.)
        @param summary: The edit summary
        """
        super().__init__(user, password, "wiktionary", language_domain, dry_run)
        self.summary = summary
        self.language_code_map = {}
        self.location_map = {}
        self.location_query = location_query

    # Fetch the contents of the given Wiktionary entry,
    # and check by the way whether the file is already in it.
    def get_entry(self, pagename: str, filename: str) -> Tuple[bool, Optional[wtp.WikiText], int]:
        response = self.api.request(
            {
                "action": "query",
                "format": "json",
                "formatversion": "2",
                "prop": "images|revisions",
                "rvprop": "content|timestamp",
                "titles": pagename,
                "imimages": f"File:{filename}",
            }
        )

        page = response["query"]["pages"][0]

        # If no pages have been found on this wiki for the given title
        if "missing" in page:
            return False, None, 0

        # If there is the 'images' key, this means that the API has found
        # the file at least once in the page, see [[:mw:API:Images]]
        is_already_present = "images" in page

        # Extract the needed infos from the response and return them
        wikicode = page["revisions"][0]["content"]
        basetimestamp = page["revisions"][0]["timestamp"]

        # Sanitize the wikicode to avoid edge cases later on
        wikicode = SANITIZE_REGEX.sub('==\n', wikicode)

        return is_already_present, wtp.parse(wikicode), basetimestamp

    # Edit the page
    def do_edit(self, page_name: str, wikicode, basetimestamp) -> bool:
        result = self.api.request(
            {
                "action": "edit",
                "format": "json",
                "formatversion": "2",
                "title": page_name,
                "summary": self.summary,
                "basetimestamp": basetimestamp,
                "text": str(wikicode),
                "token": self.api.get_csrf_token(),
                "nocreate": 1,
                "bot": 1,
            }
        )

        return "edit" in result

    def _get_language_section(self, wikicode, language_qid):
        """
        Try to extract the language section
        @param wikicode:
        @param language_qid:
        @return:
        """
        # Check if the record's language has a BCP 47 code, stop here if not
        if language_qid not in self.language_code_map:
            return None

        lang = self.language_code_map[language_qid]

        # Travel across each sections titles to find the one we want
        for section in wikicode.sections:
            if section.title is None:
                continue

            if section.title.replace(" ", "").lower() == self.language_section(lang):
                return section

                # If we arrive here, it means that there is no section for
                # the record's language
        return None

    def prepare(self, records: List[Record]) -> List[Record]:
        self.fetch_language_codes()
        self.fetch_locations(records)
        return records

    @abstractmethod
    def language_section(self, lang):
        ...

    @abstractmethod
    def fetch_language_codes(self):
        ...

    def fetch_locations(self, records):
        raw_location_map = get_locations_from_records(self.location_query, records)
        self.location_map = {}
        for line in raw_location_map:
            country = sparql.format_value(line, "countryLabel")
            location = sparql.format_value(line, "locationLabel")
            location_key = sparql.format_value(line, "location")
            self.location_map[location_key] = self.compute_location_label(country, location)

    @abstractmethod
    def compute_location_label(self, country, location):
        ...

    def save_result(self, basetimestamp, record, transcription, wikicode):
        result = False
        try:
            result = self.do_edit(transcription, wikicode, basetimestamp)
        except Exception as e:
            if "editconflict" in str(e):
                self.execute(record)
            else:
                raise e
        if result:
            print(self.get_save_message(record, transcription))
        return result

    @abstractmethod
    def get_save_message(self, record, transcription):
        ...
