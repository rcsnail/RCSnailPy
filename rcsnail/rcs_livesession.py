import asyncio
import aiohttp
from aiohttp_sse_client import client as sse_client
import urllib
import pyrebase
#from .rcsnail import RCSnail
#from .rcs_main import RCSnail
#import RCSnail
#from firebasedata import LiveData  # doesn't support authenticated users
from .rcs_renderer import MediaRenderer
import json
import logging
import os
import random

import cv2
import websockets
from av import VideoFrame

from aiortc import (RTCIceCandidate, RTCPeerConnection, RTCSessionDescription,
                    VideoStreamTrack)
from aiortc.contrib.media import MediaBlackhole, MediaPlayer, MediaRecorder
from aiortc.contrib.signaling import object_from_string, object_to_string

ROOT = os.path.dirname(__file__)
PHOTO_PATH = os.path.join(ROOT, 'photo.jpg')

class RCSSignaling:
    def __init__(self, auth, rs_url):
        self.__auth = auth
        self.__rs_url = rs_url
        self.__post_url = None

    def rs_error(self):
        print("error")

    def rs_message(self, message):
        print(message)
        if message['event'] == 'put' and message['path'] == '/rs':
            # remote session started
            print('Remote session message')

    async def connect(self):
        path = self.__rs_url + '?' + urllib.parse.urlencode({"auth": self.__auth.current_user['idToken']})
        timeout = aiohttp.ClientTimeout(total = 6000)
        session = aiohttp.ClientSession(timeout = timeout)
        self.__event_source = sse_client.EventSource(path, 
            session = session,
            on_message = self.rs_message, 
            on_error = self.rs_error
        )
        await self.__event_source.connect()
        # self.__queue_task = asyncio.ensure_future(self.queue_listen())
        
        return
        # self.__messages = params['messages']
        # self.__post_url = params['postUrl']

    async def close(self):
        if self.__event_source:
            await self.__event_source.close()

    async def receive(self):
        if self.__messages:
            message = self.__messages.pop(0)
        else:
            message = await self._websocket.recv()
            message = json.loads(message)['msg']
        print('<', message)
        return object_from_string(message)

    async def send(self, obj):
        message = object_to_string(obj)
        print('>', message)
        await self._http.post(self.__post_url, data=message)


class VideoImageTrack(VideoStreamTrack):
    """
    A video stream track that returns a rotating image.
    """
    def __init__(self):
        super().__init__()  # don't forget this!
        self.img = cv2.imread(PHOTO_PATH, cv2.IMREAD_COLOR)

    async def recv(self):
        pts, time_base = await self.next_timestamp()

        # rotate image
        rows, cols, _ = self.img.shape
        M = cv2.getRotationMatrix2D((cols / 2, rows / 2), int(pts * time_base * 45), 1)
        img = cv2.warpAffine(self.img, M, (cols, rows))

        # create video frame
        frame = VideoFrame.from_ndarray(img, format='bgr24')
        frame.pts = pts
        frame.time_base = time_base

        return frame


class RCSLiveSession(object):
    """
    RCSnail live session class handles queue item events and remote session
    """

    def __init__(self, rcs, firebase_app, auth, queueUrl, loop):
        """
        """
        self.__rcs = rcs
        self.__firebase_app = firebase_app
        self.__auth = auth
        self.__queueUrl = queueUrl
        self.__loop = loop
        print('queueUrl ' + queueUrl)
        self.__db = self.__firebase_app.database()
        self.__fb_queue = asyncio.Queue()
        # self.__queue_stream = self.__db.child(queuePath).stream(self.queue_stream_handler, token = self.__auth.current_user['idToken'])
        # self.__queue_live = LiveData(self.__firebase_app, queuePath)
        # self.__queue_live.signal('/').connect(self.queue_handler)

    def create_remote_session(self, rsUrl):
        '''
        pc = RTCPeerConnection()
        self.__pc = pc

        @pc.on('track')
        def on_track(track):
            print('Track %s received' % track.kind)
            # recorder.addTrack(track)
        rsPath = '/rs/test'
        class Track(object):
            pass
        track = Track()
        track.kind = "test"
        pc.emit('track', track)
        '''
        rsPath = '/rs/test'
        # self.__rs_stream = self.__db.child(rsPath).stream(self.rs_stream_handler, token = self.__auth.current_user['idToken'])
        

    def close(self):
        pass
        if self.__rs_stream:
            self.__rs_stream.close()
            self.__rs_stream = None

    async def run_session(self, pc, player, recorder, signaling):
        def add_tracks():
            if player and player.audio:
                pc.addTrack(player.audio)

            if player and player.video:
                pc.addTrack(player.video)
            else:
                pc.addTrack(VideoImageTrack())

        @pc.on('track')
        def on_track(track):
            print('Track %s received' % track.kind)
            recorder.addTrack(track)

        # connect to websocket and join
        await signaling.connect()

        # send offer
        add_tracks()
        await pc.setLocalDescription(await pc.createOffer())
        await signaling.send(pc.localDescription)
        print('Offer sent')

        # consume signaling
        while True:
            obj = await signaling.receive()

            if isinstance(obj, RTCSessionDescription):
                await pc.setRemoteDescription(obj)
                await recorder.start()

                if obj.type == 'offer':
                    # send answer
                    add_tracks()
                    await pc.setLocalDescription(await pc.createAnswer())
                    await signaling.send(pc.localDescription)
            elif isinstance(obj, RTCIceCandidate):
                pc.addIceCandidate(obj)
            else:
                print('Exiting')
                break

    def new_frame(self, frame):
        print('Received new frame')
        if self.__new_frame_callback:
            self.__new_frame_callback(frame)

    async def get_remote_session_url(self):
        url = self.__queueUrl + '?' + urllib.parse.urlencode({"auth": self.__auth.current_user['idToken']})
        timeout = aiohttp.ClientTimeout(total = 6000)
        client_session = aiohttp.ClientSession(timeout = timeout)
        rs_url = None
        async with sse_client.EventSource(url, 
            session = client_session
        ) as event_source:
            try:
                async for event in event_source:
                    print(event)
                    if event.message == 'put':
                        data = json.loads(event.data)
                        data_path = data['path']
                        data_data = data['data']
                        if data_path == '/':
                            if 'rsUrl' in data_data:
                                rs_url = data_data['rsUrl']
                        elif data_path == '/rsUrl':
                            rs_url = data_data
                    if rs_url != None:
                        break
                print(event)
            except ConnectionError:
                pass        
        return rs_url

    async def run(self, new_frame_callback):
        # start listening queue item
        # self.__queue_stream = self.__db.child(queuePath).stream(self.queue_stream_handler, token = self.__auth.current_user['idToken'])
        self.__new_frame_callback = new_frame_callback

        # wait for queue to return remote session url
        rs_url = await self.get_remote_session_url()
        if rs_url == None:
            return

        # create signaling and peer connection
        signaling = RCSSignaling(self.__auth, rs_url)
        pc = RTCPeerConnection()

        # create media source
        player = None

        # create media sink
        # recorder = MediaRecorder(args.record_to)
        # recorder = MediaBlackhole()
        recorder = MediaRenderer(self.new_frame)

        # add event loop
        try:
            await self.run_session(
                pc=pc,
                player=player,
                recorder=recorder,
                signaling=signaling)
        except KeyboardInterrupt:
            pass
        finally:
            # cleanup
            await recorder.stop()
            await signaling.close()
            await pc.close()


