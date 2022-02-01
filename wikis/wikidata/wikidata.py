#!/usr/bin/python3.8
# -*- coding: utf-8 -*-
# Author: Antoine "0x010C" Lamielle
# Date: 9 June 2018
# License: GNU GPL v2+

import re
import uuid

from wikis.wikifamily import WikiFamily

PRONUNCIATION_PROPERTY = "P443"
LANG_PROPERTY = "P407"
REFURL_PROPERTY = "P854"
SUMMARY = "Add an audio pronunciation file from Lingua Libre"
BRACKET_REGEX = re.compile(r" \([^(]+\)$")


class Wikidata(WikiFamily):

    def __init__(self, user, password):
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

    """
    Public methods
    """

    def prepare(self, records):
        # Resolve all redirects
        qids = []
        redirects = {}
        for record in records:
            if record["links"]["wikidata"] is not None:
                qids += [record["links"]["wikidata"]]
        while len(qids) > 0:
            redirects = {
                **redirects,
                **self.resolve_redirects(qids[:50])
            }
            qids = qids[50:]
        for record in records:
            if record["links"]["wikidata"] is not None:
                qid = record["links"]["wikidata"]
                if qid in redirects:
                    record["links"]["wikidata"] = redirects[qid]

        # If a record is linked to an article on Wikipedia but has no linked QID
        # we try to get it through sitelinks
        links = {}
        for record in records:
            if (
                    record["links"]["wikidata"] is None
                    and record["links"]["wikipedia"] is not None
            ):
                (lang, title) = record["links"]["wikipedia"].split(":", 1)
                if lang not in links:
                    links[lang] = []
                links[lang] += [title]

        connections = {}
        for lang in links:
            while len(links[lang]) > 0:
                connections = {
                    **connections,
                    **self.get_ids_from_titles(lang + "wiki", links[lang][:50], lang),
                }
                links[lang] = links[lang][50:]

        for record in records:
            if (
                    record["links"]["wikidata"] is None
                    and record["links"]["wikipedia"] is not None
            ):
                if record["links"]["wikipedia"] in connections:
                    record["links"]["wikidata"] = connections[
                        record["links"]["wikipedia"]
                    ]

        return records

    # Try to use the given record on Wikidata
    def execute(self, record):
        if record["links"]["wikidata"] is None:
            return False

        if self.is_already_present(record["links"]["wikidata"], record["file"]):
            print(record["id"] + ": already on Wikidata")
            return False

        result = self.do_edit(
            record["links"]["wikidata"],
            record["file"],
            record["language"]["qid"],
            record["id"],
        )
        if result is True:
            print(
                record["id"]
                + ": added to Wikidata - https://www.wikidata.org/wiki/"
                + record["links"]["wikidata"]
                + "#"
                + PRONUNCIATION_PROPERTY
            )

        return result

    """
    Private methods
    """

    # Find out if the given items are redirects or not
    def resolve_redirects(self, qids):
        response = self.api.request(
            {
                "action": "wbgetentities",
                "format": "json",
                "ids": "|".join(qids),
                "props": "info"
            }
        )

        redirects = {}
        if "entities" in response:
            for qid in response["entities"]:
                if "redirects" in response["entities"][qid]:
                    redirects[qid] = response["entities"][qid]["redirects"]["to"]

        return redirects

    # Try to find the corresponding Wikidata ids of titles (50 max), given
    # the wiki they belong and their language code
    def get_ids_from_titles(self, dbname, titles, lang):
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
        connections = {}
        if "entities" in response:
            for qid in response["entities"]:
                if (
                        "labels" in response["entities"][qid]
                        and lang in response["entities"][qid]["labels"]
                ):
                    title = response["entities"][qid]["sitelinks"][dbname]["title"]
                    label = response["entities"][qid]["labels"][lang]["value"]

                    # Only make a connections if the WP title is equal to
                    # the label on Wikidata
                    if (
                            BRACKET_REGEX.sub("", title).lower()
                            == BRACKET_REGEX.sub("", label).lower()
                    ):
                        connections[lang + ":" + title] = qid
                    else:
                        print(
                            "Title and label diverge: "
                            + qid
                            + " - "
                            + BRACKET_REGEX.sub("", title).lower()
                            + " - "
                            + label.lower()
                        )

        return connections

        # Check whether the given record is already present in a claim of the given item

    def is_already_present(self, entityId, filename):
        response = self.api.request(
            {
                "action": "wbgetclaims",
                "format": "json",
                "entity": entityId,
                "property": PRONUNCIATION_PROPERTY,
            }
        )

        if PRONUNCIATION_PROPERTY in response["claims"]:
            for claim in response["claims"][PRONUNCIATION_PROPERTY]:
                if claim["mainsnak"]["datavalue"]["value"] == filename:
                    return True
        return False

        # Add the given record in a new claim of the given item

    def do_edit(self, entityId, filename, language, lingualibreId):
        response = self.api.request(
            {
                "action": "wbsetclaim",
                "format": "json",
                "claim": '{"type":"statement","mainsnak":{"snaktype":"value","property":"'
                         + PRONUNCIATION_PROPERTY
                         + '","datavalue":{"type":"string","value":"'
                         + filename
                         + '"}},"id":"'
                         + entityId
                         + "$"
                         + str(uuid.uuid4())
                         + '","qualifiers":{"'
                         + LANG_PROPERTY
                         + '":[{"snaktype":"value","property":"'
                         + LANG_PROPERTY
                         + '","datavalue":{"type":"wikibase-entityid","value":{"id":"'
                         + language
                         + '"}}}]},"references":[{"snaks":{"'
                         + REFURL_PROPERTY
                         + '":[{"snaktype":"value","property":"'
                         + REFURL_PROPERTY
                         + '","datavalue":{"type":"string","value":"https://lingualibre.org/wiki/'
                         + lingualibreId
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
