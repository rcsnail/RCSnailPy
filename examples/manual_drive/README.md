# RCSnail API manual drive example

This example shows how to use RCSnail API to login, queue and drive manually the remote RC car video video feed.
Pygame + asyncio code is based on example from https://github.com/AlexElvers/pygame-with-asyncio

## Python virtual environment with pip3
    sudo apt-get install python3-venv

### Create virtual environment
    python3 -m venv .venv

### Activate the virtua environment
    source .venv/bin/activate

### To deactivate
    deactivate
    
### Install the required packages:

    pip install rcsnailpy pygame
    
## Run the code:

    $ python manual-drive.py

### Add username and password to env variables:

    RCS_USERNAME
    RCS_PASSWORD

or in VSCode to launch.json "configurations":

        {
            "name": "Python: Current File",
            "type": "python",
            "request": "launch",
            "env": {"RCS_USERNAME":"test@test.ee", "RCS_PASSWORD":"password"},
            "program": "${file}"
        },
        {
            "name": "Python: Manual Drive",
            "type": "python",
            "request": "launch",
            "env": {"RCS_USERNAME":"test@test.ee", "RCS_PASSWORD":"password"},
            "program": "${workspaceFolder}/examples/manual_drive/manual_drive.py"
        },        
    
