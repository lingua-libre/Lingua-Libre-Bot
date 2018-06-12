#!/usr/bin/python3.5
# -*- coding: utf-8 -*-
#Autor: Antoine "0x010C" Lamielle
#Date: 9 June 2018
#License: GNU GPL v2+

import sys
import re
import pywiki
import wikitextparser as wtp

from sparql import Sparql

API_ENDPOINT = 'https://fr.wiktionary.org/w/api.php'
SPARQL_ENDPOINT = 'https://query.wikidata.org/sparql'
SUMMARY = 'Add an audio pronunciation file from Lingua Libre'
# Do not remove the $1, it is used to force the section to have a content
EMPTY_PRONUNCIATION_SECTION = '\n\n=== {{S|prononciation}} ===\n$1'
PRONUNCIATION_LINE = '\n* {{écouter|lang=$2|$3|audio=$1}}'
LANGUAGE_QUERY = 'SELECT ?item ?code WHERE { ?item wdt:P305 ?code. }'
LOCATION_QUERY = """
SELECT ?location ?locationLabel ?countryLabel
WHERE {
  ?location wdt:P17 ?country.
  SERVICE wikibase:label { bd:serviceParam wikibase:language "fr,en" . }
  VALUES ?location { wd:$1 }
}
"""
BOTTOM_REGEX = re.compile( r'(?:\s*(?:\[\[(?:Category|Catégorie):[^\]]+\]\]|{{clé de tri\|[^}]+}})?)*$', re.IGNORECASE )



