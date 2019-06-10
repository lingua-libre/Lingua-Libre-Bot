#!/usr/bin/python2.7
# -*- coding: utf-8 -*-
# Autor: Antoine "0x010C" Lamielle
# Date: 18 March 2016
# License: GNU GPL v2+

import time
import json
import requests
import backoff
from version import __version__

class Pywiki:
    def __init__(self, user, password, api_endpoint, assertion):
        self.user = user
        self.basic_user_name = self.user.split("@")[0]
        self.password = password
        self.dry_run = False
        self.api_endpoint = api_endpoint
        self.assertion = assertion
        if self.assertion == "bot":
            self.limit = 5000
        else:
            self.limit = 500

        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'Lingua Libre Bot/' + __version__ +  ' (https://github.com/lingua-libre/Lingua-Libre-Bot)'})


    def set_dry_run(self, dry_run):
        self.dry_run = dry_run

    """
    Perform a given request with a simple but usefull error managment
    """

    @backoff.on_exception(backoff.expo, (requests.exceptions.Timeout, requests.exceptions.ConnectionError, requests.exceptions.ChunkedEncodingError, json.decoder.JSONDecodeError), max_tries=8)
    def request(self, data, files=None):
        if self.dry_run == True and data["action"] != "query":
            print(data)
            return {"dryrun": True}

        relogin = 3
        while relogin:
            try:
                if files is None:
                    r = self.session.post(self.api_endpoint, data=data)
                else:
                    r = self.session.post(self.api_endpoint, data=data, files=files)
                response = json.loads(r.text)
                if "error" in response:
                    if response["error"]["code"] == "assertuserfailed":
                        self.login()
                        relogin -= 1
                        continue
                    break
                return response
            except (requests.exceptions.ConnectionError):
                time.sleep(5)
                self.session = requests.Session()
                self.login()
                relogin -= 1
        raise Exception("API error", response["error"])

    """
    Login into the wiki
    """

    def login(self):
        r = self.session.post(
            self.api_endpoint,
            data={
                "action": "login",
                "lgname": self.user,
                "lgpassword": self.password,
                "format": "json",
            },
        )
        token = json.loads(r.text)["login"]["token"]
        r = self.session.post(
            self.api_endpoint,
            data={
                "action": "login",
                "lgname": self.user,
                "lgpassword": self.password,
                "lgtoken": token,
                "format": "json",
            },
        )
        if json.loads(r.text)["login"]["result"] != "Success":
            return -1
        return 0

    """
    Get a crsf token from frwiki to be able to edit a page
    """

    def get_csrf_token(self):
        r = self.request(
            {
                "action": "query",
                "meta": "tokens",
                "type": "csrf",
                "assert": self.assertion,
                "format": "json",
            }
        )
        return r["query"]["tokens"]["csrftoken"]
