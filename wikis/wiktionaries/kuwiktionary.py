#!/usr/bin/python3.8
# -*- coding: utf-8 -*-
# License: GNU GPL v2+

# NOTE:
# python3 llbot.py --wiki kuwiktionary --dryrun simple --langwm ku --item Q379244
# page pour tester l'ajout de section « pron »: porbirr (Q372968)
# page contenant déjà une section « pron » : gûz (Q379244)

import re

import wikitextparser as wtp

import sparql
from request.record import Record
from sparql import SPARQL_ENDPOINT
from wikis.wiktionary import Wiktionary, safe_append_text, get_locations_from_records, get_pronunciation_section

PRONUNCIATION_SECTION_NAME = "bilêvkirin"

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
BOTTOM_REGEX = re.compile(r"===")


class KuWiktionary(Wiktionary):

    def __init__(self, user: str, password: str, dry_run: bool) -> None:
        """
        Constructor.
        @param user: Username to login to the wiki
        @param password: Password to log into the account
        """
        super().__init__(user, password, "ku", SUMMARY, dry_run, LOCATION_QUERY)

    def fetch_locations(self, records):
        raw_location_map = get_locations_from_records(LOCATION_QUERY, records)
        self.location_map = {}
        self.location_map_with_country = {}
        for line in raw_location_map:
            country = sparql.format_value(line, "countryLabel")
            location = sparql.format_value(line, "locationLabel")
            self.location_map[sparql.format_value(line, "location")] = location
            self.location_map_with_country[sparql.format_value(line, "location")] = country
            if country != location:
                self.location_map_with_country[sparql.format_value(line, "location")] += f" ({location})"

    def fetch_language_codes(self):
        self.language_code_map = {}
        raw_language_code_map = sparql.request(SPARQL_ENDPOINT, LANGUAGE_QUERY)
        for line in raw_language_code_map:
            self.language_code_map[
                sparql.format_value(line, "item")
            ] = sparql.format_value(line, "code")

    # Try to use the given record on the Kurdish Wiktionary
    def execute(self, record: Record) -> bool:
        transcription = record.transcription

        # Fetch the content of the page having the transcription for title
        (is_already_present, wikicode, basetimestamp) = self.get_entry(transcription, record.file)

        # Whether there is no entry for this record on kuwiktionary
        if not wikicode:
            return False

        # Whether the record is already inside the entry
        if is_already_present:
            print(f'{record.id}//{transcription}: already on kuwiktionary')
            return False

        # Try to extract the section of the language of the record
        language_section = self._get_language_section(wikicode, record.language["qid"])

        # Whether there is no section for the current language
        if language_section is None:
            print(f'{record.id}//{transcription}: language section not found')
            return False

        # Try to extract the pronunciation subsection
        pronunciation_section = get_pronunciation_section(language_section, PRONUNCIATION_SECTION_NAME)

        # Create the pronunciation section if it doesn't exist
        if pronunciation_section is None:
            pronunciation_section = self.__create_pronunciation_section(language_section)

        # Choose the location to be displayed with the following order
        # 1) place of learning
        # 2) place of residence
        location = record.language["learning"] or record.speaker_residence

        # Add the pronunciation file to the pronunciation subsection
        self.__append_file(
            pronunciation_section,
            record.file,
            record.language["qid"],
            location
        )

        return self.save_result(basetimestamp, record, transcription, wikicode)

    def get_save_message(self, record, transcription):
        return f'{record.id}//{transcription}: added to kuwiktionary - https://ku.wiktionary.org/wiki/{transcription}'

    def language_section(self, lang):
        return "{{ziman|" + lang + "}}"

    # Create a pronunciation subsection
    def __create_pronunciation_section(self, wikicode):
        # The pronunciation section is the first one of the language section
        # It comes just after "=={{ziman|qqq}}=="
        section = None
        for section in wikicode.sections:
            if section.title is None:
                continue

            # Search for the language section
            if re.search(r'{{ziman\|[a-z]+}}', section.title.replace(" ", "")):
                break

        if not section:
            return
        lang_section = section

        # Add a new line before the pronunciation section only
        # if there is no other section
        section_content = wtp.parse(wikicode.sections[1].contents)
        new_section = EMPTY_PRONUNCIATION_SECTION
        if len(section_content.sections) < 2:
            new_section = new_section.replace("=== Bilêvkirin", "\n=== Bilêvkirin")

        # Append an empty pronunciation section just after the language section
        lang_section.contents = safe_append_text(
            lang_section.contents, new_section, re.compile(r"===")
        )

        return get_pronunciation_section(wikicode, PRONUNCIATION_SECTION_NAME)

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

        section_content.sections[0].contents = safe_append_text(
            section_content.sections[0].contents,
            pronunciation_line,
            BOTTOM_REGEX
        )

        wikicode.sections[1].contents = str(section_content)

        # Remove the ugly hack, see comment line 17
        wikicode.sections[1].contents = wikicode.sections[1].contents.replace("$1\n", "")

        # Remove unneeded blank lines
        wikicode.sections[1].contents = wikicode.sections[1].contents.replace("\n\n", "")