class FrWiktionary:

	"""
	Constructor
	"""
	def __init__(self, user, password):
		self.user = user
		self.password = password
		self.api = pywiki.Pywiki(user, password, API_ENDPOINT, 'user')



	"""
	Public methods
	"""

	#
	def prepare(self, records):
		sparql = Sparql( SPARQL_ENDPOINT )

		# Get BCP 47 language code map
		self.language_code_map = {}
		raw_language_code_map = sparql.request( LANGUAGE_QUERY )

		for line in raw_language_code_map:
			self.language_code_map[ sparql.format_value( line, 'item' ) ] = sparql.format_value( line, 'code' )

		# Extract all different locations
		locations = set()
		for record in records:
			if record[ 'speaker' ][ 'residence' ] != None:
				locations.add( record[ 'speaker' ][ 'residence' ] )

		self.location_map = {}
		raw_location_map = sparql.request( LOCATION_QUERY.replace( '$1', ' wd:'.join( locations ) ) )
		for line in raw_location_map:
			country = sparql.format_value( line, 'countryLabel' )
			location = sparql.format_value( line, 'locationLabel' )
			if country != location:
				self.location_map[ sparql.format_value( line, 'location' ) ] = location + ' (' + country + ')'
			else:
				self.location_map[ sparql.format_value( line, 'location' ) ] = country

		return records

	#
	def execute(self, record):
		transcription = self.normalize( record[ 'transcription' ] )
		( is_already_present, wikicode, basetimestamp ) = self.get_entry( transcription, record[ 'file' ] )

		# Whether there is no entry for this record on frwiktionary
		if wikicode == False:
			# Retry afer having inverted the case of the first letter
			transcription = self.invert_case( transcription )
			( is_already_present, wikicode, basetimestamp ) = self.get_entry( transcription, record[ 'file' ] )
			if wikicode == False:
				return False

		# Whether the record is already inside the entry
		if is_already_present == True:
			print(record[ 'id' ] + ': already on frwiktionary')
			#return False

		language_section = self.get_language_section( wikicode, record[ 'language' ][ 'qid' ] )

		# Whether there is no section for the curent language
		if language_section == None:
			print(record[ 'id' ] + ': language section not found')
			return False

		pronunciation_section = self.get_pronunciation_section( language_section )

		# Create the pronunciation section, if it doesn't exists
		if pronunciation_section == None:
			pronunciation_section = self.create_pronunciation_section( language_section )

		# Add the pronunciation file to the section
		self.append_file( pronunciation_section, record[ 'file' ], record[ 'language' ][ 'qid' ], record[ 'speaker' ][ 'residence' ] )

		print(str(wikicode))

		# Save the result
		# TODO: Manage editconflict     "code": "editconflict",
		result = self.do_edit( transcription, wikicode, basetimestamp )
		if result == True:
			print(record[ 'id' ] + ': added to frwiktionary - https://www.wiktionary.org/wiki/' + transcription)

		return result



	"""
	Private methods
	"""

	#
	def normalize(self, transcription):
		return transcription.replace( '\'', '’' )

	#
	def invert_case(self, transcription):
		if transcription[ 0 ].isupper():
			transcription = transcription[ 0 ].lower() + transcription[1:]
		else:
			transcription = transcription[ 0 ].upper() + transcription[1:]

		return transcription

	#
	def get_entry(self, pagename, filename):
		response = self.api.request({
			"action": "query",
			"format": "json",
			"formatversion": "2",
			"prop": "images|revisions",
			"rvprop": "content|timestamp",
			"titles": pagename,
			"imimages": 'File:' + filename,
		})

		page = response[ 'query' ][ 'pages' ][ 0 ]
		if 'missing' in page:
			return ( False, False, 0 )

		is_already_present = ( 'images' in page )
		wikicode = page[ 'revisions' ][ 0 ][ 'content' ]
		basetimestamp = page[ 'revisions' ][ 0 ][ 'timestamp' ]

		return ( is_already_present, wtp.parse( wikicode ), basetimestamp )

	#
	def get_language_section( self, wikicode, language_qid ):
		if language_qid not in self.language_code_map:
			return None

		lang = self.language_code_map[ language_qid ]

		for section in wikicode.sections:
			if section.title.replace( ' ', '' ).lower() == '{{langue|' + lang + '}}':
				return section

		return None

	#
	def get_pronunciation_section( self, wikicode ):
		for section in wikicode.sections:
			if section.title.replace( ' ', '' ).lower() == '{{s|prononciation}}':
				return section

		return None


	#
	def create_pronunciation_section( self, wikicode ):
		following_sections = [ '{{s|anagrammes}}', '{{s|anagr}}', '{{s|voiraussi}}', '{{s|voir}}', '{{s|références}}', '{{s|réf}}' ]

		prev_section = wikicode.sections[ 0 ]
		for section in wikicode.sections:
			if section.title.replace( ' ', '' ).lower() in following_sections:
				break
			prev_section = section

		prev_section.contents = self.safe_append_text( prev_section.contents, EMPTY_PRONUNCIATION_SECTION )

		return self.get_pronunciation_section( wikicode )

	#
	def append_file( self, wikicode, filename, language_qid, location_qid ):
		section_content = wtp.parse( wikicode.sections[ 1 ].contents )

		location = ''
		if location_qid in self.location_map:
			location = self.location_map[ location_qid ]

		section_content.sections[ 0 ].contents = self.safe_append_text(
			section_content.sections[ 0 ].contents,
			PRONUNCIATION_LINE
				.replace( '$1', filename )
				.replace( '$2', self.language_code_map[ language_qid ] )
				.replace( '$3', location )
		)

		wikicode.sections[ 1 ].contents = str( section_content )

		# Remove the ugly hack, see comment line 17
		wikicode.sections[ 1 ].contents = wikicode.sections[ 1 ].contents.replace( '$1\n', '' )


	#
	def safe_append_text( self, content, text ):
		content = str( content )

		search = BOTTOM_REGEX.search( content )
		if search:
			index = search.start()
		else:
			index = len( content )

		return content[:index] + text + content[index:]


	#
	def do_edit( self, pagename, wikicode, basetimestamp ):
		result = self.api.request( {
			"action": "edit",
			"format": "json",
			"formatversion": "2",
			"title": pagename,
			"summary": SUMMARY,
			"basetimestamp": basetimestamp,
			"text": str( wikicode ),
			"token": self.api.get_csrf_token(),
			"nocreate": 1,
			"bot": 1
		} )

		if 'edit' in result:
			return True

		return False



