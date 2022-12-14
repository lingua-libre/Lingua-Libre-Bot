#!/usr/bin/python3.8
# -*- coding: utf-8 -*-
# License: GNU GPL v2+

import re

import wikitextparser as wtp

import sparql
from request.record import Record
from sparql import SPARQL_ENDPOINT
from wikis.wiktionary import Wiktionary, replace_apostrophe, safe_append_text

SUMMARY = "Ajout d'un fichier audio de prononciation depuis [[Lingua Libre]]"

# Do not remove the $1, it is used to force the section to have a content
EMPTY_PRONUNCIATION_SECTION = "\n\n=== {{S|prononciation}} ===\n$1"
PRONUNCIATION_LINE = "\n* {{écouter|$3|$4|lang=$2|audio=$1}}"

# To be sure not to miss any title, they are normalized during comparisons;
# those listed below must thereby be in lower case and without any space
FOLLOWING_SECTIONS = [
    "{{s|anagrammes}}",
    "{{s|anagr}}",
    "{{s|voiraussi}}",
    "{{s|voir}}",
    "{{s|références}}",
    "{{s|réf}}",
]

LANGUAGE_QUERY = "SELECT ?item ?code WHERE { ?item wdt:P305 ?code. }"
LOCATION_QUERY = """
SELECT ?location ?locationLabel ?countryLabel
WHERE {
  ?location wdt:P17 ?country.
  SERVICE wikibase:label { bd:serviceParam wikibase:language "fr,en" . }
  VALUES ?location { wd:$1 }
}
"""

BOTTOM_REGEX = re.compile(
    r"(?:\s*(?:\[\[(?:Category|Catégorie):[^]]+]]|{{clé de tri\|[^}]+}})?)*$",
    re.IGNORECASE,
)


class FrWiktionary(Wiktionary):

    def __init__(self, user: str, password: str, dry_run: bool) -> None:
        """
        Constructor.
        @param user: Username to login to the wiki
        @param password: Password to log into the account
        """
        super().__init__(user, password, "fr", SUMMARY, dry_run, LOCATION_QUERY)

    def compute_location_label(self, country, location):
        return country if country == location else f"{location} ({country})"

    def fetch_language_codes(self):
        self.language_code_map = {}
        raw_language_code_map = sparql.request(SPARQL_ENDPOINT, LANGUAGE_QUERY)
        for line in raw_language_code_map:
            self.language_code_map[
                sparql.format_value(line, "item")
            ] = sparql.format_value(line, "code")

    # Try to use the given record on the French Wiktionary
    def execute(self, record: Record) -> bool:
        # Normalize the record using frwiktionary's titles conventions
        transcription = replace_apostrophe(record.transcription)

        # Fetch the content of the page having the transcription for title
        is_already_present, wikicode, basetimestamp = self.get_entry(transcription, record.file)

        # Whether there is no entry for this record on frwiktionary
        if not wikicode:
            return False

        # Whether the record is already inside the entry
        if is_already_present:
            print(f'{record.id}//{transcription}: already on frwiktionary')
            return False

        # Try to extract the section of the language of the record
        language_section = self._get_language_section(wikicode, record.language["qid"])

        # Whether there is no section for the current language
        if language_section is None:
            print(f'{record.id}//{transcription}: language section not found')
            return False

        # Try to extract the pronunciation subsection
        pronunciation_section = self._get_pronunciation_section(language_section)

        # Create the pronunciation section if it doesn't exist
        if pronunciation_section is None:
            pronunciation_section = self.__create_pronunciation_section(language_section)

        # Get the language level of the speaker and convert it to text
        language_level_id = record.language["level"]
        language_level = ""
        if language_level_id:
            if language_level_id == 'Q12':
                language_level = "débutant"
            elif language_level_id == 'Q13':
                language_level = "moyen"
            elif language_level_id == 'Q14':
                language_level = "bon"
            elif language_level_id == 'Q15':
                language_level = ""
        if language_level:
            language_level = f"|niveau={language_level}"

        # Add the pronunciation file to the pronunciation section
        location = record.language["learning"] or record.speaker_residence
        self.__append_file(
            pronunciation_section,
            record.file,
            record.language["qid"],
            location,
            language_level
        )

        return self.save_result(basetimestamp, record, transcription, wikicode)

    def get_save_message(self, record, transcription):
        return f'{record.id}//{transcription}: added to frwiktionary - https://fr.wiktionary.org/wiki/{transcription}'

    def language_section(self, lang):
        return "{{langue|" + lang + "}}"

    # Try to extract the pronunciation subsection
    def _get_pronunciation_section(self, wikicode):
        for section in wikicode.sections:
            if section.title is None:
                continue

            if section.title.replace(" ", "").lower() == "{{s|prononciation}}":
                return section

        return None

    # Create a pronunciation subsection
    def __create_pronunciation_section(self, wikicode):
        # The sections order is fixed, etymology, word type (and it's many
        # subsections, pronunciation, anagram, see also and references)
        # Travel across the sections until we find one which comes after
        # the pronunciation section
        prev_section = wikicode.sections[0]
        for section in wikicode.sections:
            if section.title is None:
                continue
            if section.title.replace(" ", "").lower() in FOLLOWING_SECTIONS:
                break
            prev_section = section

        # Append an empty pronunication section to the last section which
        # is not in the following sections list
        prev_section.contents = safe_append_text(
            prev_section.contents, EMPTY_PRONUNCIATION_SECTION, BOTTOM_REGEX
        )

        return self._get_pronunciation_section(wikicode)

    # Add the audio template to the pronunciation section
    def __append_file(self, wikicode, filename, language_qid, location_qid, language_level):
        section_content = wtp.parse(wikicode.sections[1].contents)

        location = ""
        if location_qid in self.location_map:
            location = self.location_map[location_qid]

        pronunciation_line = PRONUNCIATION_LINE.replace("$1", filename).replace("$2", self.language_code_map[
            language_qid]).replace("$3", location).replace("$4", language_level)

        if len(section_content.sections) > 1:
            pronunciation_line += "\n\n"

        section_content.sections[0].contents = safe_append_text(
            section_content.sections[0].contents,
            pronunciation_line,
            BOTTOM_REGEX
        )

        # Remove the {{ébauche-pron-audio|fr}} if there was one
        section_content = re.sub(r"\*?\s*{{ébauche-pron-audio\|fr}}\s*\n", "", str(section_content))

        wikicode.sections[1].contents = str(section_content)

        # Remove the ugly hack, see comment line 17
        wikicode.sections[1].contents = wikicode.sections[1].contents.replace("$1\n", "")
