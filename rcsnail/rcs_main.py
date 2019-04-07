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

    def __init__(self):
        self.liveSession = None
        self.__firebase_app = pyrebase.initialize_app(FIREBASE_CONFIG)


    def sign_in_with_email_and_password(self, login_or_token=None, password=None):
        """
        :param login_or_token: string
        :param password: string
        """

        assert login_or_token is None or isinstance(login_or_token, str), login_or_token
        assert password is None or isinstance(password, str), password
        # Get a reference to the auth service
        self.__auth = self.__firebase_app.auth()

        # Log the user in
        if password != "":
            self.__user = self.__auth.sign_in_with_email_and_password(login_or_token, password)
        elif login_or_token != "":
            # Log in with token
            self.__user = self.__auth.sign_in_with_custom_token(login_or_token)
        else:
            raise "User name and password missing"

        # Get a reference to the database service
        self.__db = self.__firebase_app.database()

    async def enqueue(self, loop, new_frame_callback) -> None:
        """
        Adding client to the queue to wait for the car becoming available. Returns live session object.
        """
        headers = {"Authorization": "Bearer " + self.__user['idToken']}
        session = aiohttp.ClientSession(headers = headers)
        data = {"track":"Spark"}
        r = await session.post(DEFAULT_BASE_URL + "queue", data = data)
        json_body = await r.json()
        if 'queueUrl' in json_body:
            self.liveSession = RCSLiveSession(rcs = self, 
                firebase_app = self.__firebase_app, 
                auth = self.__auth,
                queueUrl = json_body['queueUrl'],
                queueUpdateUrl = json_body['queueUpdateUrl'],
                queueKeepAliveTime = json_body['queueKeepAliveTime'],
                loop = loop)
            await self.liveSession.run(new_frame_callback)        
        else:
            raise Exception(json.dumps(json_body))

    # gear reverse: -1, neutral: 0, drive: 1
    # steering -1.0...1.0
    # throttle 0..1.0
    # braking 0..1.0
    async def updateControl(self, gear, steering, throttle, braking):
        if not (self.liveSession is None):
            await self.liveSession.updateControl(gear, steering, throttle, braking)
