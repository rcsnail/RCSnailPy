from rcsnail import RCSnail
import os
from getpass import getpass

if __name__ == '__main__':
    print('RCSnail demo')
    username = os.getenv('RCS_USERNAME', '')
    password = os.getenv('RCS_PASSWORD', '')
    if username == '':
        username = input('Username: ')
    if password == '':
        password = getpass('Password: ')
    rcs = RCSnail(username, password)
