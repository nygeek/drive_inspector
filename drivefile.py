""" Implementation of the DriveFile class

Started 2018-04-20 by Marc Donner
Copyright (C) 2018 Marc Donner

This class and the test code in the main() function at the bottom
are written to provide me with the ability to construct a systematic
inventory of the files in my Google Drive.

"""

import argparse
import json
import os
import sys
import time

import psutil
import httplib2

from apiclient import discovery
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage

reload(sys)
sys.setdefaultencoding('utf8')

APPLICATION_NAME = 'Drive Inventory'

# Cribbed from the quickstart.py code provided by Google
def get_credentials():
    """Gets valid user credentials from storage.

    If nothing has been stored, or if the stored credentials are invalid,
    the OAuth2 flow is completed to obtain the new credentials.

    Returns:
        Credentials, the obtained credential.
    """
    # If modifying these scopes, delete your previously saved credentials
    # at ~/.credentials/drive-python-quickstart.json
    scopes = 'https://www.googleapis.com/auth/drive.metadata.readonly'
    client_secret_file = '.client_secret.json'

    home_dir = os.path.expanduser('~')
    credential_dir = os.path.join(home_dir, '.credentials')
    if not os.path.exists(credential_dir):
        os.makedirs(credential_dir)
    credential_path = os.path.join(credential_dir,
                                   'drive-python-quickstart.json')

    store = Storage(credential_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(client_secret_file, scopes)
        flow.user_agent = APPLICATION_NAME
        # run_flow() also accepts some flags, but we do not understand
        # them.  The sample code has some argument parsing for the flags.
        credentials = tools.run_flow(flow, store)
        print 'Storing credentials to ' + credential_path
    return credentials

def pretty_json(json_object):
    """Return a pretty-printed string of a JSON object (string)."""
    return json.dumps(json_object, indent=4, separators=(',', ': '))

FOLDERMIMETYPE = 'application/vnd.google-apps.folder'

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
        self.service = discovery.build(
            'drive',
            'v3',
            http=get_credentials().authorize(httplib2.Http())
            )

    def get(self, file_id, debug=False):
        """Get the metadata for file_id."""
        fields = "id, name, parents, mimeType, owners, trashed"
        if debug:
            print "# get(file_id: " + file_id + ")"
        if file_id not in self.file_data:
            t_start = time.time()
            file_metadata = \
                self.service.files().get(
                    fileId=file_id,
                    fields=fields
                    ).execute()
            self.call_count += 1
            self.time_data[file_id] = time.time() - t_start
            self.file_data[file_id] = file_metadata
            self.ref_count[file_id] = 0
        self.ref_count[file_id] += 1
        _ = self.get_path(file_id)
        return self.file_data[file_id]

    def is_folder(self, file_id, debug=False):
        """Returns boolean whether file_id is a folder or not."""
        if debug:
            print "# is_folder(" + file_id + ")"
        if file_id not in self.file_data:
            file_metadata = self.get(file_id)
        else:
            file_metadata = self.file_data[file_id]
        result = file_metadata['mimeType'] == FOLDERMIMETYPE and \
                 ("fileExtension" not in file_metadata)
        if debug:
            print "#   => " + str(result)
        return result

    def list_subfolders(self, file_id, debug=False):
        """Get the folders below a file_id."""
        query = "'" + file_id + "' in parents"
        fields = "nextPageToken, "
        fields += "files(id, name, parents, mimeType, owners, trashed)"
        if debug:
            print "# list_subfolders(file_id: " + file_id + ")"
            print "# query: " + query
            print "# fields: " + fields
        npt = "start"
        while npt:
            if debug:
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
            if debug:
                print "# i: " + str(i)
            item_id = file_item['id']
            if item_id not in self.file_data:
                if debug:
                    print "# item_id: " + item_id
                self.file_data[item_id] = file_item
                self.ref_count[item_id] = 1
                _ = self.get_path(item_id)
            if self.is_folder(item_id):
                subfolders.append(item_id)
            i += 1
        return subfolders

    def list_children(self, file_id, debug=False):
        """Get the children of file_id."""
        query = "'" + file_id + "' in parents"
        fields = "nextPageToken, "
        fields += "files(id, name, parents, mimeType, owners, trashed)"
        if debug:
            print "# list_children(file_id: " + file_id + ")"
            print "# query: " + query
            print "# fields: " + fields
        npt = "start"
        while npt:
            if debug:
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
            if debug:
                print "# i: " + str(i)
            item_id = file_item['id']
            if item_id not in self.file_data:
                if debug:
                    print "# item_id: " + item_id
                self.file_data[item_id] = file_item
                self.ref_count[item_id] = 1
                _ = self.get_path(item_id)
            i += 1
        return children

    def get_parents(self, file_id, debug=False):
        """Given a file_id, get the list of parents."""
        if debug:
            print "# get_parents(" + file_id + ")"
        # check the cache
        if file_id not in self.file_data:
            # not in the cache, sadly.  Go to Google for data
            _ = self.get(file_id)
        if 'parents' in self.file_data[file_id]:
            results = self.file_data[file_id]['parents']
        else:
            results = ['<none>']
        if debug:
            print "# get_parents: " + str(results)
        return results

    def get_path(self, file_id, debug=False):
        """Given a file_id, construct the path back to root."""
        if debug:
            print "# get_path(" + file_id + ")"
        if file_id in self.path_data:
            return self.path_data[file_id]
        else:
            if file_id not in self.file_data:
                # Oops ... we are not in the file data either
                _ = self.get(file_id)
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
            result += pretty_json(self.file_data[file_id]) + "\n"
            if file_id in self.time_data:
                result += "time: " + str(self.time_data[file_id]) + "\n"
            result += "path: " + self.path_data[file_id] + "\n"
            result += "refs: " + str(self.ref_count[file_id]) + "\n"
        return result

class TestStats(object):
    """Organize and display stats for the running of the program."""

    def __init__(self):
        self.cpu_time_0 = psutil.cpu_times()
        self.iso_time_stamp = \
            time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
        self.program_name = sys.argv[0]

    def print_startup(self):
        """Display start-of-run information."""
        print
        print "# program_name: " + self.program_name
        print "# iso_time_stamp: " + self.iso_time_stamp
        print

    def print_final_report(self):
        """Print the final report form the test run."""
        cpu_time_1 = psutil.cpu_times()
        print
        print "# " + self.program_name + ": User time: " +\
            str(cpu_time_1[0] - self.cpu_time_0[0]) + " S"
        print "# " + self.program_name + "y: System time: " +\
            str(cpu_time_1[2] - self.cpu_time_0[2]) + " S"

def main():
    """Test code and basic CLI functionality engine."""

    debug = False

    test_stats = TestStats()
    test_stats.print_startup()

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
        help='When done running, dump the DriveFile object')

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
        debug = True

    if debug:
        print "args: " + str(args)

    drive_file = DriveFile()

    root_file = drive_file.get("root")
    if debug:
        print "root: " + pretty_json(root_file)

    if args.fileid != None:
        print "fileid: " + str(args.fileid)
        whatever = drive_file.get(args.fileid, debug)
        print "(" + args.fileid + "):\n"
        print pretty_json(whatever)

    if args.children != None:
        children = drive_file.list_children(args.children, debug)
        print "children of (" + args.children + ")"
        print pretty_json(children)

    if args.subfolders != None:
        subfolders = drive_file.list_subfolders(args.subfolders, debug)
        print "children of (" + args.subfolders + ")"
        i = 0
        for file_id in subfolders:
            if debug:
                print "# [" + str(i) + "] file_id: (" + file_id + ")"
            print drive_file.path_data[file_id]
            i += 1

    if args.find != None:
        # manage the traversal with a queue rather than with
        # recursion.
        queue = drive_file.list_children(args.find, debug)
        print "# find all children of (" + args.find + ")"
        num_files = 0
        num_folders = 0
        while queue:
            file_metadata = queue.pop(0)
            file_id = file_metadata['id']
            file_name = file_metadata['name']
            num_files += 1
            if debug:
                print "# [" + str(i) + "] file_id: (" + file_id + ") '" +\
                        file_name + "'"
            if drive_file.is_folder(file_id):
                num_folders += 1
                children = drive_file.list_children(file_id, debug)
                num_files += len(children)
                queue += children
                print "[" + str(num_folders) + "] " + \
                        drive_file.path_data[file_id] + \
                        " [" + str(len(children)) + "]"
        print "# num_folders: " + str(num_folders)
        print "# num_files: " + str(num_files)

    if args.dump:
        print "dumping drive_file ..."
        print str(drive_file)
        print

    print
    print "# call_count: " + str(drive_file.call_count)

    test_stats.print_final_report()

if __name__ == '__main__':
    main()
