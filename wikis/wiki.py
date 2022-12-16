#!/usr/bin/python3.8
# -*- coding: utf-8 -*-
# License: GNU GPL v2+

import abc
from typing import List

import pywiki
from record import Record


class Wiki(abc.ABC):
    """
    Provide the backbone of the implementation of the bot on any family of wikis.
    This abstract class provides a frame with the basic variables and methods.
    It MUST be inherited from by a subclass that will implement wiki-specific operations
    (such as Wiktionary for the Wiktionaries).
    """

    def __init__(self, username: str, password: str, wiki_family: str, language_domain: str, dry_run: bool) -> None:
        """
        Constructor.
        @param username: Username to login to the wiki
        @param password: Password to log into the account
        @param wiki_family: The "family" of the wiki. This is the domain name of the wiki (e.g. 'wiktionary')
        @param language_domain: The "language" of the wiki (e.g. 'fr', 'en', etc.)
        """
        self.api = pywiki.Pywiki(username, password, f"https://{language_domain}.{wiki_family}.org/w/api.php", "user", dry_run)
        self.language_domain = language_domain

    def prepare(self, records: List[Record]) -> List[Record]:
        return records

    @abc.abstractmethod
    def execute(self, record: Record) -> bool:
        """
        Add the given record on the relevant page of the project.
        @param record: the record to add
        @return: True if the record has been added; False otherwise
        """
        return False
