import asyncio
import fractions
import logging
import threading
import time

import av
from av import AudioFrame, VideoFrame
from aiortc.mediastreams import MediaStreamError, MediaStreamTrack

class MediaRendererContext:
    def __init__(self, frame):
        self.frame = frame
        self.task = None


class MediaRenderer:
    """
    A media sink that exposes video frames as events when they arrive
    """
    def __init__(self, new_frame_callback):
        self.__tracks = {}
        self.__new_frame_callback = new_frame_callback

    def addTrack(self, track):
        """
        Add a track to be recorded.

        :param: track: An :class:`aiortc.AudioStreamTrack` or :class:`aiortc.VideoStreamTrack`.
        """
        if track.kind == 'video':
            self.__tracks[track] = MediaRendererContext(None)

    async def start(self):
        """
        Start rendering.
        """
        for track, context in self.__tracks.items():
            if context.task is None:
                context.task = asyncio.ensure_future(self.__run_track(track, context))

    async def stop(self):
        """
        Stop rendering.
        """
        for track, context in self.__tracks.items():
            if context.task is not None:
                context.task.cancel()
                context.task = None
        self.__tracks = {}

    async def __run_track(self, track, context):
        while True:
            try:
                frame = await track.recv()
            except MediaStreamError:
                return
            if self.__new_frame_callback:
                self.__new_frame_callback(frame)
