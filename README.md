# RCSnailPy
Python wrapper for RCSnail API

## Python virtual environment with pip3
    $ sudo apt-get install python3-venv

### Create Python3 rcsnail-env virtualenv
    $ python3 -m venv .venv
        
### (Re)active virtualenv
    $ source .venv/bin/activate

### Deactivate virtualenv
    $ deactivate

## Install dependencies
    $ sudo apt install libavdevice-dev libavfilter-dev libopus-dev libvpx-dev pkg-config python3-dev python3-opencv
    $ pip3 install aiohttp aiohttp-sse-client aiortc opencv-python websockets FirebaseData pyrebase

## Module Development
    $ python3 setup.py develop

