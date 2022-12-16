#!/usr/bin/python3.8
# -*- coding: utf-8 -*-
# License: GNU GPL v2+
import re
import uuid
from abc import ABC, abstractmethod
from typing import List, Dict

from pywiki import NoSuchEntityException
from record import Record
from wikis.wiki import Wiki

MAX_NUMBER_OF_IDS_PER_REQUEST = 50

PRONUNCIATION_PROPERTY = "P443"
LANG_PROPERTY = "P407"
REFURL_PROPERTY = "P854"
SUMMARY = "Add an audio pronunciation file from Lingua Libre"
BRACKET_REGEX = re.compile(r" \([^(]+\)$")


def remove_brackets(title):
    return BRACKET_REGEX.sub("", title).lower()


class Wikibase(Wiki, ABC):

    def __init__(self, username: str, password: str, dry_run: bool) -> None:
        """
        Constructor.
        @param username: Username to login to the wiki
        @param password: Password to log into the account
        """
        super().__init__(username, password, "wikidata", "www", dry_run)

    def execute(self, record: Record) -> bool:
        entity_id = self._get_entity_id(record)

        if entity_id is None:
            return False

        if not self._is_entity_id_valid(entity_id):
            return False

        try:
            if self.__is_already_present(entity_id, record.file):
                print(f'{record.id}: already on Wikidata')
                return False
        except NoSuchEntityException:
            print(f'{record.id}: no such entity')
            return False

        result = self.__do_edit(record)

        if result:
            print(f"{record.id}: added to Wikidata - "
                  f"https://www.wikidata.org/wiki/{self._format_link_for_summary(entity_id)}")

        return result

    @abstractmethod
    def _get_entity_id(self, record: Record) -> str:
        """
        @return: the entity id for the project from the given record
        """

    @abstractmethod
    def _is_entity_id_valid(self, entity_id: str) -> bool:
        """
        Check if the given entity id is a valid id on the project.
        @param entity_id: the entity id to check
        @return: True if the id is correct; False otherwise
        """

    @abstractmethod
    def _build_qualifiers(self, record: Record) -> str:
        return ""

    @abstractmethod
    def _format_link_for_summary(self, link: str) -> str:
        """
        Format the given link that will be logged.
        @param link: the link to format
        @return: a formatted representation of the link
        """

    def __is_already_present(self, entity_id: str, filename: str) -> bool:
        """
        Checks if the given file is already on the page of the given entity.
        @param entity_id: the id of the page to check
        @param filename: the name of the file to check
        @return: True if the file is already on the page; False otherwise
        """
        response = self.api.request(
            {
                "action": "wbgetclaims",
                "format": "json",
                "entity": entity_id,
                "property": PRONUNCIATION_PROPERTY,
            }
        )

        if "claims" not in response:
            return False

        if PRONUNCIATION_PROPERTY not in response["claims"]:
            return False

        claims = response["claims"][PRONUNCIATION_PROPERTY]
        return any(claim["mainsnak"]["datavalue"]["value"] == filename for claim in claims)

    def __do_edit(self, record: Record) -> bool:
        """
        Add the given record in a new claim of the relevant item
        @param record: the record to add
        @return: True if the request is successful; False otherwise
        """
        response = self.api.request(
            {
                "action": "wbsetclaim",
                "format": "json",
                "claim": '{"type":"statement","mainsnak":{"snaktype":"value","property":"'
                         + PRONUNCIATION_PROPERTY
                         + '","datavalue":{"type":"string","value":"'
                         + record.file
                         + '"}},"id":"'
                         + self._get_entity_id(record)
                         + "$"
                         + str(uuid.uuid4())
                         + '","qualifiers":{'
                         + self._build_qualifiers(record)
                         + '},"references":[{"snaks":{"'
                         + REFURL_PROPERTY
                         + '":[{"snaktype":"value","property":"'
                         + REFURL_PROPERTY
                         + '","datavalue":{"type":"string","value":"https://lingualibre.org/wiki/'
                         + record.id
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


class Wikidata(Wikibase):

    def prepare(self, records: List[Record]) -> List[Record]:
        self.__resolve_redirects(records)
        self.__add_qid_from_sitelinks(records)
        return records

    def __resolve_redirects(self, records: List[Record]) -> None:
        qids = [record.links["wikidata"] for record in records if record.links["wikidata"] is not None]

        redirects = {}
        while qids:
            redirects = {
                **redirects,
                **self.__search_redirects(qids[:MAX_NUMBER_OF_IDS_PER_REQUEST])
            }
            qids = qids[MAX_NUMBER_OF_IDS_PER_REQUEST:]

        for record in records:
            if record.links["wikidata"] is None:
                continue

            qid = record.links["wikidata"]
            if qid in redirects:
                record.links["wikidata"] = redirects[qid]

    def __search_redirects(self, qids: List[str]) -> Dict[str, str]:
        """
        Associate to each qid the target of the redirection, if relevant.
        @param qids: a list of qids for which a redirection is searched
        @return: a dictionary of the redirections in which keys are source qids and values are target qids
        """
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
        return {qid: entities[qid]["redirects"]["to"] for qid in entities if "redirects" in entities[qid]}

    def __add_qid_from_sitelinks(self, records: List[Record]) -> None:
        links = {}
        for record in records:
            if record.links["wikidata"] is not None or record.links["wikipedia"] is None:
                continue

            (lang, title) = record.links["wikipedia"].split(":", 1)
            if lang not in links:
                links[lang] = []
            links[lang] += [title]
        connections = {}
        for lang in links:
            while len(links[lang]) > 0:
                connections = {
                    **connections,
                    **self.__get_ids_from_titles(lang + "wiki", links[lang][:MAX_NUMBER_OF_IDS_PER_REQUEST], lang),
                }
                links[lang] = links[lang][MAX_NUMBER_OF_IDS_PER_REQUEST:]
        for record in records:
            if record.links["wikidata"] is not None or record.links["wikipedia"] is None:
                continue
            if record.links["wikipedia"] in connections:
                record.links["wikidata"] = connections[record.links["wikipedia"]]

    def __get_ids_from_titles(self, dbname: str, titles, lang):
        """
        Try to find the corresponding Wikidata ids of titles (50 max),
        given the wiki they belong and their language code
        @param dbname:
        @param titles:
        @param lang:
        @return:
        """
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

        # Extract and verify each item found
        if "entities" not in response:
            return {}

        connections = {}
        for qid in response["entities"]:
            entity = response["entities"][qid]
            if "labels" not in entity or lang not in entity["labels"]:
                continue

            title = entity["sitelinks"][dbname]["title"]
            label = entity["labels"][lang]["value"]

            # Only make a connections if the WP title is equal to the label on Wikidata
            if remove_brackets(title) == remove_brackets(label):
                connections[f'{lang}:{title}'] = qid
            else:
                print(f'Title and label diverge: {qid} - {remove_brackets(title)} - {label.lower()}')

        return connections

    def _get_entity_id(self, record: Record) -> str:
        return record.links["wikidata"]

    def _is_entity_id_valid(self, entity_id: str) -> bool:
        return True

    def _build_qualifiers(self, record: Record) -> str:
        return (
                LANG_PROPERTY
                + '":[{"snaktype":"value","property":"'
                + LANG_PROPERTY
                + '","datavalue":{"type":"wikibase-entityid","value":{"id":"'
                + record.language["qid"]
                + '"}}}]'
        )

    def _format_link_for_summary(self, link: str) -> str:
        return f'{link}#{PRONUNCIATION_PROPERTY}'


class Lexeme(Wikibase):

    def _get_entity_id(self, record: Record) -> str:
        return record.links["lexeme"]

    def _is_entity_id_valid(self, entity_id: str) -> bool:
        if not re.match(r"^L\d+-F\d+$", entity_id):
            print(f'{entity_id} is not a valid lexeme form id')
            return False

        return True

    def _build_qualifiers(self, record: Record) -> str:
        return ""

    def _format_link_for_summary(self, link: str) -> str:
        return f'Lexeme:{link.replace("-", "#")}'
