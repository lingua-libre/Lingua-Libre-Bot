#!/usr/bin/python3.8
# -*- coding: utf-8 -*-
# License: GNU GPL v2+

import re

from record import Record
from wikis.wikidata.abstract_wikidata import AbstractWikidata


class Lexemes(AbstractWikidata):

    def execute(self, record: Record) -> bool:
        lexeme_link = record.links["lexeme"]
        if lexeme_link is None:
            return False

        if not re.match(r"^L\d+-F\d+$", lexeme_link):
            print(f"{lexeme_link} is not a valid lexeme form id")

        if super().is_already_present(lexeme_link, record.file):
            print(f"{record.id}: already on Wikidata")
            return False

        result = self.__do_edit(lexeme_link, record.file, record.id)
        if result:
            print(
                record.id
                + ": added to Wikidata - https://www.wikidata.org/wiki/Lexeme:"
                + lexeme_link.replace("-", "#")
            )

        return result

    def do_edit(self, entity_id: str, filename: str, lingualibre_id: str) -> bool:
        return super().do_edit(entity_id, filename, lingualibre_id, "")
