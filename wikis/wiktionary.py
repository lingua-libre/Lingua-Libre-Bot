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
from record import Record
from wikis.wikifamily import WikiFamily

SANITIZE_REGEX = re.compile(r"== +\n")
SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"


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


class Wiktionary(WikiFamily, abc.ABC):

    def __init__(self, user: str, password: str, language_domain: str, summary: str, dry_run: bool) -> None:
        """
        Constructor.
        @param user: Username to login to the wiki
        @param password: Password to log into the account
        @param language_domain: The "language" of the wiki (e.g. 'fr', 'en', etc.)
        @param summary: The edit summary
        """
        super().__init__(user, password, "wiktionary", language_domain, dry_run)
        self.summary = summary

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
