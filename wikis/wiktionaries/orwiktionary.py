#!/usr/bin/python3.8
# -*- coding: utf-8 -*-
# License: GNU GPL v2+

import re
from typing import List

import wikitextparser as wtp

import sparql
from sparql import SPARQL_ENDPOINT

from record import Record

import pywiki
from wikis.wiktionary import Wiktionary, safe_append_text

SUMMARY = "ଲିଙ୍ଗୁଆ ଲିବ୍ରେରୁ ଏକ ଉଚ୍ଚାରଣ ଅଡ଼ିଓ ଯୋଡ଼ିଲି"

# Do not remove the $1, it is used to force the section to have a content
EMPTY_PRONUNCIATION_SECTION = "\n=== ଉଚ୍ଚାରଣ ===\n$1"
PRONUNCIATION_LINE = "\n* {{ଅଡ଼ିଓ|$1|ଧ୍ୱନି (ମାନକ ଓଡ଼ିଆ)|lang=$2}}"
# {{ଅଡ଼ିଓ|Or-ଓଡ଼ିଆ 01.oga|ଧ୍ୱନି|lang=or}}

# To be sure not to miss any title, they are normalized during comparaisons;
# those listed bellow must thereby be without any space
FOLLOWING_SECTIONS = [
    "===ଅର୍ଥ===",
]

LANGUAGE_QUERY = """
SELECT ?item ?code ?itemLabel
WHERE {
    ?item wdt:P305 ?code.
      SERVICE wikibase:label { bd:serviceParam wikibase:language "or, en" . }
}
"""

BOTTOM_REGEX = re.compile(
    r"(?:\s*(?:\[\[(?:Category|ଶ୍ରେଣୀ):[^\]]+\]\])?)*$",
    re.IGNORECASE,
)


