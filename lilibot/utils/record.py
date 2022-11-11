from dataclasses import dataclass
from typing import Dict, List, Optional
from utils import sparql


@dataclass
class Record:
    id: str
    file: str
    transcription: str
    speaker_residence: str
    links: Dict[str, str]
    language: Dict[str, str]


def create_record(bindings: Dict[str, Dict[str, str]]) -> Record:
    """
    Create a record from bindings.
    @param bindings: bindings, representing data for a record, usually retrieved from a SPARQL query
    @return: a record
    """
    return Record(
        id=sparql.extract_value_from_uri(bindings["record"]["value"]),
        file=sparql.extract_value_from_uri(bindings["file"]["value"]),
        transcription=bindings["transcription"]["value"],
        speaker_residence=bindings["residence"]["value"],
        links=extract_links_from_bindings(bindings),
        language={
            "qid": bindings["languageQid"]["value"],
            "learning": bindings["learningPlace"]["value"],
            "level": sparql.extract_value_from_uri(bindings["languageLevel"]["value"])
        }
    )


def create_records(bindings: List[Dict[str, Dict[str, str]]]) -> List[Record]:
    """
    Create a record for each of the specified bindings.
    @param bindings: list of bindings, each one of them representing data for a single record,
    usually retrieved from a SPARQL query
    @return: a list of records
    """
    return [create_record(binding) for binding in bindings]


def extract_links_from_bindings(bindings: Dict[str, Dict[str, str]]) -> Dict[str, str]:
    """
    Extract links to Wikimedia sites out of the specified bindings.
    @param bindings: bindings, representing data for a record, usually retrieved from a SPARQL query
    @return: a dictionary of links to Wikimedia sites for the given bindings
    """
    res = {}
    if "wikipediaTitle" in bindings:
        res["wikipedia"] = bindings["wikipediaTitle"]["value"]
    if "wiktionaryEntry" in bindings:
        res["wiktionary"] = bindings["wiktionaryEntry"]["value"]
    if "lexemeId" in bindings:
        res["lexeme"] = bindings["lexemeId"]["value"]
    if "wikidataId" in bindings:
        res["wikidata"] = bindings["wikidataId"]["value"]
    return res
