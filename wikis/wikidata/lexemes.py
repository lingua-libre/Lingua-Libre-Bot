#!/usr/bin/python3.8
# -*- coding: utf-8 -*-
# Author: Sylvain Boissel
# Date: 16 December 2018
# License: GNU GPL v2+

import re
import uuid

from record import Record
from wikis.wikifamily import WikiFamily

PRONUNCIATION_PROPERTY = "P443"
REFURL_PROPERTY = "P854"
SUMMARY = "Add an audio pronunciation file from Lingua Libre"
BRACKET_REGEX = re.compile(r" \([^(]+\)$")


class Lexemes(WikiFamily):

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
        super().__init__(user, password, "wikidata", "www")

    def execute(self, record: Record) -> bool:
        if record.links["lexeme"] is None:
            return False

        if not re.match(r"^L\d+-F\d+$", record.links["lexeme"]):
            print(record.links["lexeme"] + "is not a valid lexeme form id")

        if self.__is_already_present(record.links["lexeme"], record.file):
            print(f"{record.id}: already on Wikidata")
            return False

        result = self.__do_edit(
            record.links["lexeme"],
            record.file,
            record.id,
        )
        if result:
            print(
                record.id
                + ": added to Wikidata - https://www.wikidata.org/wiki/Lexeme:"
                + record.links["lexeme"].replace("-", "#")
            )

        return result

    def __is_already_present(self, entity_id: str, filename: str) -> bool:
        """

        @param entity_id:
        @param filename:
        @return:
        """
        response = self.api.request(
            {
                "action": "wbgetclaims",
                "format": "json",
                "entity": entity_id,
                "property": PRONUNCIATION_PROPERTY,
            }
        )

        if PRONUNCIATION_PROPERTY in response["claims"]:
            for claim in response["claims"][PRONUNCIATION_PROPERTY]:
                if claim["mainsnak"]["datavalue"]["value"] == filename:
                    return True
        return False

    def __do_edit(self, entity_id: str, filename: str, lingualibre_id: str) -> bool:
        """
        Add the given record in a new claim of the given item.
        @param entity_id:
        @param filename:
        @param lingualibre_id:
        @return:
        """
        response = self.api.request(
            {
                "action": "wbsetclaim",
                "format": "json",
                "claim": '{"type":"statement","mainsnak":{"snaktype":"value","property":"'
                         + PRONUNCIATION_PROPERTY
                         + '","datavalue":{"type":"string","value":"'
                         + filename
                         + '"}},"id":"'
                         + entity_id
                         + "$"
                         + str(uuid.uuid4())
                         + '","qualifiers":{},"references":[{"snaks":{"'
                         + REFURL_PROPERTY
                         + '":[{"snaktype":"value","property":"'
                         + REFURL_PROPERTY
                         + '","datavalue":{"type":"string","value":"https://lingualibre.org/wiki/'
                         + lingualibre_id
                         + '"}}]}}],"rank":"normal"}',
                "summary": SUMMARY,
                "token": self.api.get_csrf_token(),
                "bot": 1,
            }
        )

        if "success" in response:
            return True

        print(response)
        return False
