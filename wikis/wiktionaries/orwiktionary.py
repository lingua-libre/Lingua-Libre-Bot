#!/usr/bin/python3.8
# -*- coding: utf-8 -*-
# Author: Pamputt
# Date: 11 July 2021
# License: GNU GPL v2+

import re
import wikitextparser as wtp

from sparql import Sparql
from wikis.wiktionary import Wiktionary

SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"
SUMMARY = "Ajust d'un fichèr audiò de prononciacion de Lingua Libre estant"

# Do not remove the $1, it is used to force the section to have a content
EMPTY_PRONUNCIATION_SECTION = "\n=== ଉଚ୍ଚାରଣ ===\n$1"
PRONUNCIATION_LINE = "\n* {{ଅଡ଼ିଓ|$1|ଧ୍ୱନି (ମାନକ ଓଡ଼ିଆ)|lang=$2}}"
#{{ଅଡ଼ିଓ|Or-ଓଡ଼ିଆ 01.oga|ଧ୍ୱନି|lang=or}}

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
        super().__init__(user, password, "or", SUMMARY)

    """
    Public methods
    """

    # Prepare the records to be added on the Odia Wiktionary:
    # - Fetch the needed language code map (Qid -> BCP 47, used by orwiktionary)
    def prepare(self, records):
        sparql = Sparql(SPARQL_ENDPOINT)

        # Get BCP 47 language code map
        self.language_code_map = {}
        self.language_label_map = {}
        raw_language_code_map = sparql.request(LANGUAGE_QUERY)

        for line in raw_language_code_map:
            self.language_code_map[
                sparql.format_value(line, "item")
            ] = sparql.format_value(line, "code")
            self.language_label_map[
                sparql.format_value(line, "item")
            ] = sparql.format_value(line, "itemLabel")

        return records

    # Try to use the given record on the Odia Wiktionary
    def execute(self, record):
        transcription = record["transcription"]
        print(f"Treating {transcription}")
        
        # Fetch the content of the page having the transcription for title
        (is_already_present, wikicode, basetimestamp) = self.get_entry(
            transcription, record["file"]
        )

        # Whether there is no entry for this record on orwiktionary
        if not wikicode:
            return False

        # Whether the record is already inside the entry
        if is_already_present:
            print(record["id"] + ": already on ocwiktionary")
            return False

        # Try to extract the section of the language of the record
        language_section = self.get_language_section(
            wikicode, record["language"]["qid"]
        )
        
        # Whether there is no section for the current language
        if language_section is None:
            print(record["id"] + "//" + transcription + ": language section not found")
            return False

        # Try to extract the pronunciation subsection
        pronunciation_section = self.get_pronunciation_section(language_section)

        # Create the pronunciation section if it doesn't exist
        if pronunciation_section is None:
            pronunciation_section = self.create_pronunciation_section(language_section)

        # Add the pronunciation file to the pronunciation section
        self.append_file(
            pronunciation_section,
            record["file"],
            record["language"]["qid"],
        )
        
        # Save the result
        try:
            #result = self.do_edit(transcription, wtp.parse(wikicode), basetimestamp)
            result = self.do_edit(transcription, wikicode, basetimestamp)
        except Exception as e:
            # If we got an editconflict, just restart from the beginning
            if str(e).find("editconflict") > -1:
                self.execute(record)
            else:
                raise e

        if result:
            print(
                record["id"]
                + ": added to orwiktionary - https://or.wiktionary.org/wiki/"
                + transcription
            )

        return result


    """
    Private methods
    """

    # Try to extract the language section
    def get_language_section(self, wikicode, language_qid):
        # Check if the record's language has a BCP 47 code, stop here if not
        if language_qid not in self.language_code_map:
            return None

        lang = self.language_code_map[language_qid]
        langLabel = self.language_label_map[language_qid]

        # Travel across each sections titles to find the one we want
        for section in wikicode.sections:
            if section.title is None:
                continue

            #Examples:
            #* water -> == [[ଇଂରାଜୀ ଭାଷା|ଇଂରାଜୀ]] ==
            #(keep ଇଂରାଜୀ ଭାଷା because this is the Wikidata label)
            #* ଓଡ଼ିଆ -> ==ଓଡ଼ିଆ==
            #* ନାଜର୍ -> == [[ଓଡ଼ିଆ]] ==

            clean_title = section.title
            pos1 = clean_title.find("|")
            if pos1 != -1:
                pos2 = clean_title.find("]]")
                clean_title = clean_title[:pos1]+clean_title[pos2:]
            clean_title = clean_title.replace(" ", "") \
                                     .replace("[[","") \
                                     .replace("]]","")
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
    def create_pronunciation_section(self, wikicode):
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
        prev_section.contents = self.safe_append_text(
            prev_section.contents, EMPTY_PRONUNCIATION_SECTION
        )

        return self.get_pronunciation_section(wikicode)

    # Add the audio template to the pronunciation section
    def append_file(self, wikicode, filename, language_qid):
        section_content = wtp.parse(wikicode.sections[1].contents)

        pronunciation_line = PRONUNCIATION_LINE.replace("$1", filename).replace("$2", self.language_code_map[
            language_qid])
        if len(section_content.sections) > 1:
            pronunciation_line += "\n\n"

        section_content.sections[0].contents = self.safe_append_text(
            section_content.sections[0].contents,
            pronunciation_line,
        )

        wikicode.sections[1].contents = str(section_content)

    # Append a string to a wikitext string, but before any category
    def safe_append_text(self, content, text):
        content = str(content)

        search = BOTTOM_REGEX.search(content)
        if search:
            index = search.start()
        else:
            index = len(content)

        return content[:index] + text + content[index:]
