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

APPLICATION_NAME = 'Drive Inventory'

def get_credentials():
    """Gets valid user credentials from storage.

    If nothing has been stored, or if the stored credentials are invalid,
    the OAuth2 flow is completed to obtain the new credentials.

    Returns:
        Credentials, the obtained credential.
    """
    # If modifying these scopes, delete your previously saved credentials
    # at ~/.credentials/drive-python-quickstart.json
    SCOPES = 'https://www.googleapis.com/auth/drive.metadata.readonly'
    CLIENT_SECRET_FILE = '.client_secret.json'

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
        self.timeData = {}
        self.credentials = get_credentials()
        self.http = self.credentials.authorize(httplib2.Http())
        self.service = discovery.build('drive', 'v3', http=self.http)

    def get(self, file_id):
        """Get the metadata for file_id."""
        print "# get(file_id: " + file_id + ")"
        if file_id in self.fileData:
            return self.fileData[file_id]
        else:
            t0 = time.time()
            file_data = self.service.files().get(fileId=file_id).execute()
            elapsed = time.time() - t0
            self.fileData[file_id] = file_data
            self.timeData[file_id] = elapsed
            return file_data

    def list_root_children(self):
        """Get the children of root."""
        print "# list_root_children()"
        query = "'0APmGZa1CyME_Uk9PVA' in parents"
        print "# query: " + query
        file_list = self.service.files().list(
                q=query
                ).execute()
        return file_list

    def list_children(self, file_id):
        """Get the children of file_id."""
        print "# list_children(file_id: " + file_id + ")"
        query = "'" + file_id + "' in parents"
        print "# query: " + query
        fields = "nextPageToken, "
        fields += "files(id, name, parents, mimeType, owners)"
        print "# fields: " + fields
        npt = "start"
        while npt:
            print "npt: (" + npt + ")"
            if npt == "start":
                results = self.service.files().list(
                        q=query,
                        fields=fields
                        ).execute()
                children = results.get('files', [])
                npt = results.get('nextPageToken')
            else:
                results = self.service.files().list(
                        pageToken=npt,
                        q=query,
                        fields=fields
                        ).execute()
                children += results.get('files', [])
                npt = results.get('nextPageToken')
        i = 0
        for file_item in children:
            print "# i: " + str(i)
            item_id = file_item['id']
            print "# item_id: " + item_id
            self.fileData[item_id] = file_item
            i += 1
        return children

    def __str__(self):
        result = ""
        for file_id in self.fileData:
            result += "(" + file_id + "):\n"
            result += prettyJSON(self.fileData[file_id])
            result += '\n' 
        return result

def main():

    # capture timing information
    cputime_0 = psutil.cpu_times()

    isoTimeStamp = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
    print "# isoTimeStamp: " + isoTimeStamp

    program_name = sys.argv[0]
    print "program_name: " + program_name

    description = "Use the Google Drive API (REST v3) to get information "
    description += "about files to which you have access."
    parser = argparse.ArgumentParser(description=description)

    parser.add_argument(
            '-p',
            '--path',
            type=str,
            help='Given a path, fetch and display the metadata.')

    parser.add_argument(
            '-f',
            '--fileid',
            type=str,
            help='Given a fileid, fetch and display the metadata.')

    args = parser.parse_args()
    print "args: " + str(args)

    df = DriveFile()

    root_file = df.get("root")
    print "root: " + prettyJSON(root_file)

    if args.path != None:
        print "path: " + str(args.path)
        root_file = df.get(args.path)
        print "root"
        print prettyJSON(root_file)

    if args.fileid != None:
        print "fileid: " + str(args.fileid)
        whatever = df.get(args.fileid)
        print "(" + args.fileid + "):\n"
        print prettyJSON(whatever)

    # children = df.list_root_children()
    # print "children of root:"
    # print prettyJSON(children)

    children = df.list_children("0APmGZa1CyME_Uk9PVA")
    print "children of 0APmGZa1CyME_Uk9PVA:"
    print prettyJSON(children)


    print "\n...\n"

    print "df:"
    print str(df)

    print "\n...\n"

    cputime_1 = psutil.cpu_times()
    print "# " + program_name + ": User time: " +\
            str(cputime_1[0] - cputime_0[0]) + " S"
    print "# " + program_name + "y: System time: " +\
            str(cputime_1[2] - cputime_0[2]) + " S"

if __name__ == '__main__':
    main()
