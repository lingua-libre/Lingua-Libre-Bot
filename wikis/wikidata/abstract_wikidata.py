import re
from abc import ABC

import uuid

from wikis.wikifamily import WikiFamily

PRONUNCIATION_PROPERTY = "P443"
REFURL_PROPERTY = "P854"
SUMMARY = "Add an audio pronunciation file from Lingua Libre"


class AbstractWikidata(WikiFamily, ABC):
    def __init__(self, user: str, password: str):
        super().__init__(user, password, "wikidata", "www")

    def is_already_present(self, entity_id, filename):
        """
        Check whether the given record is already present in a claim of the given item.
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

        if PRONUNCIATION_PROPERTY not in response["claims"]:
            return False

        return any(
            claim["mainsnak"]["datavalue"]["value"] == filename
            for claim in response["claims"][PRONUNCIATION_PROPERTY]
        )

    def do_edit(self, entity_id: str, filename: str, lingualibre_id: str, qualifiers: str) -> bool:
        """
        Add the given record in a new claim of the given item.
        @param entity_id:
        @param filename:
        @param lingualibre_id:
        @param qualifiers:
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
                         + '","qualifiers":{' + qualifiers + '},"references":[{"snaks":{"'
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
