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
    $ pip install wheel aiohttp aiohttp-sse-client aiortc opencv-python websockets FirebaseData pirebase

## Module Development
    $ python setup.py develop


## Windows
Building with Visual Studio VS2017 and installing dependencies manually from
https://github.com/cisco/libsrtp/releases/tag/v2.2.0
http://opus-codec.org/release/stable/2018/10/18/libopus-1_3.html
https://github.com/webmproject/libvpx

Compiled libraries and headers are under 3rdparty folder. Use win-prepare.bat file to install aiortc on Windows.
