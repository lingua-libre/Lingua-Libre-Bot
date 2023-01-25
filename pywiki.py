#!/usr/bin/python3.8
# -*- coding: utf-8 -*-
# License: GNU GPL v2+

import json
import time

import backoff
import requests

from version import __version__

class NoSuchEntityException(Exception):
    ...

class Pywiki:
    def __init__(self, username: str, password: str, api_endpoint, user_type: str, dry_run: bool):
        self.username = username
        self.basic_user_name = self.username.split("@")[0]
        self.password = password
        self.dry_run = dry_run
        self.api_endpoint = api_endpoint
        self.user_type = user_type
        self.limit = 5000 if user_type == "bot" else 500
        self.session = requests.Session()
        self.session.headers.update(
            {
                'User-Agent': f'Lingua Libre Bot/{__version__}'
                              + ' (https://github.com/lingua-libre/Lingua-Libre-Bot)'
            }
        )

    @backoff.on_exception(backoff.expo,
                          (requests.exceptions.Timeout,
                           requests.exceptions.ConnectionError,
                           requests.exceptions.ChunkedEncodingError,
                           json.decoder.JSONDecodeError),
                          max_tries=8)
    def request(self, data, files=None):
        """
        Perform a given request with a simple but usefull error management
        @param data:
        @param files:
        @return:
        """
        if self.dry_run and data["action"] != "query":
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
                    if response["error"]["code"] == "no-such-entity":
                        raise NoSuchEntityException()
                    break
                return response
            except requests.exceptions.ConnectionError:
                time.sleep(5)
                self.session = requests.Session()
                self.login()
                relogin -= 1

        raise Exception("API error", response["error"])

    def login(self) -> int:
        """
        Login into the wiki
        :returns:
        """
        r = self.session.post(
            self.api_endpoint,
            data={
                "action": "login",
                "lgname": self.username,
                "lgpassword": self.password,
                "format": "json",
            },
        )
        token = json.loads(r.text)["login"]["token"]
        r = self.session.post(
            self.api_endpoint,
            data={
                "action": "login",
                "lgname": self.username,
                "lgpassword": self.password,
                "lgtoken": token,
                "format": "json",
            },
        )
        return -1 if json.loads(r.text)["login"]["result"] != "Success" else 0

    def get_csrf_token(self):
        """
          Get a crsf token from frwiki to be able to edit a page
        """
        r = self.request(
            {
                "action": "query",
                "meta": "tokens",
                "type": "csrf",
                "assert": self.user_type,
                "format": "json",
            }
        )
        return r["query"]["tokens"]["csrftoken"]