class OrWiktionary(Wiktionary):

    def __init__(self, username: str, password: str, dry_run: bool) -> None:
        """
        Constructor.

        Parameters
        ----------
        username
            Username to login to the wiki.
        password
            Password to log into the account.
        """
        super().__init__(username, password, "or", SUMMARY, dry_run)
        self.username = username
        self.password = password

    """
    Public methods
    """

    # Prepare the records to be added on the Odia Wiktionary:
    # - Fetch the needed language code map (Qid -> BCP 47, used by orwiktionary)
    def prepare(self, records: List[Record]) -> List[Record]:
        # Get BCP 47 language code map
        self.language_code_map = {}
        self.language_label_map = {}
        raw_language_code_map = sparql.request(SPARQL_ENDPOINT, LANGUAGE_QUERY)

        for line in raw_language_code_map:
            self.language_code_map[
                sparql.format_value(line, "item")
            ] = sparql.format_value(line, "code")
            self.language_label_map[
                sparql.format_value(line, "item")
            ] = sparql.format_value(line, "itemLabel")

        return records

    # Check if the file always exists on Wikimedia Commons
    # under its original filename (the one know by Lingua Libre
    # wikibase). It may be different because several files have
    # been renamed in the past
    def new_filename_on_Commons(self, filename: str) -> str:
        commons_api = pywiki.Pywiki(self.username, self.password, f"https://commons.wikimedia.org/w/api.php", "user", False)
        response = commons_api.request(
            {
                "action": "query",
                "format": "json",
                "formatversion": "2",
                "letitle": "File:" + filename,
                "list": "logevents",
                "letype": "move",
            }
        )

        if not response["query"]["logevents"]:
            return None
        
        page = response["query"]["logevents"][0]
        #print(f"new_filename_on_commons: {page}")
        if "params" not in page:
            #print(f"Pas de 'params' dans {response}")
            return None

        filename = page["params"]["target_title"]
        if filename.startswith("File:"):
            filename = filename[5:]
        return filename
        
        return None
    
    def exists_on_commons(self, filename: str) -> bool:            
        commons_api = pywiki.Pywiki(self.username, self.password, f"https://commons.wikimedia.org/w/api.php", "user", False)
        response = commons_api.request(
            {
                "action": "query",
                "format": "json",
                "formatversion": "2",
                "titles": "File:" + filename,
            }
        )

        page = response["query"]["pages"][0]
        #print(f"{page}")

        # If no pages have been found on Wikimedia Commons for the given title
        if "missing" in page:
            return False
        
        return True

    # Try to use the given record on the Odia Wiktionary
    def execute(self, record: Record) -> bool:
        transcription = record.transcription
        print(f"Treating {transcription}")

        new_name = self.new_filename_on_Commons(record.file)
        if new_name:
            record.file = new_name
        
        # Check if file exists on Commons
        if not self.exists_on_commons(record.file):
            print(f"{record.file} does not exists anymore on Wikimedia Commons. Maybe moved!")
            return False

        # Fetch the content of the page having the transcription for title
        (is_already_present, wikicode, basetimestamp) = self.get_entry(
            transcription, record.file
        )

        # Whether there is no entry for this record on orwiktionary
        if not wikicode:
            return False

        # Whether the record is already inside the entry
        if is_already_present:
            print(f"{record.id}: already on orwiktionary")
            return False

        # Try to extract the section of the language of the record
        language_section = self.__get_language_section(
            wikicode, record.language["qid"]
        )

        # Whether there is no section for the current language
        if language_section is None:
            print(f"{record.id}//{transcription}: language section not found")
            return False

        # Try to extract the pronunciation subsection
        pronunciation_section = self.get_pronunciation_section(language_section)

        # Create the pronunciation section if it doesn't exist
        if pronunciation_section is None:
            pronunciation_section = self.__create_pronunciation_section(language_section)

        # Add the pronunciation file to the pronunciation section
        self.__append_file(
            pronunciation_section,
            record.file,
            record.language["qid"],
        )

        # Save the result
        result = False
        try:
            result = self.do_edit(transcription, wikicode, basetimestamp)
        except Exception as e:
            # If we got an editconflict, just restart from the beginning
            if "editconflict" in str(e):
                self.execute(record)
            else:
                raise e

        if result:
            print(
                record.id
                + ": added to orwiktionary - https://or.wiktionary.org/wiki/"
                + transcription
            )

        return result

    """
    Private methods
    """

    # Try to extract the language section
    def __get_language_section(self, wikicode, language_qid):
        # Check if the record's language has a BCP 47 code, stop here if not
        if language_qid not in self.language_code_map:
            return None

        lang = self.language_code_map[language_qid]
        langLabel = self.language_label_map[language_qid]

        # Travel across each sections titles to find the one we want
        for section in wikicode.sections:
            if section.title is None:
                continue

            # Examples:
            # * water -> == [[ଇଂରାଜୀ ଭାଷା|ଇଂରାଜୀ]] ==
            # (keep ଇଂରାଜୀ ଭାଷା because this is the Wikidata label)
            # * ଓଡ଼ିଆ -> ==ଓଡ଼ିଆ==
            # * ନାଜର୍ -> == [[ଓଡ଼ିଆ]] ==

            clean_title = section.title
            pos1 = clean_title.find("|")
            if pos1 != -1:
                pos2 = clean_title.find("]]")
                clean_title = clean_title[:pos1] + clean_title[pos2:]
            clean_title = clean_title.replace(" ", "") \
                .replace("[[", "") \
                .replace("]]", "")
            if clean_title == langLabel:
                return section

        # If we arrive here, it means that there is no section for
        # the record's language
        return None

    # Try to extract the pronunciation subsection
    def get_pronunciation_section(self, wikicode):
        for section in wikicode.sections:
            if section.title is None:
                continue

            if section.title.replace(" ", "") == "ଉଚ୍ଚାରଣ":
                return section

        return None

    # Create a pronunciation subsection
    def __create_pronunciation_section(self, wikicode):
        # Travel across the sections until we find a new
        # language section
        # Examples of language section:
        # ==ଓଡ଼ିଆ==  -> Odia language
        # == [[ଇଂରାଜୀ ଭାଷା|ଇଂରାଜୀ]] == -> English language
        prev_section = wikicode.sections[0]
        for section in wikicode.sections:
            if section.title is None:
                continue
            if re.search(r'==.+==', section.title.replace(" ", "")):
                break
            prev_section = section

        # Append an empty pronunciation section to the last section which
        # is not in the following sections list
        prev_section.contents = safe_append_text(
            prev_section.contents, EMPTY_PRONUNCIATION_SECTION, BOTTOM_REGEX
        )

        return self.get_pronunciation_section(wikicode)

    # Add the audio template to the pronunciation section
    def __append_file(self, wikicode, filename, language_qid):
        section_content = wtp.parse(wikicode.sections[1].contents)

        pronunciation_line = PRONUNCIATION_LINE.replace("$1", filename).replace("$2", self.language_code_map[
            language_qid])
        if len(section_content.sections) > 1:
            pronunciation_line += "\n\n"

        section_content.sections[0].contents = safe_append_text(
            section_content.sections[0].contents,
            pronunciation_line,
            BOTTOM_REGEX
        )

        wikicode.sections[1].contents = str(section_content)
