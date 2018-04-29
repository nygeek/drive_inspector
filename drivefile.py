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
        print 'Storing credentials to ' + credential_path
    return credentials

def prettyJSON(json_object):
    return json.dumps(json_object, indent=4, separators=(',', ': '))

FOLDERMIMETYPE = 'application/vnd.google-apps.folder'

# this is the flag to control display of debug messages.
DEBUG = False

class DriveFile(object):
    """Class to provide cached access to Google Drive object metadata."""

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
        self.call_count = 0
        self.credentials = get_credentials()
        self.http = self.credentials.authorize(httplib2.Http())
        self.service = discovery.build('drive', 'v3', http=self.http)

    def get(self, file_id):
        """Get the metadata for file_id."""
        global DEBUG
        fields = "id, name, parents, mimeType, owners, trashed"
        if DEBUG:
            print "# get(file_id: " + file_id + ")"
        if file_id not in self.file_data:
            t0 = time.time()
            file_metadata = \
                self.service.files().get(
                    fileId=file_id,
                    fields=fields
                    ).execute()
            self.call_count += 1
            self.time_data[file_id] = time.time() - t0
            self.file_data[file_id] = file_metadata
            self.ref_count[file_id] = 0
        self.ref_count[file_id] += 1
        path = self.get_path(file_id)
        return self.file_data[file_id]

    def is_folder(self, file_id):
        """Returns boolean whether file_id is a folder or not."""
        global DEBUG
        fields = "id, name, parents, mimeType, owners, trashed"
        if DEBUG:
            print "# is_folder(" + file_id + ")"
        if file_id not in self.file_data:
            file_metadata = self.get(file_id)
        else:
            file_metadata = self.file_data[file_id]
        result = file_metadata['mimeType'] == FOLDERMIMETYPE and \
                 ("fileExtension" not in file_metadata)
        if DEBUG:
            print "#   => " + str(result)
        return result

    def list_subfolders(self, file_id):
        """Get the folders below a file_id."""
        global DEBUG
        if DEBUG:
            print "# list_subfolders(file_id: " + file_id + ")"
        query = "'" + file_id + "' in parents"
        if DEBUG:
            print "# query: " + query
        fields = "nextPageToken, "
        fields += "files(id, name, parents, mimeType, owners, trashed)"
        if DEBUG:
            print "# fields: " + fields
        npt = "start"
        while npt:
            if DEBUG:
                print "npt: (" + npt + ")"
            if npt == "start":
                results = self.service.files().list(
                    q=query,
                    fields=fields
                    ).execute()
                self.call_count += 1
                children = results.get('files', [])
                npt = results.get('nextPageToken')
            else:
                results = self.service.files().list(
                    pageToken=npt,
                    q=query,
                    fields=fields
                    ).execute()
                self.call_count += 1
                children += results.get('files', [])
                npt = results.get('nextPageToken')
        i = 0
        # now comb through the children and add the folders to
        # the results vector
        subfolders = []
        for file_item in children:
            if DEBUG:
                print "# i: " + str(i)
            item_id = file_item['id']
            if item_id not in self.file_data:
                if DEBUG:
                    print "# item_id: " + item_id
                self.file_data[item_id] = file_item
                self.ref_count[item_id] = 1
                path = self.get_path(item_id)
            if self.is_folder(item_id):
                subfolders.append(item_id)
            i += 1
        return subfolders

    def list_children(self, file_id):
        """Get the children of file_id."""
        global DEBUG
        if DEBUG:
            print "# list_children(file_id: " + file_id + ")"
        query = "'" + file_id + "' in parents"
        if DEBUG:
            print "# query: " + query
        fields = "nextPageToken, "
        fields += "files(id, name, parents, mimeType, owners, trashed)"
        if DEBUG:
            print "# fields: " + fields
        npt = "start"
        while npt:
            if DEBUG:
                print "# npt: (" + npt + ")"
            if npt == "start":
                results = self.service.files().list(
                    q=query,
                    fields=fields
                    ).execute()
                self.call_count += 1
                children = results.get('files', [])
                npt = results.get('nextPageToken')
            else:
                results = self.service.files().list(
                    pageToken=npt,
                    q=query,
                    fields=fields
                    ).execute()
                self.call_count += 1
                children += results.get('files', [])
                npt = results.get('nextPageToken')
        i = 0
        for file_item in children:
            if DEBUG:
                print "# i: " + str(i)
            item_id = file_item['id']
            if item_id not in self.file_data:
                if DEBUG:
                    print "# item_id: " + item_id
                self.file_data[item_id] = file_item
                self.ref_count[item_id] = 1
                path = self.get_path(item_id)
            i += 1
        return children

    def get_parents(self, file_id):
        """Given a file_id, get the list of parents."""
        global DEBUG
        if DEBUG:
            print "# get_parents(" + file_id + ")"
        # check the cache
        if file_id not in self.file_data:
            # not in the cache, sadly.  Go to Google for data
            file_metadata = self.get(file_id)
        if 'parents' in self.file_data[file_id]:
            results = self.file_data[file_id]['parents']
        else:
            results = ['<none>']
        if DEBUG:
            print "# get_parents: " + str(results)
        return results

    def get_path(self, file_id):
        """Given a file_id, construct the path back to root."""
        global DEBUG
        if DEBUG:
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

    global DEBUG

    # capture timing information
    cputime_0 = psutil.cpu_times()

    print

    isoTimeStamp = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
    print "# isoTimeStamp: " + isoTimeStamp

    program_name = sys.argv[0]
    print "# program_name: " + program_name

    print

    description = "Use the Google Drive API (REST v3) to get information "
    description += "about files to which you have access."
    parser = argparse.ArgumentParser(description=description)

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

    parser.add_argument(
        '-f',
        '--fileid',
        type=str,
        help='Given a fileid, fetch and display the metadata.')

    parser.add_argument(
        '--find',
        type=str,
        help='Given a fileid, recursively traverse all subfolders.')

    parser.add_argument(
        '-s',
        '--subfolders',
        type=str,
        help='List the subfolders of the FileID')

    parser.add_argument(
        '-D',
        '--DEBUG',
        '--Debug',
        action='store_const', const=True,
        help='Turn debugging on')

    args = parser.parse_args()

    if args.DEBUG:
        DEBUG = True

    if DEBUG:
        print "args: " + str(args)

    df = DriveFile()

    root_file = df.get("root")
    if DEBUG:
        print "root: " + prettyJSON(root_file)

    if args.fileid != None:
        print "fileid: " + str(args.fileid)
        whatever = df.get(args.fileid)
        print "(" + args.fileid + "):\n"
        print prettyJSON(whatever)

    if args.children != None:
        children = df.list_children(args.children)
        print "children of (" + args.children + ")"
        print prettyJSON(children)

    if args.subfolders != None:
        subfolders = df.list_subfolders(args.subfolders)
        print "children of (" + args.subfolders + ")"
        i = 0
        for file_id in subfolders:
            if DEBUG:
                print "# [" + str(i) + "] file_id: (" + file_id + ")"
            print df.path_data[file_id]
            i += 1

    if args.find != None:
        # manage the traversal with a queue rather than with
        # recursion.
        queue = df.list_children(args.find)
        print "# find all children of (" + args.find + ")"
        num_files = 0
        num_folders = 0
        while queue:
            file_metadata = queue.pop(0)
            file_id = file_metadata['id']
            file_name = file_metadata['name']
            num_files += 1
            if DEBUG:
                print "# [" + str(i) + "] file_id: (" + file_id + ") '" +\
                        file_name + "'"
            if df.is_folder(file_id):
                num_folders += 1
                children = df.list_children(file_id)
                num_files += len(children)
                queue += children
                print "[" + str(num_folders) + "] " + \
                        df.path_data[file_id] + \
                        " [" + str(len(children)) + "]"
        print "# num_folders: " + str(num_folders)
        print "# num_files: " + str(num_files)

    # children = df.list_children("0APmGZa1CyME_Uk9PVA")
    # print "children of (0APmGZa1CyME_Uk9PVA):"
    # print prettyJSON(children)

    if args.dump:
        print "dumping df ..."
        print str(df)
        print

    print

    print "# call_count: " + str(df.call_count)

    cputime_1 = psutil.cpu_times()
    print "# " + program_name + ": User time: " +\
            str(cputime_1[0] - cputime_0[0]) + " S"
    print "# " + program_name + "y: System time: " +\
            str(cputime_1[2] - cputime_0[2]) + " S"

if __name__ == '__main__':
    main()
