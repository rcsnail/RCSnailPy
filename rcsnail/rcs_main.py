import asyncio
import aiohttp
import json
import ssl

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
        self.__auth = None
        self.__db = None
        self.__user = None
        self.__firebase_app = pyrebase.initialize_app(FIREBASE_CONFIG)

        self.client_session = None
        self.live_session = None

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
            raise Exception("User name and password missing")

        # Get a reference to the database service
        self.__db = self.__firebase_app.database()

    async def enqueue(self, loop, new_frame_callback, new_telemetry_callback=None, track="private", car="") -> None:
        """
        Adding client to the queue to wait for the car becoming available. Returns live session object.
        """
        ignore_aiohttp_ssl_eror(loop)

        headers = {"Authorization": "Bearer " + self.__user['idToken']}
        self.client_session = aiohttp.ClientSession(headers=headers)
        data = {"track": track, "car": car}
        r = await self.client_session.post(DEFAULT_BASE_URL + "queue", data=data)
        json_body = await r.json()
        if 'queueUrl' in json_body:
            self.live_session = RCSLiveSession(rcs=self,
                                               firebase_app=self.__firebase_app,
                                               auth=self.__auth,
                                               queueUrl=json_body['queueUrl'],
                                               queueUpdateUrl=json_body['queueUpdateUrl'],
                                               queueKeepAliveTime=json_body['queueKeepAliveTime'],
                                               loop=loop)
            await self.live_session.run(new_frame_callback, new_telemetry_callback)
        else:
            raise Exception(json.dumps(json_body))

    async def close_client_session(self):
        await self.client_session.close()

    # gear reverse: -1, neutral: 0, drive: 1
    # steering -1.0...1.0
    # throttle 0..1.0
    # braking 0..1.0
    async def updateControl(self, gear, steering, throttle, braking):
        if self.live_session is not None:
            await self.live_session.updateControl(gear, steering, throttle, braking)


def ignore_aiohttp_ssl_eror(loop, aiohttpversion='3.5.4'):
    """Ignore aiohttp #3535 issue with SSL data after close

    There appears to be an issue on Python 3.7 and aiohttp SSL that throws a
    ssl.SSLError fatal error (ssl.SSLError: [SSL: KRB5_S_INIT] application data
    after close notify (_ssl.c:2609)) after we are already done with the
    connection. See GitHub issue aio-libs/aiohttp#3535

    Given a loop, this sets up a exception handler that ignores this specific
    exception, but passes everything else on to the previous exception handler
    this one replaces.

    If the current aiohttp version is not exactly equal to aiohttpversion
    nothing is done, assuming that the next version will have this bug fixed.
    This can be disabled by setting this parameter to None

    """
    if aiohttpversion is not None and aiohttp.__version__ != aiohttpversion:
        return

    orig_handler = loop.get_exception_handler() or loop.default_exception_handler

    def ignore_ssl_error(loop, context):
        if context.get('message') == 'SSL error in data received':
            # validate we have the right exception, transport and protocol
            exception = context.get('exception')
            protocol = context.get('protocol')
            if (
                isinstance(exception, ssl.SSLError) and exception.reason == 'KRB5_S_INIT' and
                isinstance(protocol, asyncio.sslproto.SSLProtocol) and
                isinstance(protocol._app_protocol, aiohttp.client_proto.ResponseHandler)
            ):
                if loop.get_debug():
                    asyncio.log.logger.debug('Ignoring aiohttp SSL KRB5_S_INIT error')
                return
        orig_handler(context)

    loop.set_exception_handler(ignore_ssl_error)