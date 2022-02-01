#!/usr/bin/python3.8
# -*- coding: utf-8 -*-
# Author: Florian "Poslovitch" Cuny
# Date: 7 July 2021
# License: GNU GPL v2+

import abc
import wikitextparser as wtp
import re

from wikis.wikifamily import WikiFamily

SANITIZE_REGEX = re.compile(r"== +\n")


class Wiktionary(WikiFamily, abc.ABC):

    def __init__(self, user: str, password: str, language_domain: str, summary: str):
        """
        Constructor.

        Parameters
        ----------
        user
            Username to login to the wiki.
        password
            Password to log into the account.
        language_domain:
            The "language" of the wiki (e.g. 'fr', 'en', etc.).
        summary:
            The edit summary.
        """
        super().__init__(user, password, "wiktionary", language_domain)
        self.summary = summary

    """
    Public methods
    """

    # Fetch the contents of the given Wiktionary entry,
    # and check by the way whether the file is already in it.
    def get_entry(self, pagename: str, filename: str):
        response = self.api.request(
            {
                "action": "query",
                "format": "json",
                "formatversion": "2",
                "prop": "images|revisions",
                "rvprop": "content|timestamp",
                "titles": pagename,
                "imimages": "File:" + filename,
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
