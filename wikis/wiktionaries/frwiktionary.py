#!/usr/bin/python3.8
# -*- coding: utf-8 -*-
# Author: Antoine "0x010C" Lamielle
# Date: 9 June 2018
# License: GNU GPL v2+

import re
import wikitextparser as wtp

from sparql import Sparql
from wikis.wiktionary import Wiktionary

SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"
SUMMARY = "Ajout d'un fichier audio de prononciation depuis Lingua Libre"

# Do not remove the $1, it is used to force the section to have a content
EMPTY_PRONUNCIATION_SECTION = "\n\n=== {{S|prononciation}} ===\n$1"
PRONUNCIATION_LINE = "\n* {{écouter|$3|$4|lang=$2|audio=$1}}"

# To be sure not to miss any title, they are normalized during comparaisons;
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
    r"(?:\s*(?:\[\[(?:Category|Catégorie):[^\]]+\]\]|{{clé de tri\|[^}]+}})?)*$",
    re.IGNORECASE,
)


class FrWiktionary(Wiktionary):

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
        super().__init__(user, password, "fr", SUMMARY)

    """
    Public methods
    """

    # Prepare the records to be added on the French Wiktionary:
    # - Fetch the needed language code map (Qid -> BCP 47, used by frwiktionary)
    # - Get the labels of the speaker's location in French
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
            if record["language"]["learning"] is not None:
                locations.add(record["language"]["learning"])
            elif record["speaker"]["residence"] is not None:
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

    # Try to use the given record on the French Wiktionary
    def execute(self, record):
        # Normalize the record using frwiktionary's titles conventions
        transcription = self.normalize(record["transcription"])

        # Fetch the content of the page having the transcription for title
        (is_already_present, wikicode, basetimestamp) = self.get_entry(
            transcription, record["file"]
        )

        # Whether there is no entry for this record on frwiktionary
        if not wikicode:
            return False
        '''
        # Whether the record is already inside the entry
        if is_already_present:
            print(record["id"] + "//" + transcription + ": already on frwiktionary")
            return False
        '''
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

        # Get the language level of the speaker and convert it to text
        language_level_id = record["language"]["level"]
        language_level = ""
        if language_level_id:
            if language_level_id == 'Q12':
                language_level = "débutant"
            if language_level_id == 'Q13':
                language_level = "moyen"
            if language_level_id == 'Q14':
                language_level = "bon"
            # do not display anything if "native"
            if language_level_id == 'Q15':
                language_level = ""
        if language_level:
            language_level="|niveau=" + language_level
 
        # Add the pronunciation file to the pronunciation section
        location = ""
        if record["language"]["learning"]:
            location = record["language"]["learning"]
        else:
            location = record["speaker"]["residence"]

        self.append_file(
            pronunciation_section,
            record["file"],
            record["language"]["qid"],
            location,
            language_level
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
                + ": added to frwiktionary - https://fr.wiktionary.org/wiki/"
                + transcription
            )

        return result

    """
    Private methods
    """

    # Normalize the transcription to fit frwiktionary's title conventions
    def normalize(self, transcription):
        return transcription.replace("'", "’")

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

            if section.title.replace(" ", "").lower() == "{{langue|" + lang + "}}":
                return section

                # If we arrive here, it means that there is no section for
                # the record's language
        return None

    # Try to extract the pronunciation subsection
    def get_pronunciation_section(self, wikicode):
        for section in wikicode.sections:
            if section.title is None:
                continue

            if section.title.replace(" ", "").lower() == "{{s|prononciation}}":
                return section

        return None

    # Create a pronunciation subsection
    def create_pronunciation_section(self, wikicode):
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
        prev_section.contents = self.safe_append_text(
            prev_section.contents, EMPTY_PRONUNCIATION_SECTION
        )

        return self.get_pronunciation_section(wikicode)

    # Add the audio template to the pronunciation section
    def append_file(self, wikicode, filename, language_qid, location_qid, language_level):
        section_content = wtp.parse(wikicode.sections[1].contents)

        location = ""
        if location_qid in self.location_map:
            location = self.location_map[location_qid]

        pronunciation_line = PRONUNCIATION_LINE.replace("$1", filename).replace("$2", self.language_code_map[
            language_qid]).replace("$3", location).replace("$4",language_level)

        if len(section_content.sections) > 1:
            pronunciation_line += "\n\n"

        section_content.sections[0].contents = self.safe_append_text(
            section_content.sections[0].contents,
            pronunciation_line,
        )

        # Remove the {{ébauche-pron-audio|fr}} if there was one
        section_content = re.sub("\*?\s*\{\{ébauche-pron-audio\|fr\}\}\s*\n", "", str(section_content))

        wikicode.sections[1].contents = str(section_content)

        # Remove the ugly hack, see comment line 17
        wikicode.sections[1].contents = wikicode.sections[1].contents.replace(
            "$1\n", ""
        )

    # Append a string to a wikitext string, but before any category or sortkey
    def safe_append_text(self, content, text):
        content = str(content)

        search = BOTTOM_REGEX.search(content)
        if search:
            index = search.start()
        else:
            index = len(content)

        return content[:index] + text + content[index:]
