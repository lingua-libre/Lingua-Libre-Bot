#!/usr/bin/python3.5
# -*- coding: utf-8 -*-
# Autor: Antoine "0x010C" Lamielle
# Date: 11 June 2018
# License: GNU GPL v2+

import requests
import json
import urllib.parse


class Sparql:

    """
    Constructor
    """

    def __init__(self, endpoint):
        self.endpoint = endpoint

    def request(self, query):
        response = requests.post(self.endpoint, data={"format": "json", "query": query})

        return json.loads(response.text)["results"]["bindings"]

    def format_value(self, sparql_result, key):
        if key in sparql_result:
            value = sparql_result[key]["value"]
            if sparql_result[key]["type"] == "uri":
                if value.startswith(u"https://lingualibre.fr/entity/"):
                    value = value[30:]
                if value.startswith(u"http://www.wikidata.org/entity/"):
                    value = value[31:]
                if value.startswith(
                    u"http://commons.wikimedia.org/wiki/Special:FilePath/"
                ):
                    value = urllib.parse.unquote(value[51:])
            return value
        return None
