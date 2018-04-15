#
# dls.py
#
# Drive LS
#
# Written 2018-04-07 by Marc Donner
#

# Cribbed from quickstart.py code provided by the Google Drive API
# documentation.

import argparse
import datetime
import httplib2
import os
import psutil
import sys
import time

from apiclient import discovery
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage

# try:
#     import argparse
#     flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
# except ImportError:
#     flags = None

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

def getOwner(service, fileID):
    """Given a fileID, get owner information."""
    # print "# getOwner(" + fileID + ")"
    results = service.files().get(
            fileId=fileID,
            fields='owners'
            ).execute()
    # print "#     => " + str(results)
    if len(results) > 1:
        print "# more than one owner: " + str(fileId)
    ownerParts = results['owners'][0]
    return ownerParts

def getParents(service, fileID):
    """Given a fileID, get list of parent IDs."""
    # print "# getParents(" + fileID + ")"
    parents = service.files().get(
            fileId=fileID,
            fields='parents'
            ).execute()
    # print "#     => " + str(parents)
    if len(parents) > 1:
        print "# More than one parent: (" + fileID + ")"
    return parents['parents'][0]

# TODO fix this when you make the DriveFS class
pathFromFileID = {}

def getPath(service, fileID):
    """Given a fileID, construct the path from 'My Drive' to the file."""
    # print "# getPath(" + fileID + ")"
    # check the cache
    if fileID in pathFromFileID:
        return pathFromFileID[fileID]
    parent = getParents(service, fileID)
    parentName = getFileName(service, parent)
    if parentName == "My Drive":
        return "/My Drive"
    path = getPath(service, parent) + "/" + parentName
    # put the path in the cache
    pathFromFileID[fileID] = path
    return path

def getFileName(service, fileID):
    """Given a fileID, get file display name."""
    # print "# getFileName(" + fileID + ")"
    results = service.files().get(
            fileId=fileID,
            fields='name'
            ).execute()
    name = results['name']
    # print "#     => " + name
    return name

def main():
    """Shows basic usage of the Google Drive API.

    Creates a Google Drive API service object and outputs the names and IDs
    for up to 10 files.
    """

    # capture timing information
    cputime_0 = psutil.cpu_times()

    isoTimeStamp = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
    print "# dls.py: " + isoTimeStamp

    seen = {}

    credentials = get_credentials()
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('drive', 'v3', http=http)

    # Now list files whereever I am ...
    program_name = sys.argv[0]
    # print "program_name: " + program_name

    search_string = "Project Workbook"
    # print "search_string: " + search_string

    npt = "start"

    filesPerCall = 25
    fileNum = 0
    fields = "nextPageToken, files(id, name, parents)"
    while npt:
        if npt == "start":
            results = service.files().list(
                pageSize=filesPerCall, \
                fields=fields
                ).execute()
        else:
            results = service.files().list( \
                pageSize=filesPerCall, \
                pageToken=npt, \
                fields=fields
                ).execute()
        # print "# results: " + str(results)
        items = results.get('files', [])
        npt = results.get('nextPageToken')
        # print "npt: " + str(npt)
        if not items:
            print('No files found.')
        else:
            for item in items:
                fileID = item['id']
                if fileID not in seen:
                    seen[fileID] = 0
                seen[fileID] += 1
                print('[{0}]: \'{1}\' ({2})'.format( \
                    fileNum, \
                    item['name'].encode('utf-8'), \
                    seen[fileID] \
                    ))
                ownerData = getOwner(service, fileID)
                print "   owner:" + \
                        ownerData['displayName'] + " (" + \
                        ownerData['emailAddress'] + ")"
                path = getPath(service, fileID)
                print "  path: " + path
                parents = item['parents']
                # for parentID in parents:
                #     parentName = getFileName(service, parentID)
                #     print "   parent: '" + parentName + "'"
                fileNum += 1

    cputime_1 = psutil.cpu_times()
    print

    print "# dls.py: User time: " +\
            str(cputime_1[0] - cputime_0[0]) + " S"
    print "# dls.py: fileNum: " + str(fileNum)
    print "# dls.py: User time per record: " +\
            str(1e3 * (cputime_1[0] - cputime_0[0]) / fileNum) +\
            " mS"
    print "# dls.py: System time: " +\
            str(cputime_1[2] - cputime_0[2]) + " S"
    print "# dls.py: System time per record: " +\
            str(1e3 * (cputime_1[2] - cputime_0[2]) / fileNum) +\
            " mS"

if __name__ == '__main__':
    main()
