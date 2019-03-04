# RCSnailPy
Python wrapper for RCSnail API

## Python virtual environment with pip3
    sudo pip3 install virtualenv
or 
    sudo apt-get install python3-venv

### Create Python3 rcsnail-env virtualenv
    virtualenv -p python3 rcsnail-env

### or directly with Python3
    python3 -m venv rcsnail-env
        
### (Re)active virtualenv
    source rcsnail-env/bin/activate

### Deactivate virtualenv
    deactivate

## Install dependencies
    sudo apt install libavdevice-dev libavfilter-dev libopus-dev libvpx-dev pkg-config python3-opencv
    pip3 install aiohttp aiortc opencv-python websockets FirebaseData pyrebase 
