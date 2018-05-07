""" Implementation of the DriveInspector tools and utilities

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

# This disable is probably overkill.  It silences the pylint whining
# about no-member when encountering references to
# apiclient.discovery.service()
#
# pylint: disable=no-member
#
from apiclient import discovery

from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage

# Work items
# [+] 2018-04-29 Create a function Path => FileID (namei, basically)
# [x] 2018-04-29 Normalize the DrivePath functions - two sorts
#     one that returns a list of file metadata objects and one
#     the returns just a list of FileIDs.
#         2018-05-06 - replacing this with a render / view approach
# [+] 2018-04-29 Naming convention for functions that return
#     metadata versus FileID list
# [ ] 2018-04-29 Add a local store for state.  Needed for the
#     PWD and CD functionality and for cache persistence
# [+] 2018-04-29 Figure out how to fix the PyLint errors that come
#     from the oauth2client.file.Storage ... this is a dynamic method
#     and PyLint reports an error (false positive) from it.
#         2018-05-05 put in a '# pylint: ' directive to stop the messages
# [+] 2018-04-29 Implement an ls function - Path => FileID => list
# [+] 2018-05-04 Figure out convention so that we can pass either a
#     a path OR a FileID to one of the main methods (find, ls, ...)
#         2018-05-06 did this with a kluge.  Not happy ... I'd prefer
#         some clever polymorphism that diagnoses what string is a
#         path and what is a FileID.
# [+] 2018-05-06 Make each search function return a list of FileIDs
# [ ] 2018-05-06 Make each retrieve function accept a list of FileIDs
#     and a list of attributes and return a 2D array of values
# [ ] 2018-05-06 Make a flag to modify the --find operation to show
#     either just the directories or all of the files.

reload(sys)
sys.setdefaultencoding('utf8')

APPLICATION_NAME = 'Drive Inspector'

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
STANDARD_FIELDS = "id, name, parents, mimeType, owners, trashed"

class DriveFile(object):
    """Class to provide cached access to Google Drive object metadata."""

    def __init__(self):
        self.file_data = {}
        self.file_data['<none>'] = {}
        self.time_data = {}
        self.time_data['<none>'] = 0
        self.path_data = {}
        self.path_data['<none>'] = ""
        self.path_data['root'] = "/"
        self.ref_count = {}
        self.ref_count['<none>'] = 0
        self.call_count = 0
        self.service = discovery.build(
            'drive',
            'v3',
            http=get_credentials().authorize(httplib2.Http())
            )

    def get(self, file_id, debug=False):
        """Get the metadata for file_id.
           Returns: metadata structure
        """
        if debug:
            print "# get(file_id: " + file_id + ")"
        if file_id not in self.file_data:
            t_start = time.time()
            file_metadata = \
                self.service.files().get(
                    fileId=file_id,
                    fields=STANDARD_FIELDS
                    ).execute()
            self.call_count += 1
            self.time_data[file_id] = time.time() - t_start
            self.file_data[file_id] = file_metadata
            self.ref_count[file_id] = 0
        self.ref_count[file_id] += 1
        _ = self.get_path(file_id)
        return self.file_data[file_id]

    def resolve_path(self, path, debug=False):
        """Given a path, find and return the FileID matching the
           terminal node.
           Returns: FileID
        """
        if debug:
            print "# resolve_path(" + str(path) + ")"
        # for now the path should begin with /
        if path[0] != "/":
            print "Error: only rooted paths for now."
            return "<error>"
        if path in self.path_data.values():
            for file_id, dict_path in self.path_data.iteritems():
                if dict_path == path:
                    return file_id
                # better not ever get here!
        path_components = path.split("/")
        # this pop drops the leading empty string
        path_components.pop(0)
        if debug:
            print "path_components: " + str(path_components)
        node = self.get("root")['id']
        for component in path_components:
            node = self.get_named_child(node, component, debug)
            if node in ["<not_found>", "<error"]:
                return node
            if debug:
                print "# " + component + " => (" + node + ")"
        return node

    def get_named_child(self, file_id, component, debug=False):
        """ Given a file_id (folder) and a component name, find the
            matching child, if it exists.
            Returns: FileID
            Returns: <not_found> if there is no child by that name
        """
        if debug:
            print "# get_named_child(" + file_id + ", " + component + ")"
        children = self.list_children(file_id, debug)
        for child_id in children:
            if child_id not in self.file_data:
                _ = self.get(child_id)
            if self.file_data[child_id]['name'] == component:
                # found it!
                return child_id
        return "<not_found>"

    def is_folder(self, file_id, debug=False):
        """Test whether file_id is a folder.
           Returns: Boolean
        """
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
        """Get the folders that have a given file_id as a parent.
           Returns: array of FileID
        """
        query = "'" + file_id + "' in parents"
        fields = "nextPageToken, "
        # fields += "files(id, name, parents, mimeType, owners, trashed)"
        fields += "files(" + STANDARD_FIELDS + ")"
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
        """Get the children of file_id.
           Returns: array of FileID
        """
        query = "'" + file_id + "' in parents"
        fields = "nextPageToken, "
        # fields += "files(id, name, parents, mimeType, owners, trashed)"
        fields += "files(" + STANDARD_FIELDS + ")"
        if debug:
            print "# list_children(file_id: " + file_id + ")"
            print "# query: " + query
            print "# fields: " + fields
        npt = "start"
        while npt:
            if debug:
                print "# npt: (" + npt + ")"
            if npt == "start":
                _ = self.service.files().list(
                    q=query,
                    fields=fields
                    ).execute()
                self.call_count += 1
                children = _.get('files', [])
                npt = _.get('nextPageToken')
            else:
                _ = self.service.files().list(
                    pageToken=npt,
                    q=query,
                    fields=fields
                    ).execute()
                self.call_count += 1
                children += _.get('files', [])
                npt = _.get('nextPageToken')
        i = 0
        results = []
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
                results.append(item_id)
            i += 1
        return results

    def get_parents(self, file_id, debug=False):
        """Given a file_id, get the list of parents.
           Returns: array of FileID
        """
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
        """Given a file_id, construct the path back to root.
           Returns: string
        """
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
                self.path_data[file_id] = "/"
                return ""
            self.path_data[file_id] = self.get_path(parent) + file_name
            if self.is_folder(file_id):
                self.path_data[file_id] += "/"
            return self.path_data[file_id]

    def show_metadata(self, path, file_id, debug=False):
        """ Display the metadata for a node."""
        if path is not None:
            if debug:
                print "# show_metadata(path: '" + path + "')"
            file_id = self.resolve_path(path, debug)
        else:
            if debug:
                print "# show_metadata(file_id: (" + file_id + "))"
        print pretty_json(self.get(file_id))

    def show_children(self, path, file_id, debug=False):
        """ Display the names of the children of a node.
            This is the core engine of the --ls function.
        """
        if path is not None:
            if debug:
                print "# show_children(path: '" + path + "')"
            file_id = self.resolve_path(path, debug)
        else:
            if debug:
                print "# show_children(file_id: (" + file_id + "))"
        children = self.list_children(file_id, debug)
        if debug:
            print "children: " + str(children)
        for child in children:
            if debug:
                print "# child: " + str(child)
            child_name = self.get(child)['name']
            if self.is_folder(child):
                child_name += "/"
            print child_name

    def show_all_children(self, path, file_id, debug=False):
        """ Display all child directories of a node
            This is the core engine of the --find function.
        """
        if path is not None:
            if debug:
                print "# show_all_children(path: '" + path + "')"
            file_id = self.resolve_path(path, debug)
        else:
            if debug:
                print "# show_all_children(file_id: (" + file_id + "))"
        queue = self.list_children(file_id, debug)
        num_files = 0
        num_folders = 0
        while queue:
            file_id = queue.pop(0)
            file_metadata = self.get(file_id)
            file_name = file_metadata['name']
            num_files += 1
            if debug:
                print "# file_id: (" + file_id + ") '" +\
                        file_name + "'"
            if self.is_folder(file_id):
                num_folders += 1
                children = self.list_children(file_id, debug)
                num_files += len(children)
                queue += children
                print "[" + str(num_folders) + "] " + \
                        self.get_path(file_id) + \
                        " [" + str(len(children)) + "]"
        print "# num_folders: " + str(num_folders)
        print "# num_files: " + str(num_files)

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
    args_are_paths = True

    test_stats = TestStats()
    test_stats.print_startup()

    parser = argparse.ArgumentParser(description=\
        "Use the Google Drive API (REST v3) to get information " + \
        "about files to which you have access."\
        )
    parser.add_argument(
        '-d',
        '--dump',
        action='store_const', const=True,
        help='When done running, dump the DriveFile object'
        )
    parser.add_argument(
        # this modifier causes args_are_paths to be set False
        '-f',
        action='store_const', const=True,
        help='Modifier.  Argument to stat, ls, find will be a FileID.'
        )
    parser.add_argument(
        '--find',
        type=str,
        help='Given a fileid, recursively traverse all subfolders.'
        )
    parser.add_argument(
        '-l',
        '--ls',
        type=str,
        help='Given a path, list the files contained in it.'
        )
    parser.add_argument(
        '--stat',
        type=str,
        help="Return the metadata for the node at the end of a path."
        )
    parser.add_argument(
        '-D',
        '--DEBUG',
        action='store_const', const=True,
        help='Turn debugging on'
        )

    args = parser.parse_args()

    if args.DEBUG:
        debug = True
        print "args: " + str(args)

    if args.f:
        args_are_paths = False

    # Do the work ...

    drive_file = DriveFile()

    if args.find != None:
        if args_are_paths:
            if debug:
                print "# find '" + args.find + "'"
            drive_file.show_all_children(args.find, None, debug)
        else:
            drive_file.show_all_children(None, args.find, debug)
    elif args.ls != None:
        if args_are_paths:
            if debug:
                print "# ls '" + args.ls + "'"
            drive_file.show_children(args.ls, None, debug)
        else:
            drive_file.show_children(None, args.ls, debug)
    elif args.stat != None:
        if args_are_paths:
            drive_file.show_metadata(args.stat, None, debug)
        else:
            drive_file.show_metadata(None, args.stat, debug)

    # Done with the work

    if args.dump:
        print "dumping drive_file ..."
        print str(drive_file)
        print

    print
    print "# call_count: " + str(drive_file.call_count)

    test_stats.print_final_report()

if __name__ == '__main__':
    main()
