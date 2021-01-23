#!/usr/bin/python3.8
# -*- coding: utf-8 -*-
# Author: Antoine "0x010C" Lamielle
# Date: 11 June 2018
# License: GNU GPL v2+

import requests
import json
import urllib.parse
import backoff


class Sparql:

    """
    Constructor
    """

    def __init__(self, endpoint):
        self.endpoint = endpoint

    @backoff.on_exception(backoff.expo, exception=(requests.exceptions.Timeout,
                                                   requests.exceptions.ConnectionError,
                                                   requests.exceptions.ChunkedEncodingError,
                                                   json.decoder.JSONDecodeError),
                          max_tries=8)
    def request(self, query):
        response = requests.post(self.endpoint, data={"format": "json", "query": query})
        return json.loads(response.text)["results"]["bindings"]

    def format_value(self, sparql_result, key):
        if key in sparql_result:
            value = sparql_result[key]["value"]
            if sparql_result[key]["type"] == "uri":
                if value.startswith(u"https://lingualibre.org/entity/"):
                    value = value[30:]
                if value.startswith(u"http://www.wikidata.org/entity/"):
                    value = value[31:]
                if value.startswith(
                    u"http://commons.wikimedia.org/wiki/Special:FilePath/"
                ):
                    value = urllib.parse.unquote(value[51:])
            return value
        return None
