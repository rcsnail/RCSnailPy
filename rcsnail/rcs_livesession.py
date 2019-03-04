import asyncio
import aiohttp
import pyrebase
#from .rcsnail import RCSnail
#from .rcs_main import RCSnail
#import RCSnail
from firebasedata import LiveData

from aiortc import (RTCIceCandidate, RTCPeerConnection, RTCSessionDescription,
                    VideoStreamTrack)
from aiortc.contrib.media import MediaBlackhole, MediaPlayer, MediaRecorder
from aiortc.contrib.signaling import object_from_string, object_to_string

class RCSLiveSession(object):
    """
    This is RCSnail live session class
    """

    def __init__(self, rcs, liveUrl):
        """
        """
        self.__rcs = rcs
        self.__liveUrl = liveUrl
        print(liveUrl)
        self.__pc = RTCPeerConnection()

