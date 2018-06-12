#!/usr/bin/python3.5
# -*- coding: utf-8 -*-
#Autor: Antoine "0x010C" Lamielle
#Date: 9 June 2018
#License: GNU GPL v2+

import sys
import configparser
import argparse
import time

from sparql import Sparql

from wikidata import Wikidata
from frwiktionary import FrWiktionary


config = configparser.ConfigParser()
config.read("./config.ini")

ENDPOINT = "https://lingualibre.fr/bigdata/namespace/wdq/sparql"
BASEQUERY = """select distinct ?record ?file ?speaker ?speakerLabel ?date ?transcription ?qualifier ?wikidataId ?wikipediaTitle ?wiktionaryEntry ?languageIso ?languageQid ?languageWMCode ?linkeduser ?gender ?residence
where {
  ?record prop:P2 entity:Q2 .
  ?record prop:P3 ?file .
  ?record prop:P4 ?language .
  ?record prop:P5 ?speaker .
  ?record prop:P6 ?date .
  ?record prop:P7 ?transcription .
  OPTIONAL { ?record prop:P18 ?qualifier . }
  OPTIONAL { ?record prop:P12 ?wikidataId . }
  OPTIONAL { ?record prop:P19 ?wikipediaTitle . }
  OPTIONAL { ?record prop:P20 ?wiktionaryEntry . }

  OPTIONAL { ?language prop:P13 ?languageIso . }
  OPTIONAL { ?language prop:P12 ?languageQid . }
  OPTIONAL { ?language prop:P17 ?languageWMCode . }

  ?speaker prop:P11 ?linkeduser .
  OPTIONAL { ?speaker prop:P8 ?gender . }
  OPTIONAL { ?speaker prop:P14 ?residence . }

  SERVICE wikibase:label {
    bd:serviceParam wikibase:language "en" .
  }

  #filters
}"""


def get_records( query ):
	sparql = Sparql(ENDPOINT)
	raw_records = sparql.request(query)
	records = []
	for record in raw_records:
		records += [{
			"id":             sparql.format_value( record, 'record' ),
			"file":           sparql.format_value( record, 'file' ),
			"date":           sparql.format_value( record, 'date' ),
			"transcription":  sparql.format_value( record, 'transcription' ),
			"qualifier":      sparql.format_value( record, 'qualifier' ),
			"user":           sparql.format_value( record, 'linkeduser' ),
			"speaker": {
				"id":         sparql.format_value( record, 'speaker' ),
				"name":       sparql.format_value( record, 'speakerLabel' ),
				"gender":     sparql.format_value( record, 'gender' ),
				"residence":  sparql.format_value( record, 'residence' ),
			},
			"links": {
				"wikidata":   sparql.format_value( record, 'wikidataId' ),
				"wikipedia":  sparql.format_value( record, 'wikipediaTitle' ),
				"wiktionary": sparql.format_value( record, 'wiktionaryEntry' ),
			},
			"language": {
				"iso":        sparql.format_value( record, 'languageIso' ),
				"qid":        sparql.format_value( record, 'languageQid' ),
				"wm":         sparql.format_value( record, 'languageWMCode' ),

			}
		}]

	return records


# Main
def main():
	# Create an object for each supported wiki
	supported_wikis = {
		'wikidatawiki': Wikidata( config.get( 'wiki', 'user' ), config.get( 'wiki', 'password' ) ),
		'frwiktionary': FrWiktionary( config.get( 'wiki', 'user' ), config.get( 'wiki', 'password' ) )
	}

	# Declare the command-line arguments
	parser = argparse.ArgumentParser(description='Reuse records made on Lingua Libre on some wikis.')
	parser.add_argument('--item', help='run only on the given item')
	parser.add_argument('--startdate', help='from which timestamp to start')
	parser.add_argument('--enddate', help='at which timestamp to end')
	parser.add_argument('--user', help='run only on records from the given user')
	parser.add_argument('--wiki', help='run only on the selected wiki', choices=list( supported_wikis.keys() ))
	langgroup = parser.add_mutually_exclusive_group()
	langgroup.add_argument('--lang', help='run only on records from the given language, identified by its lingua libre qid')
	langgroup.add_argument('--langiso', help='run only on records from the given language, identified by its iso 693-3 code')
	langgroup.add_argument('--langwm', help='run only on records from the given language, identified by its wikimedia code')

	# Parse the command-line arguments
	args = parser.parse_args()

	# Add some filters depending on the fetched arguments
	filters = ""
	if args.item != None:
		filters = 'BIND( entity:' + args.item + ' as ?record ).'
	else:
		if args.startdate != None:
			filters = 'FILTER( ?date > "' + args.startdate + '"^^xsd:dateTime ).'
		if args.enddate != None:
			filters += 'FILTER( ?date < "' + args.enddate + '"^^xsd:dateTime ).'
		if args.user != None:
			filters += 'FILTER( ?linkeduser = "' + args.user + '" ).'
		if args.lang != None:
			filters += 'BIND( entity:' + args.lang + ' as ?language ).'
		elif args.langiso != None:
			filters += 'FILTER( ?languageIso = "' + args.langiso + '" ).'
		elif args.langwm != None:
			filters += 'FILTER( ?languageWMCode = "' + args.langwm + '" ).'

	# Get the informations of all the records
	records = get_records( BASEQUERY.replace( '#filters', filters ) )

	# Filter the wikis depending on the fetched arguments
	if args.wiki != None:
		tmp = supported_wikis[ args.wiki ]
		supported_wikis = { args.wiki: tmp }

	# Prepare the records (fetch extra infos, clean some datas,...)
	for dbname in supported_wikis:
		records = supported_wikis[ dbname ].prepare( records )

	# Try to reuse each listed records on each supported wikis
	for record in records:
		for dbname in supported_wikis:
			if supported_wikis[ dbname ].execute( record ):
				time.sleep(30)

	print(len(records))



if __name__ == '__main__':
	main()

