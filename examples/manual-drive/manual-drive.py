import asyncio
import os
from getpass import getpass
from rcsnail import RCSnail, RCSLiveSession

if __name__ == '__main__':
    print('RCSnail demo')
    username = os.getenv('RCS_USERNAME', '')
    password = os.getenv('RCS_PASSWORD', '')
    if username == '':
        username = input('Username: ')
    if password == '':
        password = getpass('Password: ')
    rcs = RCSnail(username, password)

    loop = asyncio.get_event_loop()
    liveSession = loop.run_until_complete(rcs.enqueue())
    try:
        loop.run_until_complete(liveSession.run())
    except KeyboardInterrupt:
        pass
    finally:
        # cleanup
        loop.run_until_complete(liveSession.stop())
