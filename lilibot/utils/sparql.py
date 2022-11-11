from typing import List, Protocol, Dict
import requests

WIKIDATA_SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"
LINGUALIBRE_ENTITY_URI_PREFIX = u"https://lingualibre.org/entity/"
WIKIDATA_ENTITY_URI_PREFIX = u"http://www.wikidata.org/entity/"
COMMONS_FILENAME_URI_PREFIX = u"http://commons.wikimedia.org/wiki/Special:FilePath/"


class SessionWithPost(Protocol):
    def post(self, url, data=None, json=None, **kwargs) -> object:
        ...


class UnknownUriPrefixException(Exception):
    pass


def wikidata_post(query: str, session: SessionWithPost = None) -> List:
    if not session:
        session = requests.Session()

    result = session.post(WIKIDATA_SPARQL_ENDPOINT, data={"format": "json", "query": query})
    return result.json()["results"]["bindings"]


def extract_value_from_uri(uri: str) -> str:
    if uri.startswith(WIKIDATA_ENTITY_URI_PREFIX):
        return uri[len(WIKIDATA_ENTITY_URI_PREFIX):]
    if uri.startswith(LINGUALIBRE_ENTITY_URI_PREFIX):
        return uri[len(LINGUALIBRE_ENTITY_URI_PREFIX):]
    if uri.startswith(COMMONS_FILENAME_URI_PREFIX):
        return uri[len(COMMONS_FILENAME_URI_PREFIX):]
    raise UnknownUriPrefixException(uri)

