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
        self.file_data = {}
        self.file_data['<none>'] = {}
        self.time_data = {}
        self.time_data['<none>'] = 0
        self.path_data = {}
        self.path_data['<none>'] = ""
        self.path_data['root'] = ""
        self.ref_count = {}
        self.ref_count['<none>'] = 0
        self.credentials = get_credentials()
        self.http = self.credentials.authorize(httplib2.Http())
        self.service = discovery.build('drive', 'v3', http=self.http)

    def get(self, file_id):
        """Get the metadata for file_id."""
        fields = "id, name, parents, mimeType, owners, trashed"
        print "# get(file_id: " + file_id + ")"
        if file_id not in self.file_data:
            t0 = time.time()
            file_metadata = \
                self.service.files().get(
                        fileId=file_id,
                        fields=fields
                        ).execute()
            self.time_data[file_id] = time.time() - t0
            self.file_data[file_id] = file_metadata
            self.ref_count[file_id] = 0
        self.ref_count[file_id] += 1
        path = self.get_path(file_id)
        return self.file_data[file_id]

    def list_children(self, file_id):
        """Get the children of file_id."""
        print "# list_children(file_id: " + file_id + ")"
        query = "'" + file_id + "' in parents"
        print "# query: " + query
        fields = "nextPageToken, "
        fields += "files(id, name, parents, mimeType, owners, trashed)"
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
            if item_id not in self.file_data:
                print "# item_id: " + item_id
                self.file_data[item_id] = file_item
                self.ref_count[item_id] = 1
                path = self.get_path(item_id)
            i += 1
        return children

    def get_parents(self, file_id):
        """Given a file_id, get the list of parents."""
        print "# get_parents(" + file_id + ")"
        # check the cache
        if file_id not in self.file_data:
            # not in the cache, sadly.  Go to Google for data
            file_metadata = self.get(file_id)
        if 'parents' in self.file_data[file_id]:
            results = self.file_data[file_id]['parents']
        else:
            results = ['<none>']
        print "# get_parents: " + str(results)
        return results

    def get_path(self, file_id):
        """Given a file_id, construct the path back to root."""
        print "# get_path(" + file_id + ")"
        if file_id in self.path_data:
            return self.path_data[file_id]
        else:
            if file_id not in self.file_data:
                # Oops ... we are not in the file data either
                file_metadata = self.get(file_id)
            file_name = self.file_data[file_id]['name']
            if 'parents' not in self.file_data[file_id]:
                parent = 'root'
            else:
                parent = self.file_data[file_id]['parents'][0]
            if file_name == "My Drive":
                self.path_data[file_id] = ""
                return ""
            self.path_data[file_id] = self.get_path(parent) + \
                "/" + file_name
            return self.path_data[file_id]

    def __str__(self):
        result = ""
        for file_id in self.file_data:
            result += "(" + file_id + "):\n"
            result += prettyJSON(self.file_data[file_id]) + "\n"
            if file_id in self.time_data:
                result += "time: " + str(self.time_data[file_id]) + "\n"
            result += "path: " + self.path_data[file_id] + "\n"
            result += "refs: " + str(self.ref_count[file_id]) + "\n"
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

    parser.add_argument(
            '-c',
            '--children',
            type=str,
            help='Given a fileid, display the metadata for the children.')

    parser.add_argument(
            '-d',
            '--dump',
            action='store_const', const=True,
            help='When done running, dump the driveFile object')

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

    if args.children != None:
        children = df.list_children(args.children)
        print "children of (" + args.children + ")"
        print prettyJSON(children)

    # children = df.list_children("0APmGZa1CyME_Uk9PVA")
    # print "children of (0APmGZa1CyME_Uk9PVA):"
    # print prettyJSON(children)

    if args.dump:
        print "dumping df ..."
        print str(df)
        print

    cputime_1 = psutil.cpu_times()
    print "# " + program_name + ": User time: " +\
            str(cputime_1[0] - cputime_0[0]) + " S"
    print "# " + program_name + "y: System time: " +\
            str(cputime_1[2] - cputime_0[2]) + " S"

if __name__ == '__main__':
    main()
