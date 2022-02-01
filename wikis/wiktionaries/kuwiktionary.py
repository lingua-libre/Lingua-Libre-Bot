#!/usr/bin/python3.8
# -*- coding: utf-8 -*-
# Author: Pamputt
# Date: 28 September 2021
# License: GNU GPL v2+

# NOTE:
# python3 llbot.py --wiki kuwiktionary --dryrun simple --langwm ku --item Q379244
# page pour tester l'ajout de section « pron »: porbirr (Q372968)
# page contenant déjà une section « pron » : gûz (Q379244)

import re

import wikitextparser as wtp

from sparql import Sparql
from wikis.wiktionary import Wiktionary

SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"
SUMMARY = "Dengê bilêvkirinê ji Lingua Libre lê hat zêdekirin"

# Do not remove the $1, it is used to force the section to have a content
EMPTY_PRONUNCIATION_SECTION = "=== Bilêvkirin ===\n$1"
PRONUNCIATION_LINE = "\n* {{deng|$2|$1|Deng|dever=$3}}\n"

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
            if record.language["learning"] is not None:
                locations.add(record.language["learning"])
            if record.speaker.residence is not None:
                locations.add(record.speaker.residence)

        # Prepare two location maps
        # One that contains both the city and the country (for all languages but Kurdish)
        # One that contains only the city (only for the Kurdish language)
        self.location_map = {}
        self.location_map_with_country = {}
        raw_location_map = sparql.request(
            LOCATION_QUERY.replace("$1", " wd:".join(locations))
        )
        for line in raw_location_map:
            country = sparql.format_value(line, "countryLabel")
            location = sparql.format_value(line, "locationLabel")
            self.location_map[sparql.format_value(line, "location")] = location
            self.location_map_with_country[sparql.format_value(line, "location")] = country
            if country != location:
                self.location_map_with_country[sparql.format_value(line, "location")] += (
                        " (" + location + ")"
                )

        return records

    # Try to use the given record on the Kurdish Wiktionary
    def execute(self, record):
        transcription = record.transcription

        # Fetch the content of the page having the transcription for title
        (is_already_present, wikicode, basetimestamp) = self.get_entry(transcription, record.file)

        # Whether there is no entry for this record on kuwiktionary
        if not wikicode:
            return False

        # Whether the record is already inside the entry
        if is_already_present:
            print(f"{record.id}//{transcription}: already on kuwiktionary")
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
        pronunciation_section = self.__get_pronunciation_section(language_section)

        # Create the pronunciation section if it doesn't exist
        if pronunciation_section is None:
            pronunciation_section = self.__create_pronunciation_section(language_section)

        # Choose the location to be displayed with the following order
        # 1) place of learning
        # 2) place of residence
        location = ""
        location = record.language["learning"] or record.speaker.residence
        # Add the pronunciation file to the pronunciation subsection
        self.__append_file(
            pronunciation_section,
            record.file,
            record.language["qid"],
            location
        )

        # Save the result
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
                f"{record.id}//{transcription}: added to kuwiktionary - https://ku.wiktionary.org/wiki/{transcription}")

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
    @staticmethod
    def __get_pronunciation_section(wikicode):
        for section in wikicode.sections:
            if section.title is None:
                continue

            if section.title.replace(" ", "").lower() == "bilêvkirin":
                return section

        return None

    # Create a pronunciation subsection
    def __create_pronunciation_section(self, wikicode):
        # The pronunciation section is the first one of the language section
        # It comes just after "=={{ziman|qqq}}=="        
        lang_section = wikicode.sections[0]
        for section in wikicode.sections:
            if section.title is None:
                continue

            # Search for the language section
            if re.search(r'{{ziman\|[a-z]+}}', section.title.replace(" ", "")):
                break

        lang_section = section

        # Add a new line before the pronunciation section only
        # if there is no other section
        section_content = wtp.parse(wikicode.sections[1].contents)
        new_section = EMPTY_PRONUNCIATION_SECTION
        if len(section_content.sections) < 2:
            new_section = new_section.replace("=== Bilêvkirin", "\n=== Bilêvkirin")

        # Append an empty pronunciation section just after the language section
        pattern = r"==="
        lang_section.contents = self.__safe_append_text(
            lang_section.contents, new_section, pattern
        )

        return self.__get_pronunciation_section(wikicode)

    # Add the audio template to the pronunciation section
    def __append_file(self, wikicode, filename, language_qid, location_qid):
        section_content = wtp.parse(wikicode.sections[1].contents)

        location = ""
        if (language_qid == "Q36368" and  # Kurdish language on Wikidata
                location_qid in self.location_map):
            location = self.location_map[location_qid]

        if (language_qid != "Q36368" and
                location_qid in self.location_map_with_country):
            location = self.location_map_with_country[location_qid]

        pronunciation_line = PRONUNCIATION_LINE.replace("$1", filename).replace("$2", self.language_code_map[
            language_qid]).replace("$3", location)
        # Add new lines if there are sections after
        if len(section_content.sections) > 1:
            pronunciation_line += "\n\n"

        pattern = r"==="
        section_content.sections[0].contents = self.__safe_append_text(
            section_content.sections[0].contents,
            pronunciation_line,
            pattern
        )

        wikicode.sections[1].contents = str(section_content)

        # Remove the ugly hack, see comment line 17
        wikicode.sections[1].contents = wikicode.sections[1].contents.replace(
            "$1\n", ""
        )

        # Remove unneeded blank lines
        wikicode.sections[1].contents = wikicode.sections[1].contents.replace(
            "\n\n", ""
        )

    # Append a string to a wikitext string, just after the language section
    # (before any section)
    @staticmethod
    def __safe_append_text(content, text, pattern):
        content = str(content)

        search = re.compile(pattern).search(content)
        index = search.start() if search else len(content)
        return content[:index] + text + content[index:]
