#!/usr/bin/python3.8
# -*- coding: utf-8 -*-
# Author: Antoine "0x010C" Lamielle
# Date: 11 June 2018
# License: GNU GPL v2+

import requests
import json
import urllib.parse
import backoff

LINGUALIBRE_ENTITY = u"https://lingualibre.org/entity/"
# Keep both of these below as "http" : that's what's returned by the SPARQL requests
WIKIDATA_ENTITY = u"http://www.wikidata.org/entity/"
COMMONS_FILEPATH = u"http://commons.wikimedia.org/wiki/Special:FilePath/"


class Sparql:

    """
    Constructor
    """

    def __init__(self, endpoint):
        self.endpoint = endpoint

    # TODO better handle the exceptions coming from this
    @backoff.on_exception(backoff.expo, exception=(requests.exceptions.Timeout,
                                                   requests.exceptions.ConnectionError,
                                                   requests.exceptions.ChunkedEncodingError,
                                                   json.decoder.JSONDecodeError),
                          max_tries=5)
    def request(self, query):
        response = requests.post(self.endpoint, data={"format": "json", "query": query})
        
        ''' 504 error
        <html>
        <head><title>504 Gateway Time-out</title></head>
        <body>
        <center><h1>504 Gateway Time-out</h1></center>
        <hr><center>nginx</center>
        </body>
        </html>
        '''
        if response.text.find("504 Gateway Time-out") != -1:
            print("504 Gateway Time-out\n" \
                  "Try to use --startdate")
            return ""

        ''' 429 error
        <html>
        <head>
        <meta http-equiv="Content-Type" content="text/html;charset=utf-8"/>
        <title>Error 429 Too Many Requests - Please retry in 3 seconds.</title>
        </head>
        <body><h2>HTTP ERROR 429</h2>
        <p>Problem accessing /bigdata/namespace/wdq/sparql. Reason:
        <pre>    Too Many Requests - Please retry in 3 seconds.</pre></p><hr><a href="http://eclipse.org/jetty">Powered by Jetty:// 9.4.12.v20180830</a><hr/>
        
        </body>
        </html>
        '''
        if response.text.find("Error 429 Too Many Requests") != -1:
            print("Error 429 Too Many Requests")
            return ""
        
        return json.loads(response.text)["results"]["bindings"]

    def format_value(self, sparql_result, key):
        if key in sparql_result:
            #blank value (unknown value)
            if sparql_result[key]["type"] == "bnode":
                return None

            value = sparql_result[key]["value"]
            if sparql_result[key]["type"] == "uri":
                if value.startswith(LINGUALIBRE_ENTITY):
                    value = value[len(LINGUALIBRE_ENTITY):]
                if value.startswith(WIKIDATA_ENTITY):
                    value = value[len(WIKIDATA_ENTITY):]
                if value.startswith(COMMONS_FILEPATH):
                    value = urllib.parse.unquote(value[len(COMMONS_FILEPATH):])
            return value
        return None
