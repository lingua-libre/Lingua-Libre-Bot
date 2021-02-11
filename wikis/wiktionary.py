#!/usr/bin/python3.8
# -*- coding: utf-8 -*-
# Author: Florian "Poslovitch" Cuny
# Date: 23 January 2021
# License: GNU GPL v2+

from abc import ABC, abstractmethod
import pywiki


class Wiktionary(ABC):
    """
    Handles the bot's behavior when contributing to Wiktionaries.

    This abstract class provides a frame with the basic variables and workflow.
    It MUST be inherited from by a subclass that will implement version-specific operations
    (such as FrWiktionary for the French Wiktionary).
    """

    def __init__(self, user, password, domain_name: str):
        self.API_ENDPOINT = f"https://{domain_name}/w/api.php"
        self.api = pywiki.Pywiki(user, password, self.API_ENDPOINT, "user")
        self.dry_run = False
        pass

    # Abstract methods

    @abstractmethod
    def get_edit_summary(self, record):
        """
        Returns the edit summary for this record.
        """
        return None

    # Public methods

    def set_dry_run(self) -> None:
        """
        Configures the bot to do a dry run (i.e. run without applying the changes to pages).
        """
        self.dry_run = True
        self.api.set_dry_run(True)

    def get_location_translation(self, record):
        """
        Fetches the labels of the record's speaker's location, in the wiktionary's language.
        """
        # TODO: Get the LOCATION_QUERY

    def prepare_records(self, records):
        """
        Fetches additional information about the records
        """

        for record in records:
            # TODO: Add the whole handling there
            self.get_location_translation(record)

    def execute(self, record):
        pass

    def fetch_entry(self, pagename, filename):
        """
        Fetches the page content from Wiktionary and checks whether the file is already part of it.

        Parameters
        ----------
        pagename: str
            Name of the page to fetch
        filename: str
            Name of the file of the recording

        Returns
        -------
        bool
            `True` if the recording is already part of the page, `False` otherwise.
        str
            Content of the page (as unparsed wikicode).
        str
            Timestamp of the page's current revision (used by the API to detect eventual edit conflicts).
        """

    def do_edit(self, pagename, wikicode, basetimestamp):
        """
        Applies the edit to the page.

        Returns
        -------
        bool
            True if the edit was successfully applied, False otherwise.
        """
        result = self.api.request(
            {
                "action": "edit",
                "format": "json",
                "formatversion": "2",
                "title": pagename,
                "summary": self.get_edit_summary(),
                "basetimestamp": basetimestamp,
                "text": str(wikicode),
                "token": self.api.get_csrf_token(),
                "nocreate": 1,
                "bot": 1,
            }
        )

        if "edit" in result:
            return True

        return False