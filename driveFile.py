#
# This is the DriveFile class
#

#
# Started 2018-04-20 by Marc Donner
# Copyright (C) 2018 Marc Donner
#

import argparse
import datetime
import httplib2
import json
import os
import psutil
import sys
import time

from apiclient import discovery
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage

reload(sys)
sys.setdefaultencoding('utf8')

# If modifying these scopes, delete your previously saved credentials
# at ~/.credentials/drive-python-quickstart.json
SCOPES = 'https://www.googleapis.com/auth/drive.metadata.readonly'
CLIENT_SECRET_FILE = '.client_secret.json'
APPLICATION_NAME = 'Drive Inventory'

def get_credentials():
    """Gets valid user credentials from storage.

    If nothing has been stored, or if the stored credentials are invalid,
    the OAuth2 flow is completed to obtain the new credentials.

    Returns:
        Credentials, the obtained credential.
    """
    home_dir = os.path.expanduser('~')
    credential_dir = os.path.join(home_dir, '.credentials')
    if not os.path.exists(credential_dir):
        os.makedirs(credential_dir)
    credential_path = os.path.join(credential_dir,
                                   'drive-python-quickstart.json')

    store = Storage(credential_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
        flow.user_agent = APPLICATION_NAME
        # run_flow() also accepts some flags, but we do not understand
        # them.  The sample code has some argument parsing for the flags.
        credentials = tools.run_flow(flow, store)
        print('Storing credentials to ' + credential_path)
    return credentials

def prettyJSON(json_object):
    return json.dumps(json_object, indent=4, separators=(',', ': '))

class DriveFile(object):
    """Class to provide cached access to Google Drive object metadata."""
    FOLDERMIMETYPE = 'application/vnd.google-apps.folder'

    def __init__(self):
        self.fileData = {}
        self.credentials = get_credentials()
        self.http = self.credentials.authorize(httplib2.Http())
        self.service = discovery.build('drive', 'v3', http=self.http)

    def get(self, file_id):
        file_data = self.service.files().get(fileId=file_id).execute()
        self.fileData[file_id] = file_data
        return file_data

def main():

    program_name = sys.argv[0]
    print "program_name: " + program_name

    parser = argparse.ArgumentParser(description='Accept a path.')

    parser.add_argument('path', type=str, nargs='?',\
            default='root', help='Path')

    args = parser.parse_args()

    print "path: " + args.path

    df = DriveFile()
    root_file = df.get("root")
    print prettyJSON(root_file)

if __name__ == '__main__':
    main()
