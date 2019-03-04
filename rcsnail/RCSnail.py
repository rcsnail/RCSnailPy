import asyncio
import aiohttp

import pyrebase

from firebasedata import LiveData

DEFAULT_BASE_URL = "https://api.rcsnail.com/v1/"
FIREBASE_CONFIG = {
    "apiKey": "AIzaSyBYUu8CpzeRDs8I6_-ME8YkCJOI07YVSXk",
    "authDomain": "rcsnail-620e0.firebaseapp.com",
    "databaseURL": "https://rcsnail-620e0.firebaseio.com",
    "projectId": "rcsnail-620e0",
    "storageBucket": "rcsnail-620e0.appspot.com",
    "messagingSenderId": "1004648222667"
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

    async def queue(self) -> str:
        """
        Adding client to the queue to wait for the car becoming available. Returns live session object.
        """
        headers = {"Authorization": "Bearer " + self.__user['idToken']}
        session = await aiohttp.ClientSession(headers = headers)
        r = await session.get(DEFAULT_BASE_URL + "queue")
        # return r
        json_body = await r.json()
        return json_body
