#!/usr/bin/python3.8
# -*- coding: utf-8 -*-
# Author: Antoine "0x010C" Lamielle
# Date: 11 June 2018
# License: GNU GPL v2+

import requests
import json
import urllib.parse
import backoff
import re
import time

LINGUALIBRE_ENTITY = u"https://lingualibre.org/entity/"
# Keep both of these below as "http" : that's what's returned by the SPARQL requests
WIKIDATA_ENTITY = u"http://www.wikidata.org/entity/"
COMMONS_FILEPATH = u"http://commons.wikimedia.org/wiki/Special:FilePath/"


# TODO better handle the exceptions coming from this
@backoff.on_exception(backoff.expo,
                      exception=(requests.exceptions.Timeout,
                                 requests.exceptions.ConnectionError,
                                 requests.exceptions.ChunkedEncodingError,
                                 json.decoder.JSONDecodeError),
                      max_tries=5)
def request(endpoint: str, query: str):
    response = requests.post(endpoint, data={"format": "json", "query": query})

    if response.status_code == 504:
        print("504 Gateway Time-out\n"
              "Try to use --startdate")
        return ""

    if response.status_code == 429:
        print("Error 429 Too Many Requests")
        return ""

    if response.status_code == 403:
        retry_after = int(response.headers["Retry-After"])

        error = re.search(r'<\W*title\W*(.*)</title', response.text, re.IGNORECASE)
        print(f"Error 403; {error.group(1)}\nWait for {retry_after} seconds")

        time.sleep(retry_after)
        return ""

    exception_name = "MalformedQueryException"
    if response.text.find(exception_name) != -1:
        error = response.text
        pos1 = response.text.find(exception_name) + len(exception_name) + 1
        pos2 = response.text.find("\n", pos1)
        error = error[pos1:pos2].strip()
        print(f"MalformedQueryException: {error}")
        return ""

    exception_name = "TimeoutException"
    if response.text.find(exception_name) != -1:
        error = response.text
        pos1 = response.text.find(f"java.util.concurrent.{exception_name}")
        pos2 = response.text.find("\n", pos1)
        error = error[pos1:pos2].strip()
        print(f"TimeoutException: {error}")
        return ""

    return json.loads(response.text)["results"]["bindings"]


def format_value(sparql_result, key):
    if key not in sparql_result:
        return None
    # blank value (unknown value)
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
