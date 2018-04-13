#
# dls.py
#
# Drive LS
#
# Written 2018-04-07 by Marc Donner
#

# cribbed from quickstart.py code provided by the Google Drive API
# documentation

import httplib2
import os
import sys

from apiclient import discovery
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage

try:
    import argparse
    flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
except ImportError:
    flags = None

# If modifying these scopes, delete your previously saved credentials
# at ~/.credentials/drive-python-quickstart.json
SCOPES = 'https://www.googleapis.com/auth/drive.metadata.readonly'
CLIENT_SECRET_FILE = '.client_secret.json'
APPLICATION_NAME = 'Drive API Python Quickstart'

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
        if flags:
            credentials = tools.run_flow(flow, store, flags)
        else: # Needed only for compatibility with Python 2.6
            credentials = tools.run(flow, store)
        print('Storing credentials to ' + credential_path)
    return credentials

def main():
    """Shows basic usage of the Google Drive API.

    Creates a Google Drive API service object and outputs the names and IDs
    for up to 10 files.
    """
    credentials = get_credentials()
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('drive', 'v3', http=http)

    # Now list files whereever I am ...
    program_name = sys.argv[0]
    # print "program_name: " + program_name

    search_string = "Project Workbook"
    # print "search_string: " + search_string

    filesPerCall = 25
    fileID = 0
    results = service.files().list(
        pageSize=filesPerCall, \
        fields="nextPageToken, files(id, name)" \
        ).execute()
    items = results.get('files', [])
    npt = results.get('nextPageToken')
    # print "npt: " + str(npt)
    if not items:
        print('No files found.')
    else:
        # print('Files:')
        for item in items:
            print('[{0}]: \'{1}\''.format( \
                fileID, \
                item['name'].encode('utf-8').strip()))
            fileID += 1

    while npt:
        results = service.files().list( \
            pageSize=filesPerCall, \
            pageToken=npt, \
            fields="nextPageToken, files(id, name)").execute()
        items = results.get('files', [])
        npt = results.get('nextPageToken')
        # print "npt: " + str(npt)
        if not items:
            print('No more files found.')
        else:
            for item in items:
                print('[{0}]: \'{1}\''.format(fileID, item['name'].encode('utf-8').strip()))
                fileID += 1

if __name__ == '__main__':
    main()
