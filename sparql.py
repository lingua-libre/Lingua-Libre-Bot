#!/usr/bin/python3.8
# -*- coding: utf-8 -*-
# Author: Antoine "0x010C" Lamielle
# Date: 11 June 2018
# License: GNU GPL v2+

import json
import re
import time
import urllib.parse

import backoff
import requests

LINGUALIBRE_ENTITY = u"https://lingualibre.org/entity/"
# Keep both of these below as "http" : that's what's returned by the SPARQL requests
WIKIDATA_ENTITY = u"http://www.wikidata.org/entity/"
COMMONS_FILEPATH = u"http://commons.wikimedia.org/wiki/Special:FilePath/"


class Sparql:

    def __init__(self, endpoint):
        self.endpoint = endpoint

    # TODO better handle the exceptions coming from this
    @backoff.on_exception(backoff.expo,
                          exception=(requests.exceptions.Timeout,
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
        if response.status_code == 504:
            print("504 Gateway Time-out\n"
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
        if response.status_code == 429:
            print("Error 429 Too Many Requests")
            return ""

        '''
        <head>
        <meta http-equiv="Content-Type" content="text/html;charset=utf-8"/>
        <title>Error 403 You have been banned until 2021-09-19T02:42:25.612Z, please respect throttling and retry-after headers.</title>
        </head>
        '''
        if response.status_code == 403:
            retry_after = int(response.headers["Retry-After"])

            error = re.search(r'<\W*title\W*(.*)</title', response.text, re.IGNORECASE)
            print(f"Error 403; {error.group(1)}\nWait for {retry_after} seconds")

            time.sleep(retry_after)
            return ""

        ''' MalformedQueryException
        ...
        java.util.concurrent.ExecutionException: org.openrdf.query.MalformedQueryException: Lexical error at line 26, column 64.  Encountered: " " (32), after : "tris"
        at java.util.concurrent.FutureTask.report(FutureTask.java:122)
        at java.util.concurrent.FutureTask.get(FutureTask.java:206)
        ...
        '''
        exception_name = "MalformedQueryException"
        if response.text.find(exception_name + ":") != -1:
            error = response.text
            pos1 = response.text.find(exception_name) + len(exception_name) + 1
            pos2 = response.text.find("\n", pos1)
            error = error[pos1:pos2].strip()
            print(f"MalformedQueryException: {error}")
            return ""

        ''' TimeoutException
        java.util.concurrent.TimeoutException
        at java.util.concurrent.FutureTask.get(FutureTask.java:205)
        at com.bigdata.rdf.sail.webapp.BigdataServlet.submitApiTask(BigdataServlet.java:292)
        at com.bigdata.rdf.sail.webapp.QueryServlet.doSparqlQuery(QueryServlet.java:678)
        ...
        '''
        exception_name = "TimeoutException"
        if response.text.find(exception_name) != -1:
            error = response.text
            pos1 = response.text.find("java.util.concurrent." + exception_name)
            pos2 = response.text.find("\n", pos1)
            error = error[pos1:pos2].strip()
            print(f"TimeoutException: {error}")
            return ""

        return json.loads(response.text)["results"]["bindings"]

    @staticmethod
    def format_value(sparql_result, key):
        if key not in sparql_result:
            return None
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
