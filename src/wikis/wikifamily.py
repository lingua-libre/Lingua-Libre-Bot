#!/usr/bin/python3.8
# -*- coding: utf-8 -*-
# Author: Florian "Poslovitch" Cuny
# Date: 5 June 2021
# License: GNU GPL v2+

from abc import ABC, abstractmethod
from typing import List

import pywiki
from record import Record


class WikiFamily(ABC):
    """
    Provides the backbone of the implementation of the bot on any family of wikis.
    This abstract class provides a frame with the basic variables and methods.
    It MUST be inherited from by a subclass that will implement wiki-specific operations
    (such as Wiktionary for the Wiktionaries).
    """

    def __init__(self, user: str, password: str, wiki_family: str, language_domain: str):
        """
        Constructor.

        Parameters
        ----------
        user
            Username to login to the wiki.
        password
            Password to log into the account.
        wiki_family:
            The "family" of the wiki. This is the domain name of the wiki (e.g. 'wiktionary').
        language_domain:
            The "language" of the wiki (e.g. 'fr', 'en' or even 'www').
        """
        self.API_ENDPOINT = f"https://{language_domain}.{wiki_family}.org/w/api.php"
        self.api = pywiki.Pywiki(user, password, self.API_ENDPOINT, "user")
        self.language_domain = language_domain

    """
    Public methods
    """

    def set_dry_run(self):
        """
        Enables the "dry run" mode.
        The bot will compute changes without applying them to the pages, and will print out the page content or the
        request it will have generated.
        """
        self.api.set_dry_run(True)

    def prepare(self, records: List[Record]) -> List[Record]:
        """
        Prepare the records to be added to pages.
        @param records: the list of records to prepare
        @return: the list of prepared records
        """
        return records

    @abstractmethod
    def execute(self, record: Record) -> bool:
        """
        Add the record to the pages.
        @param record: the list of records to add
        """
