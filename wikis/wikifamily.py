#!/usr/bin/python3.8
# -*- coding: utf-8 -*-
# Author: Florian "Poslovitch" Cuny
# Date: 5 June 2021
# License: GNU GPL v2+

import abc

import pywiki


class WikiFamily(abc.ABC):
    """
    Provides the backbone of the implementation of the bot on any family of wikis.
    This abstract class provides a frame with the basic variables and methods.
    It MUST be inherited from by a subclass that will implement wiki-specific operations
    (such as Wiktionary for the Wiktionaries).
    """

    def __init__(self, user, password, wiki_family: str, language_domain: str):
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

    def prepare(self, records):
        return records

    """
    Abstract methods
    """

    @abc.abstractmethod
    def execute(self, record):
        return None
