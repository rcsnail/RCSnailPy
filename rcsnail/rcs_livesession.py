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
import time
import logging
import ssl

import cv2
import websockets
from av import VideoFrame

from aiortc import (RTCIceCandidate, RTCPeerConnection, RTCSessionDescription,
                    VideoStreamTrack)
from aiortc.contrib.media import MediaBlackhole, MediaPlayer, MediaRecorder
from aiortc.contrib.signaling import object_from_string, object_to_string
from aiortc.sdp import candidate_from_sdp, candidate_to_sdp

ROOT = os.path.dirname(__file__)
PHOTO_PATH = os.path.join(ROOT, 'photo.jpg')

class RCSSignaling:
    def __init__(self, auth, rs_url, post_url, is_offerer, loop):
        self.__auth = auth
        self.__rs_url = rs_url
        self.__post_url = post_url
        self.__is_offerer = is_offerer
        self.__message_queue = asyncio.Queue()
        self.__uid = auth.current_user['localId']
        self.__loop = loop
        self._session = None

    def rs_error(self):
        print("error")

    def is_offerer(self):
        return self.__is_offerer

    def handle_message(self, key, data):
        if key in self.__received_messages:
            return
        self.__received_messages[key] = data
        # await self.__message_queue.put(data)
        if "type" in data and data["type"] == "candidates":
            for message in data["candidates"]:
                asyncio.run_coroutine_threadsafe(self.__message_queue.put(message), loop = self.__loop)
        else:
            asyncio.run_coroutine_threadsafe(self.__message_queue.put(data), loop = self.__loop)

    def rs_message(self, message):
        print(message)
        if message.message == 'put':
            data = json.loads(message.data)
            data_path = data['path']
            data_data = data['data']
            if data_path == '/':
                if data_data != None:
                    # parse existing messages
                    for data_key in data_data:
                        self.handle_message('/' + data_key, data_data[data_key])
            else:
                # data_path for new message '/-LaP0ffzKHctPD1uQs7M'
                # data_data['type']
                # data_data['sdp'] or data_data['candidate']
                self.handle_message(data_path, data_data)

    async def rs_listen(self):
        async for event in self.__event_source:
            pass
            #print(event)

    async def connect(self):
        self.__received_messages = {} # empty dict for received messages
        headers = {
            "Authorization": "Bearer " + self.__auth.current_user['idToken'],
            'content-type': 'application/json'
        }
        self._http = aiohttp.ClientSession(headers=headers)

        path = self.__rs_url + '?' + urllib.parse.urlencode({"auth": self.__auth.current_user['idToken']})
        timeout = aiohttp.ClientTimeout(total=6000)
        self._session = aiohttp.ClientSession(timeout=timeout)
        self.__event_source = sse_client.EventSource(path,
                                                     session=self._session,
                                                     on_message=self.rs_message,
                                                     on_error=self.rs_error)
        await self.__event_source.connect()
        self.__rs_task = asyncio.ensure_future(self.rs_listen())


    async def close(self):
        if self.__event_source:
            await self.__event_source.close()
        if self.__rs_task:
            self.__rs_task.cancel()
        if self._http:
            await self._http.close()
        if self._session:
            await self._session.close()

    async def receive(self):
        message = await self.__message_queue.get()
        # message = json.loads(message)['msg']
        print('<', message)
        # msg = json.dumps(message)
        if message['type'] in ['answer', 'offer']:
            sdp = message['sdp']
            #return RTCSessionDescription(**msg)
            return RTCSessionDescription(sdp=sdp, type=message['type'])
        elif message['type'] == 'candidate':
            candidate = candidate_from_sdp(message['candidate'].split(':', 1)[1])
            candidate.sdpMid = message['sdpMid']
            candidate.sdpMLineIndex = message['sdpMLineIndex']
            return candidate
        else:
            return None

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

    def __init__(self, rcs, firebase_app, auth, queueUrl, queueUpdateUrl, queueKeepAliveTime, loop):
        """
        """
        self.__rcs = rcs
        self.__firebase_app = firebase_app
        self.__auth = auth
        self.__queueUrl = queueUrl
        self.__loop = loop
        self.__frameCount = 0
        self.__uid = auth.current_user['localId']
        self.__queueUpdateUrl = queueUpdateUrl
        self.__queueKeepAliveTime = queueKeepAliveTime
        self.__controlChannel = None
        self.__controlPacket = 0
        self.__canSendControl = True
        self.__lastSendControl = 0
        self.__taskQueueKeepAlive = loop.create_task(self.queueKeepAlive())
        self.__rto = 0
        print('queueUrl ' + queueUrl)

    async def queueKeepAlive(self):
        while True:
            await asyncio.sleep(self.__queueKeepAliveTime)
            headers = {"Authorization": "Bearer " + self.__auth.current_user['idToken']}
            session = aiohttp.ClientSession(headers=headers)
            data = {"keep-alive": True}
            r = await session.post(self.__queueUpdateUrl, data=data)
            json_body = await r.json()
            await session.close()
            if not ('state' in json_body) or (json_body['state'] != 'waiting'):
                break

    def close(self):
        print('Closing RCS live session')

    async def run_session(self, pc, player, recorder, signaling):
        def add_tracks():
            channel = pc.createDataChannel('control')
            self.__controlChannel = channel
                #, maxPacketLifeTime = 1  # this seems better
                ##, maxRetransmits = 0 
                #, ordered = False
                #)
            octets = 0
            
            @channel.on('message')
            async def on_message(message):
                nonlocal octets

                if message:
                    octets += len(message)
                    # fp.write(message)
                    data = json.loads(message)
                    delta = 0
                    if "c" in data:
                        delta = int(time.time() * 1000.0) - data["c"]
                        self.__canSendControl = True
                    asyncio.ensure_future(self.new_telemetry(data))
                    #logging.warn("data recv %d %s" % (delta, message))
                else:
                    elapsed = time.time() - start
                    print('received %d bytes in %.1f s (%.3f Mbps)' % (
                        octets, elapsed, octets * 8 / elapsed / 1000000))

                    # say goodbye
                    # await signaling.
                    send(None)

            if signaling.is_offerer():
                tranceiver = pc.addTransceiver('video', direction='recvonly')
                # workaround for ICE connection issue
                tranceiver._transport.transport.iceGatherer._connection.local_username = \
                    self.__controlChannel.transport.transport.transport.iceGatherer._connection.local_username
                tranceiver._transport.transport.iceGatherer._connection.local_password = \
                    self.__controlChannel.transport.transport.transport.iceGatherer._connection.local_password
                print('video recvonly tranceiver created') 

            '''
            def send_data():
                data = "turn left"
                self.__controlChannel.send(data)

            self.__controlChannel.on('bufferedamountlow', send_data)
            self.__controlChannel.on('open', send_data)
            
            if player and player.audio:
                pc.addTrack(player.audio)

            if player and player.video:
                pc.addTrack(player.video)
            else:
                pc.addTrack(VideoImageTrack())
            '''

        @pc.on('track')
        def on_track(track):
            print('Track %s received' % track.kind)
            recorder.addTrack(track)

        @pc.on('datachannel')
        def on_datachannel(channel):
            start = time.time()
            octets = 0
            print('datachannel started: %s' % (channel.label)) 

            @channel.on('message')
            async def on_message(message):
                nonlocal octets

                if message:
                    octets += len(message)
                    # fp.write(message)
                    data = json.loads(message)
                    delta = 0
                    if "c" in data:
                        delta = int(time.time() * 1000.0) - data["c"]
                        self.__canSendControl = True
                    asyncio.ensure_future(self.new_telemetry(data))
                    #logging.warn("data recv %d %s" % (delta, message))
                else:
                    elapsed = time.time() - start
                    print('received %d bytes in %.1f s (%.3f Mbps)' % (
                        octets, elapsed, octets * 8 / elapsed / 1000000))

                    # say goodbye
                    # await signaling.
                    send(None)

        # connect to websocket and join
        await signaling.connect()

        
        # send offer
        if signaling.is_offerer():
            add_tracks()
            offer = await pc.createOffer()
            await pc.setLocalDescription(offer)
            await signaling.send(pc.localDescription)
            # await signaling.send(offer)
            print('Offer sent')        

        # consume signaling
        while True:
            obj = await signaling.receive()

            if isinstance(obj, RTCSessionDescription):
                await pc.setRemoteDescription(obj)
                if obj.type == "offer":
                    add_tracks()
                    answer = await pc.createAnswer()
                    await pc.setLocalDescription(answer)
                    await signaling.send(pc.localDescription)
                await recorder.start()
            elif isinstance(obj, RTCIceCandidate):
                await pc.addIceCandidate(obj)
            else:
                print('Exiting')
                break

        await signaling.close()

    # gear reverse: -1, neutral: 0, drive: 1
    # steering -1.0...1.0
    # throttle 0..1.0
    # braking 0..1.0
    async def updateControl(self, gear, steering, throttle, braking):
        if ( #self.__canSendControl and 
                self.__controlChannel != None and 
                self.__controlChannel.readyState == "open"):
            # if steering == 0 and throttle == 0 and braking == 0: 
            #    return
            sendTime = int(time.time() * 1000.0)
            # if not self.__canSendControl and self.__lastSendControl > (sendTime - 100):
            #    return
            self.__lastSendControl = sendTime
            data = {
                "p": self.__controlPacket,
                "c": sendTime,
                "g": gear,
                "s": steering,
                "t": throttle,
                "b": braking
                #,"dummy": " " * 1000
            }
            self.__controlPacket = self.__controlPacket + 1
            self.__canSendControl = True
            # logging.warn("data send %s" % (data))
            # print('data send %s' % (data)) 
            if abs(self.__rto - self.__controlChannel.transport._rto) / self.__controlChannel.transport._rto > 0.1:
                self.__rto = self.__controlChannel.transport._rto
                print('rto', self.__rto)
            self.__controlChannel.send(json.dumps(data))
            # print('data sent') 
            
            
            if self.__controlChannel.transport._association_state == self.__controlChannel.transport.State.ESTABLISHED:
                # print('data flushing')
                await self.__controlChannel.transport._data_channel_flush()
                await self.__controlChannel.transport._transmit()
                # print('data flushed')
                #pass            

            # send dummy bytes to force previous package delivery
            # data = bytes(5000)
            # self.__controlChannel.send(data)

    def new_frame(self, frame):
        if self.__frameCount % 100 == 0:
            print('Received new frame', self.__frameCount)
        self.__frameCount = self.__frameCount + 1
        if self.__new_frame_callback:
            self.__new_frame_callback(frame)

    async def new_telemetry(self, telemetry):
        if self.__new_telemetry_callback:
            self.__new_telemetry_callback(telemetry)

    async def get_remote_session_url(self):
        url = self.__queueUrl + '?' + urllib.parse.urlencode({"auth": self.__auth.current_user['idToken']})
        timeout = aiohttp.ClientTimeout(total=6000)
        client_session = aiohttp.ClientSession(timeout=timeout)
        rs_url = None
        rs_post_url = None
        is_offerer = True
        async with sse_client.EventSource(url, session=client_session) as event_source:
            try:
                async for event in event_source:
                    print(event)
                    if event.message == 'put' or event.message == 'patch':
                        data = json.loads(event.data)
                        data_path = data['path']
                        data_data = data['data']
                        if data_path == '/':
                            if 'rsUrl' in data_data:
                                rs_url = data_data['rsUrl']
                            if 'rsPostUrl' in data_data:
                                rs_post_url = data_data['rsPostUrl']
                            if 'createAnswer' in data_data:
                                is_offerer = not data_data['createAnswer']
                        elif data_path == '/rsUrl':
                            rs_url = data_data
                    if rs_url != None:
                        break
                print(event)
                self.__taskQueueKeepAlive.cancel()
            except ConnectionError:
                pass

        await client_session.close()
        return rs_url, rs_post_url, is_offerer

    async def run(self, new_frame_callback, new_telemetry_callback=None):
        self.__new_frame_callback = new_frame_callback
        self.__new_telemetry_callback = new_telemetry_callback

        # wait for queue to return remote session url
        rs_url, rs_post_url, is_offerer = await self.get_remote_session_url()
        if rs_url == None:
            return

        # create signaling and peer connection
        signaling = RCSSignaling(self.__auth, rs_url, rs_post_url, is_offerer, self.__loop)
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
