#!/usr/bin/python3.8
# -*- coding: utf-8 -*-
# License: GNU GPL v2+

import re
from typing import List

from record import Record
from wikis.wikidata.abstract_wikidata import AbstractWikidata, PRONUNCIATION_PROPERTY

LANG_PROPERTY = "P407"
BRACKET_REGEX = re.compile(r" \([^(]+\)$")


class Wikidata(AbstractWikidata):

    def prepare(self, records: List[Record]) -> List[Record]:
        redirects = {}
        qids = [
            record.links["wikidata"]
            for record in records
            if record.links["wikidata"] is not None
        ]

        while qids:
            redirects = {
                **redirects,
                **self.__resolve_redirects(qids[:50])
            }
            qids = qids[50:]
        for record in records:
            if record.links["wikidata"] is not None:
                qid = record.links["wikidata"]
                if qid in redirects:
                    record.links["wikidata"] = redirects[qid]

        # If a record is linked to an article on Wikipedia but has no linked QID
        # we try to get it through sitelinks
        links = {}
        for record in records:
            if record.links["wikidata"] is None and record.links["wikipedia"] is not None:
                (lang, title) = record.links["wikipedia"].split(":", 1)
                if lang not in links:
                    links[lang] = []
                links[lang] += [title]

        connections = {}
        for lang in links:
            while len(links[lang]) > 0:
                connections = {
                    **connections,
                    **self.__get_ids_from_titles(lang + "wiki", links[lang][:50], lang),
                }
                links[lang] = links[lang][50:]

        for record in records:
            if (
                    record.links["wikidata"] is None
                    and record.links["wikipedia"] is not None
                    and record.links["wikipedia"] in connections
            ):
                record.links["wikidata"] = connections[record.links["wikipedia"]]

        return records

    # Try to use the given record on Wikidata
    def execute(self, record: Record) -> bool:
        wd_link = record.links["wikidata"]
        if wd_link is None:
            return False

        if super().is_already_present(wd_link, record.file):
            print(record.id + ": already on Wikidata")
            return False

        result = self.do_edit(wd_link, record.file, record.language["qid"], record.id, )
        if result:
            print(f"{record.id}: added to Wikidata - https://www.wikidata.org/wiki/{wd_link}#{PRONUNCIATION_PROPERTY}")
            return result

    # Find out if the given items are redirects or not
    def __resolve_redirects(self, qids):
        response = self.api.request(
            {
                "action": "wbgetentities",
                "format": "json",
                "ids": "|".join(qids),
                "props": "info"
            }
        )

        if "entities" not in response:
            return {}

        entities = response["entities"]
        return {
            qid: entities[qid]["redirects"]["to"]
            for qid in entities
            if "redirects" in entities[qid]
        }

    # Try to find the corresponding Wikidata ids of titles (50 max), given
    # the wiki they belong and their language code
    def __get_ids_from_titles(self, dbname, titles, lang):
        response = self.api.request(
            {
                "action": "wbgetentities",
                "format": "json",
                "sites": dbname,
                "titles": "|".join(titles),
                "props": "info|sitelinks|labels",
                "languages": lang,
                "sitefilter": dbname,
            }
        )

        if "entities" not in response:
            return {}

        # Extract and verify each item found
        connections = {}

        entities = response["entities"]
        for qid in entities:
            entity_qid = entities[qid]
            if "labels" not in entity_qid or lang not in entity_qid["labels"]:
                continue

            title = entity_qid["sitelinks"][dbname]["title"]
            label = entity_qid["labels"][lang]["value"]

            # Only make a connections if the WP title is equal to
            # the label on Wikidata
            formated_title = self.format_title(title)
            if formated_title == self.format_title(label):
                connections[f"{lang}:{title}"] = qid
            else:
                print(f"Title and label diverge: {qid} - {formated_title} - {label.lower()}")

        return connections

    @staticmethod
    def format_title(title: str) -> str:
        return BRACKET_REGEX.sub("", title).lower()

    def do_edit(self, entity_id: str, filename: str, language: str, lingualibre_id: str) -> bool:
        return super().do_edit(entity_id, filename, lingualibre_id, '"'
                               + LANG_PROPERTY
                               + '":[{"snaktype":"value","property":"'
                               + LANG_PROPERTY
                               + '","datavalue":{"type":"wikibase-entityid","value":{"id":"'
                               + language
                               + '"}}}]')
