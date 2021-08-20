#!/usr/bin/python3.8
# -*- coding: utf-8 -*-
# Author: Pamputt
# Date: 11 August 2021
# License: GNU GPL v2+

import re
import wikitextparser as wtp

from sparql import Sparql
from wikis.wiktionary import Wiktionary

SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"
SUMMARY = "Dengê bilêvkirinê ji Lingua Libre lê hat zêdekirin"

# Do not remove the $1, it is used to force the section to have a content
EMPTY_PRONUNCIATION_SECTION = "\n\n=== Bilêvkirin ===\n$1"
PRONUNCIATION_LINE = "\n* {{deng|$2|$1|Deng|dever=$3}}"

LANGUAGE_QUERY = "SELECT ?item ?code WHERE { ?item wdt:P305 ?code. }"
LOCATION_QUERY = """
SELECT ?location ?locationLabel ?countryLabel
WHERE {
  ?location wdt:P17 ?country.
  SERVICE wikibase:label { bd:serviceParam wikibase:language "ku,en" . }
  VALUES ?location { wd:$1 }
}
"""


class KuWiktionary(Wiktionary):

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
        super().__init__(user, password, "ku", SUMMARY)

    """
    Public methods
    """

    # Prepare the records to be added on the Kurdish Wiktionary:
    # - Fetch the needed language code map (Qid -> BCP 47, used by kuwiktionary)
    # - Get the labels of the speaker's location in Kurdish
    def prepare(self, records):
        sparql = Sparql(SPARQL_ENDPOINT)

        # Get BCP 47 language code map
        self.language_code_map = {}
        raw_language_code_map = sparql.request(LANGUAGE_QUERY)

        for line in raw_language_code_map:
            self.language_code_map[
                sparql.format_value(line, "item")
            ] = sparql.format_value(line, "code")

            # Extract all different locations
        locations = set()
        for record in records:
            if record["speaker"]["residence"] is not None:
                locations.add(record["speaker"]["residence"])

        self.location_map = {}
        raw_location_map = sparql.request(
            LOCATION_QUERY.replace("$1", " wd:".join(locations))
        )
        for line in raw_location_map:
            country = sparql.format_value(line, "countryLabel")
            location = sparql.format_value(line, "locationLabel")
            self.location_map[sparql.format_value(line, "location")] = country
            if country != location:
                self.location_map[sparql.format_value(line, "location")] += (
                        " (" + location + ")"
                )

        return records

    # Try to use the given record on the Kurdish Wiktionary
    def execute(self, record):
        transcription = record["transcription"]
        
        # Fetch the content of the page having the transcription for title
        (is_already_present, wikicode, basetimestamp) = self.get_entry(
            transcription, record["file"]
        )
        if not is_already_present:
            print(f"--- BEFORE ---\n{wikicode}\n")
            print("--- END BEFORE ---")

        # Whether there is no entry for this record on kuwiktionary
        if not wikicode:
            return False

        # Whether the record is already inside the entry
        if is_already_present:
            print(record["id"] + "//" + transcription + ": already on kuwiktionary")
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
        print(f"--- PRON SECTION ---\n{pronunciation_section}\n--- END PRON SECTION ---")
        pronunciation_section = self.clean_section(pronunciation_section)
        print(f"--- PRON SECTION ---\n{pronunciation_section}\n--- END PRON SECTION ---")

        # Create the pronunciation section if it doesn't exist
        if pronunciation_section is None:
            pronunciation_section = self.create_pronunciation_section(language_section)

        # Add the pronunciation file to the pronunciation section
        self.append_file(
            pronunciation_section,
            record["file"],
            record["language"]["qid"],
            record["speaker"]["residence"],
        )

        # Save the result
        try:
            result = self.do_edit(transcription, wikicode, basetimestamp)
        except Exception as e:
            # If we got an editconflict, just restart from the beginning
            if str(e).find("editconflict") > -1:
                self.execute(record)
            else:
                raise e

        if result:
            print(
                record["id"] + "//" + transcription
                + ": added to kuwiktionary - https://ku.wiktionary.org/wiki/"
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

        # Travel across each sections titles to find the one we want
        for section in wikicode.sections:
            if section.title is None:
                continue

            if section.title.replace(" ", "").lower() == "{{ziman|" + lang + "}}":
                return section

        # If we arrive here, it means that there is no section for
        # the record's language
        return None

    # Try to extract the pronunciation subsection
    def get_pronunciation_section(self, wikicode):
        for section in wikicode.sections:
            if section.title is None:
                continue

            if section.title.replace(" ", "").lower() == "bilêvkirin":
                return section

        return None

    # Create a pronunciation subsection
    def create_pronunciation_section(self, wikicode):
        # The pronunciation section is the first one of the language section
        # It comes just after "=={{ziman|qqq}}=="        
        lang_section = wikicode.sections[0]
        for section in wikicode.sections:
            if section.title is None:
                continue
            
            # Search for the language section
            if re.search(r'\{\{ziman\|[a-z]+\}\}', section.title.replace(" ", "")):
                print(f"FOUND -> {section}")
                break

            lang_section = section

        # Append an empty pronunication section just after the language section
        lang_section.contents = self.safe_append_text(
            lang_section.contents, EMPTY_PRONUNCIATION_SECTION
        )
        
        return self.get_pronunciation_section(wikicode)

    # Add the audio template to the pronunciation section
    def append_file(self, wikicode, filename, language_qid, location_qid):
        section_content = wtp.parse(wikicode.sections[1].contents)

        location = ""
        if location_qid in self.location_map:
            location = self.location_map[location_qid]

        pronunciation_line = PRONUNCIATION_LINE.replace("$1", filename).replace("$2", self.language_code_map[
            language_qid]).replace("$3", location)
        if len(section_content.sections) > 1:
            pronunciation_line += "\n\n"

        section_content.sections[0].contents = self.safe_append_text(
            section_content.sections[0].contents,
            pronunciation_line,
        )

        wikicode.sections[1].contents = str(section_content)

        '''
        # Remove the ugly hack, see comment line 17
        wikicode.sections[1].contents = wikicode.sections[1].contents.replace(
            "$1\n", ""
        )
        '''

    # Append a string to a wikitext string, just after the language section
    # (before any section)
    def safe_append_text(self, content, text):
        content = str(content)

        search = re.compile(r"===").search(content)
        if search:
            index = search.start()
        else:
            index = len(content)

        return content[:index] + text + content[index:]

    # Remove blank lines at the end of the section
    def clean_section(self, section):
        new_content = "=== " + section.title + " ===\n"
        content = section.contents
        
        for line in content.split("\n"):
            print(f"{line} -> {len(line)}")
            print(new_content)
            if len(line) > 0:
                new_content += line + "\n"

        return new_content + "\n"
