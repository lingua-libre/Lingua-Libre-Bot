#!/usr/bin/python3.8
# -*- coding: utf-8 -*-
# License: GNU GPL v2+

import re

import wikitextparser as wtp

import pywiki
import sparql
from wikis.wiktionary import Wiktionary

SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"
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

    def __init__(self, username, password, dry_run: bool):
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
    def prepare(self, records):
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
    # under its original filename (the one known in the Lingua Libre
    # wikibase). It may be different because several files have
    # been renamed in the past
    def new_filename_on_Commons(self, filename):
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
        if "params" not in page:
            return None

        filename = page["params"]["target_title"]
        if filename.startswith("File:"):
            filename = filename[5:]
        return filename
        
        return None
    
    def exists_on_commons(self, filename):            
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

        # If no pages have been found on Wikimedia Commons for the given title
        if "missing" in page:
            return False
        
        return True

    # Try to use the given record on the Odia Wiktionary
    def execute(self, record):
        transcription = record.transcription
        print(f"Treating {transcription}")

        # Check whether file has been renamed on Wikimedia Commons
        new_name = self.new_filename_on_Commons(record.file)
        if new_name:
            record.file = new_name
        
        # Check whether file exists on Wikimedia Commons
        if not self.exists_on_commons(record.file):
            #print(f"{record.file} does not exists anymore on Wikimedia Commons. Maybe moved!")
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
        language_section = self.get_language_section(
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
            pronunciation_section = self.create_pronunciation_section(language_section)

                # Count the number of pronunciations already present in the section                                        
        count = 0
        if (pronunciation_section != None and
            len(pronunciation_section.sections) > 1 and
            pronunciation_section.sections[1].contents):
            count = pronunciation_section.sections[1].contents.count('{{deng|')
            # https://or.wiktionary.org/wiki/%E0%AC%AC%E0%AD%8D%E0%AD%9F%E0%AC%AC%E0%AC%B9%E0%AC%BE%E0%AC%B0%E0%AC%95%E0%AC%BE%E0%AC%B0%E0%AD%80%E0%AC%99%E0%AD%8D%E0%AC%95_%E0%AC%86%E0%AC%B2%E0%AD%8B%E0%AC%9A%E0%AC%A8%E0%AC%BE:Psubhashish#Lingua_Libre_Bot

            if count >= 5:
                file1 = open('orwiktionary_more_than_5_pron.txt', 'a')
                file1.write(f'{record.language["qid"]}/{transcription}: {count}\n')
                file1.close()
                print(f'{transcription}: more than 5 pronunciations; skip')
                return 
            
        # Add the pronunciation file to the pronunciation section
        if (count < 5):
            self.append_file(
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
        index = search.start() if search else len(content)
        return content[:index] + text + content[index:]
