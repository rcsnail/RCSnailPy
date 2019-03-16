import asyncio
import aiohttp
import json

import pyrebase

from firebasedata import LiveData
from .rcs_livesession import RCSLiveSession

DEFAULT_BASE_URL = "https://api.rcsnail.com/v1/"
FIREBASE_CONFIG = {
    "apiKey": "AIzaSyD1vHD9TzuDwnvrFfHnL2g6KNgHvmnjShM",
    "authDomain": "rcsnail-api.firebaseapp.com",
    "databaseURL": "https://rcsnail-api.firebaseio.com",
    "projectId": "rcsnail-api",
    "storageBucket": "rcsnail-api.appspot.com",
    "messagingSenderId": "485865779952"    
}

class RCSnail(object):
    """
    This is RCSnail main class
    """

    def __init__(self, login_or_token=None, password=None):
        """
        :param login_or_token: string
        :param password: string
        """

        assert login_or_token is None or isinstance(login_or_token, str), login_or_token
        assert password is None or isinstance(password, str), password
        self.__firebase = pyrebase.initialize_app(FIREBASE_CONFIG)
        # Get a reference to the auth service
        auth = self.__firebase.auth()

        # Log the user in
        if password != "":
            self.__user = auth.sign_in_with_email_and_password(login_or_token, password)
        elif login_or_token != "":
            # Log in with token
            self.__user = auth.sign_in_with_custom_token(login_or_token)
        else:
            raise "User name and password missing"

        # Get a reference to the database service
        self.__db = self.__firebase.database()

    async def enqueue(self) -> RCSLiveSession:
        """
        Adding client to the queue to wait for the car becoming available. Returns live session object.
        """
        headers = {"Authorization": "Bearer " + self.__user['idToken']}
        session = aiohttp.ClientSession(headers = headers)
        data = json.loads('{"track":"Spark"}')
        r = await session.post(DEFAULT_BASE_URL + "queue", data = data)
        json_body = await r.json()
        if 'liveUrl' in json_body:
            liveSession = RCSLiveSession(rcs = self, liveUrl = json_body['liveUrl'])
            return liveSession
        else:
            raise Exception(json.dumps(json_body))
