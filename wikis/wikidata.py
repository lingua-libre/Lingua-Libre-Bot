#!/usr/bin/python3.8
# -*- coding: utf-8 -*-
# License: GNU GPL v2+
import abc
import re
import uuid

from wikis.wikifamily import WikiFamily

PRONUNCIATION_PROPERTY = "P443"
LANG_PROPERTY = "P407"
REFURL_PROPERTY = "P854"
SUMMARY = "Add an audio pronunciation file from Lingua Libre"
BRACKET_REGEX = re.compile(r" \([^(]+\)$")


def remove_brackets(title):
    return BRACKET_REGEX.sub("", title).lower()


class AbcWikidata(WikiFamily, abc.ABC):
    def __init__(self, user: str, password: str) -> None:
        """
        Constructor.
        @param user: Username to login to the wiki
        @param password: Password to log into the account
        """
        super().__init__(user, password, "wikidata", "www")

    @abc.abstractmethod
    def _get_wiki_name(self):
        ...

    def _is_link_valid(self, record) -> bool:
        return True

    def _is_already_present(self, entity_id: str, filename: str) -> bool:
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

    def execute(self, record) -> bool:
        wiki = self._get_wiki_name()
        link = record["links"][wiki]

        if link is None:
            return False

        if not self._is_link_valid(link):
            return False

        if self._is_already_present(link, record["file"]):
            print(record["id"] + ": already on Wikidata")
            return False

        qualifiers = self._build_qualifiers(record)

        result = self._do_edit(
            link,
            record["file"],
            record["id"],
            qualifiers
        )

        if result:
            print(f"{record['id']}: added to Wikidata - "
                  f"https://www.wikidata.org/wiki/{self._get_edit_link(link)}")

        return result

    def _do_edit(self, entity_id: str, filename: str, lingualibre_id: str, qualifiers: str) -> bool:
        """
        Add the given record in a new claim of the given item
        @param entity_id: The id of the entity to edit
        @param filename: The name of the file to add to the entity
        @param lingualibre_id: The id of the element in Lingua Libre
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
                         + '","qualifiers":{'
                         + qualifiers
                         + '},"references":[{"snaks":{"'
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

    def _build_qualifiers(self, record):
        return ""

    @abc.abstractmethod
    def _get_edit_link(self, link: str) -> str:
        ...


class Wikidata(AbcWikidata):

    def prepare(self, records):
        """
        Prepare all the records for their use on Wikidata
        @param records:
        @return:
        """
        # Resolve all redirects
        qids = []
        redirects = {}
        for record in records:
            if record["links"]["wikidata"] is not None:
                qids += [record["links"]["wikidata"]]

        while len(qids) > 0:
            redirects = {
                **redirects,
                **self.__resolve_redirects(qids[:50])
            }
            qids = qids[50:]

        for record in records:
            if record["links"]["wikidata"] is None:
                continue

            qid = record["links"]["wikidata"]
            if qid in redirects:
                record["links"]["wikidata"] = redirects[qid]

        # If a record is linked to an article on Wikipedia but has no linked QID
        # we try to get it through sitelinks
        links = {}
        for record in records:
            if not (record["links"]["wikidata"] is None and record["links"]["wikipedia"] is not None):
                continue

            (lang, title) = record["links"]["wikipedia"].split(":", 1)
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
            if not (record["links"]["wikidata"] is None and record["links"]["wikipedia"] is not None):
                continue
            if record["links"]["wikipedia"] in connections:
                record["links"]["wikidata"] = connections[record["links"]["wikipedia"]]

        return records

    def __resolve_redirects(self, qids):
        """
        Find out if the given items are redirects or not
        @param qids:
        @return:
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
        return {
            qid: entities[qid]["redirects"]["to"]
            for qid in entities
            if "redirects" in entities[qid]
        }

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

    def _get_wiki_name(self) -> str:
        return "wikidata"

    def _build_qualifiers(self, record):
        return (
                LANG_PROPERTY
                + '":[{"snaktype":"value","property":"'
                + LANG_PROPERTY
                + '","datavalue":{"type":"wikibase-entityid","value":{"id":"'
                + record["language"]["qid"]
                + '"}}}]'
        )

    def _get_edit_link(self, link):
        return f'{link}#{PRONUNCIATION_PROPERTY}'


class Lexemes(AbcWikidata):

    def _is_link_valid(self, link: str) -> bool:
        if not re.match(r"^L\d+-F\d+$", link):
            print(f'{link} is not a valid lexeme form id')
            return False

        return True

    def _get_wiki_name(self) -> str:
        return "lexeme"

    def _get_edit_link(self, link: str) -> str:
        return f'Lexeme:{link.replace("-", "#")}'
