import asyncio
import aiohttp
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

roomId = ''.join([random.choice('0123456789') for x in range(10)])
ROOT = os.path.dirname(__file__)
PHOTO_PATH = os.path.join(ROOT, 'photo.jpg')

class ApprtcSignaling:
    def __init__(self, room):
        self._http = None
        self._origin = 'https://appr.tc'
        self._room = room
        self._websocket = None

    async def connect(self):
        join_url = self._origin + '/join/' + self._room

        # fetch room parameters
        self._http = aiohttp.ClientSession()
        async with self._http.post(join_url) as response:
            # we cannot use response.json() due to:
            # https://github.com/webrtc/apprtc/issues/562
            data = json.loads(await response.text())
        assert data['result'] == 'SUCCESS'
        params = data['params']

        self.__is_initiator = params['is_initiator'] == 'true'
        self.__messages = params['messages']
        self.__post_url = self._origin + '/message/' + self._room + '/' + params['client_id']

        # connect to websocket
        self._websocket = await websockets.connect(params['wss_url'], extra_headers={
            'Origin': self._origin
        })
        await self._websocket.send(json.dumps({
            'clientid': params['client_id'],
            'cmd': 'register',
            'roomid': params['room_id'],
        }))

        return params

    async def close(self):
        if self._websocket:
            await self.send(None)
            self._websocket.close()
        if self._http:
            await self._http.close()

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
        if self.__is_initiator:
            await self._http.post(self.__post_url, data=message)
        else:
            await self._websocket.send(json.dumps({
                'cmd': 'send',
                'msg': message,
            }))


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

    def __init__(self, rcs, firebase_app, auth, queuePath, loop):
        """
        """
        self.__rcs = rcs
        self.__firebase_app = firebase_app
        self.__auth = auth
        self.__queuePath = queuePath
        self.__loop = loop
        print('queuePath ' + queuePath)
        self.__db = self.__firebase_app.database()
        self.__fb_queue = asyncio.Queue()
        # self.__queue_stream = self.__db.child(queuePath).stream(self.queue_stream_handler, token = self.__auth.current_user['idToken'])
        # self.__queue_live = LiveData(self.__firebase_app, queuePath)
        # self.__queue_live.signal('/').connect(self.queue_handler)

    '''
    def queue_handler(sender, value=None):
        print(value)
        rs = self.__queue_live.get('rs')
        print(rs)
    '''

    def queue_stream_handler(self, message):
        print(message["event"]) # put  
        print(message["path"]) # /-K7yGTTEp7O549EzTYtI
        print(message["data"]) # {'title': 'Pyrebase', "body": "etc..."}
        if message['event'] == 'put' and message['path'] == '/rs':
            # remote session started
            print('Remote session started')
            self.create_remote_session(rsPath = message['data'])
            # self.__queue_stream.close() # can't close the stream from here
            # self.__queue_stream = None


    def create_remote_session(self, rsPath):
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


    def rs_stream_handler(self, message):
        print(message["event"]) # put  
        print(message["path"]) # /-K7yGTTEp7O549EzTYtI
        print(message["data"]) # {'title': 'Pyrebase', "body": "etc..."}
        

    def close(self):
        if self.__queue_stream:
            self.__queue_stream.close()
            self.__queue_stream = None
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
        params = await signaling.connect()

        if params['is_initiator'] == 'true':
            # send offer
            add_tracks()
            await pc.setLocalDescription(await pc.createOffer())
            await signaling.send(pc.localDescription)
            print('Please point a browser at %s' % params['room_link'])

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

    async def run(self, new_frame_callback):
        # start listening queue item
        # self.__queue_stream = self.__db.child(queuePath).stream(self.queue_stream_handler, token = self.__auth.current_user['idToken'])
        self.__new_frame_callback = new_frame_callback

        # create signaling and peer connection
        signaling = ApprtcSignaling(roomId)
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


