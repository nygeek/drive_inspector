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

#
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
# [+] 2018-04-29 Add a local store for state.  Needed for the
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
# [ ] 2018-05-06 Make a render function that accepts a list of FileIDs
#     and a list of attributes and return a 2D array of values
# [+] 2018-05-06 Make a flag to modify the --find operation to show
#     either just the directories or all of the files.
#         2018-05-12 Added the --all flag to do this.
# [+] 2018-05-07 Handle relative paths
#         2018-05-09 - done
# [+] 2018-05-07 Implement a PWD / CWD and CD function
#         2018-05-09 - done
# [+] 2018-05-07 Consolidate all of the FileID cache data so that
#     we only need a single structure (self.file_data{}).  It would
#     have four things under each FileID: metadata, path, time, ref_count
#         2018-05-08 - done.
# [+] 2018-05-07 Rewrite get_subfolders() to call get_children() and
#     just filter out the non-children.
#         2018-05-08 - done.
# [ ] 2018-05-11 Add an interactive main loop, let's call it drive-shell.
# [+] 2018-05-12 list_children never relies on the cache.  Maybe I can
#     do something clever here?
#         2018-05-12 Augmented list_children to look in the cache first.
# [+] 2018-05-12 Add flags to remove the existing cache and to skip
#     writing the cache when done.
#         2018-05-13 --nocache and --Z flags added.  --Z omits writing the
#         cache, but does not actually remove the file.

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
STRMODE = 'full'

class DriveFile(object):
    """Class to provide cached access to Google Drive object metadata."""

    def __init__(self, debug):
        self.file_data = {}
        self.file_data['path'] = {}
        self.file_data['path']['<none>'] = ""
        self.file_data['path']['root'] = "/"
        self.file_data['time'] = {}
        self.file_data['time']['<none>'] = 0
        self.file_data['ref_count'] = {}
        self.file_data['ref_count']['<none>'] = 0
        self.call_count = {}
        self.call_count['get'] = 0
        self.call_count['list_children'] = 0
        self.file_data['cwd'] = '/'
        self.cache_path = "./filedata-cache.json"
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
        if 'metadata' in self.file_data and \
            file_id not in self.file_data['metadata']:
            if debug:
                print "# calling Google ..." 
            t_start = time.time()
            file_metadata = \
                self.service.files().get(
                    fileId=file_id,
                    fields=STANDARD_FIELDS
                    ).execute()
            self.call_count['get'] += 1
            self.file_data['time'][file_id] = time.time() - t_start
            self.file_data['metadata'][file_id] = file_metadata
        if file_id not in self.file_data['ref_count']:
            self.file_data['ref_count'][file_id] = 0
        self.file_data['ref_count'][file_id] += 1
        _ = self.get_path(file_id, debug)
        return self.file_data['metadata'][file_id]

    def resolve_path(self, path, debug=False):
        """Given a path, find and return the FileID matching the
           terminal node.
           Returns: FileID
        """
        if debug:
            print "# resolve_path(" + str(path) + ")"
        # for now the path should begin with /
        if path[0] != "/":
            # relative path ... combine with cwd ...
            path = self.get_cwd() + "/" + path
        if path in self.file_data['path'].values():
            for file_id, dict_path in self.file_data['path'].iteritems():
                if dict_path == path:
                    return file_id
                # better not ever get here!
        path_components = path.split("/")
        # this pop drops the leading empty string
        path_components.pop(0)
        if debug:
            print "path_components: " + str(path_components)
        node = self.get("root", debug)['id']
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
            print "# get_named_child(file_id:" + \
                file_id + ", " + component + ")"
        children = self.list_children(file_id, debug)
        for child_id in children:
            if debug:
                print "# get_named_child(child_id:" + child_id + ")"
            if child_id not in self.file_data['metadata']:
                _ = self.get(child_id, debug)
            if self.file_data['metadata'][child_id]['name'] == component:
                # found it!
                return child_id
        return "<not_found>"

    def is_folder(self, file_id, debug=False):
        """Test whether file_id is a folder.
           Returns: Boolean
        """
        if debug:
            print "# is_folder(" + file_id + ")"
        file_metadata = self.get(file_id, debug)
        result = file_metadata['mimeType'] == FOLDERMIMETYPE and \
                 ("fileExtension" not in file_metadata)
        if debug:
            print "#   => " + str(result)
        return result

    def list_subfolders(self, file_id, debug=False):
        """Get the folders that have a given file_id as a parent.
           Returns: array of FileID
        """
        if debug:
            print "# list_subfolders(file_id: " + file_id + ")"
        children = self.list_children(file_id, debug)
        # now filter out the non-folders and only return the FileIDs
        # of folders
        subfolders = []
        i = 0
        for item_id in children:
            if debug:
                print "# i: " + str(i) + " item_id: (" + str(item_id) + ")"
            if self.is_folder(item_id, debug):
                subfolders.append(item_id)
                i += 1
        return subfolders

    def list_children(self, file_id, debug=False):
        """Get the children of file_id.
           Returns: array of FileID
        """
        if debug:
            print "# list_children(file_id: " + file_id + ")"

        results = []

        # Are there children of file_id in the cache?
        for item_id in self.file_data['metadata']:
            if debug:
                print "# list_children: check cache: " + str(item_id)
            metadata = self.file_data['metadata'][item_id]
            if debug:
                print "# list_children: check cache: " + str(metadata)
            if 'parents' in metadata and file_id in metadata['parents']:
                if debug:
                    print "#   found cached child: " + item_id
                results.append(item_id)

        if len(results) == 0:
            query = "'" + file_id + "' in parents"
            fields = "nextPageToken, "
            fields += "files(" + STANDARD_FIELDS + ")"
            if debug:
                print "# query: " + query
                print "# fields: " + fields
            # No children from the cache - search Google Drive
            npt = "start"
            while npt:
                if debug:
                    print "# list_children: npt: (" + npt + ")"
                if npt == "start":
                    _ = self.service.files().list(
                        q=query,
                        fields=fields
                        ).execute()
                    self.call_count['list_children'] += 1
                    children = _.get('files', [])
                    npt = _.get('nextPageToken')
                else:
                    _ = self.service.files().list(
                        pageToken=npt,
                        q=query,
                        fields=fields
                        ).execute()
                    self.call_count['list_children'] += 1
                    children += _.get('files', [])
                    npt = _.get('nextPageToken')
                # Now comb through and put everything in file_data.
                i = 0
                results = []
                for file_item in children:
                    item_id = file_item['id']
                    item_name = file_item['name']
                    if debug:
                        print "# list_children: i: " + str(i) + \
                                " (" + item_id + ") '" + item_name + "'"
                    if item_id not in self.file_data['metadata']:
                        if debug:
                            print "# list_children: item_id: " + item_id
                        self.file_data['metadata'][item_id] = file_item
                        self.file_data['ref_count'][item_id] = 1
                        _ = self.get_path(item_id, debug)
                    results.append(item_id)
                    i += 1
        if debug:
            print "# list_children results: " + str(results)
        return results

    def get_parents(self, file_id, debug=False):
        """Given a file_id, get the list of parents.
           Returns: array of FileID
        """
        if debug:
            print "# get_parents(" + file_id + ")"
        # check the cache
        if file_id not in self.file_data['metadata']:
            _ = self.get(file_id, debug)
        if 'parents' in _:
            results = _['parents']
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
        if file_id in self.file_data['path']:
            return self.file_data['path'][file_id]
        else:
            if file_id not in self.file_data['metadata']:
                # Oops ... we are not in the file data either
                _ = self.get(file_id, debug)
            file_name = self.file_data['metadata'][file_id]['name']
            if 'parents' not in self.file_data['metadata'][file_id]:
                parent = 'root'
            else:
                parent = self.file_data['metadata'][file_id]['parents'][0]
            if file_name == "My Drive":
                self.file_data['path'][file_id] = "/"
                return ""
            self.file_data['path'][file_id] = \
                self.get_path(parent) + file_name
            if self.is_folder(file_id):
                self.file_data['path'][file_id] += "/"
            return self.file_data['path'][file_id]

    def show_metadata(self, path, file_id, debug=False):
        """ Display the metadata for a node."""
        if path is not None:
            if debug:
                print "# show_metadata(path: '" + path + "')"
            file_id = self.resolve_path(path, debug)
        else:
            if debug:
                print "# show_metadata(file_id: (" + file_id + "))"
        print pretty_json(self.get(file_id, debug))

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
            child_name = self.get(child, debug)['name']
            if self.is_folder(child):
                child_name += "/"
            print child_name

    def show_all_children(
            self,
            path,
            file_id,
            show_all=False,
            debug=False
            ):
        """ Display all child directories of a node
            This is the core engine of the --find function.
            One of path or file_id should be set, the other None.
            If show_all is True, then display all files.  If False
            then show only the folder structure.
        """
        if path is not None:
            if debug:
                print "# show_all_children(path: '" + path + "')"
                print "#    show_all: " + str(show_all)
            file_id = self.resolve_path(path, debug)
        else:
            if debug:
                print "# show_all_children(file_id: (" + file_id + "))"
                print "#    show_all: " + str(show_all)
        queue = self.list_children(file_id, debug)
        num_files = 0
        num_folders = 0
        while queue:
            file_id = queue.pop(0)
            file_metadata = self.get(file_id, debug)
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
                # print "[" + str(num_folders) + "] " + \
                #         self.get_path(file_id) + \
                #         "(" + str(len(children)) + ")"
                print self.get_path(file_id)
            elif show_all:
                print self.get_path(file_id)
        print "# num_folders: " + str(num_folders)
        print "# num_files: " + str(num_files)

    def set_cwd(self, path, debug=False):
        """Set the current working directory string
           Returns: nothing
        """
        if debug:
            print "# set_cwd: " + path
        self.file_data['cwd'] = path

    def get_cwd(self, debug=False):
        """Return the value of the current working directory
           Returns: string
        """
        if debug:
            print "# get_cwd: " + self.cwd
        return self.file_data['cwd']

    def load_cache(self, debug):
        """Load the cache from stable storage."""
        if debug:
            print "# load_cache: " + str(self.cache_path)
        try:
            f = open(self.cache_path, "r")
            self.file_data = json.load(f)
            for file_id in self.file_data['metadata'].keys():
                self.file_data['ref_count'][file_id] = 0
            print "# Loaded " + str(len(self.file_data['metadata'])) \
                + " cached file metadata."
            # for file_id in self.file_data['metadata'].keys():
            #     self.get_path(file_id, debug)
        except IOError as e:
            print "# Starting with empty cache."
            self.init_metadata_cache(debug)

    def init_metadata_cache(self, debug):
        """Initialize the self.file_data cache['metadata']."""
        if debug:
            print "# init_metadata_cache()"
        self.file_data['metadata'] = {}
        self.file_data['metadata']['<none>'] = {}

    def dump_cache(self):
        """Write the cache out to a file. """
        try:
            f = open(self.cache_path, "w")
            json.dump(self.file_data, \
                f, indent=3, separators=(',', ': '))
            print "# Wrote " + str(len(self.file_data['metadata'])) + \
                    " file metadata to " + self.cache_path + "."
        except IOError as e:
            print "IOError: " + str(e)

    def __str__(self):
        if STRMODE == 'full':
            result = pretty_json(self.file_data)
        else:
            result = "cwd: " + self.cwd + "\n"
            for file_id in self.file_data['metadata']:
                result += "(" + file_id + "):\n"
                result += pretty_json(
                    self.file_data['metadata'][file_id]) + "\n"
                if file_id in self.file_data['time']:
                    result += "time: " + \
                        str(self.file_data['time'][file_id]) + "\n"
                result += "path: " + \
                    self.file_data['path'][file_id] + "\n"
                result += "refs: " + \
                    str(self.file_data['ref_count'][file_id]) + "\n"
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

    test_stats = TestStats()
    test_stats.print_startup()

    parser = argparse.ArgumentParser(description=\
        "Use the Google Drive API (REST v3) to get information " + \
        "about files to which you have access."\
        )
    parser.add_argument(
        '-a', '--all',
        action='store_const', const=True,
        help='(Modifier)  When running a find, show all files.'
        )
    parser.add_argument(
        '--cd',
        type=str,
        help='Change the working directory.'
        )
    parser.add_argument(
        '-d', '--dump',
        action='store_const', const=True,
        help='When done running, dump the DriveFile object'
        )
    parser.add_argument(
        # this modifier causes args_are_paths to be set False
        '-f',
        action='store_const', const=True,
        help='(Modifier)  Argument to stat, ls, find will be a FileID.'
        )
    parser.add_argument(
        '--find',
        type=str,
        help='Given a fileid, recursively traverse all subfolders.'
        )
    parser.add_argument(
        '--ls',
        type=str,
        help='Given a path, list the files contained in it.'
        )
    parser.add_argument(
        '-n', '--nocache',
        action='store_const', const=True,
        help='(Modifier)  When set, skip loading the cache.'
        )
    parser.add_argument(
        '--stat',
        type=str,
        help="Return the metadata for the node at the end of a path."
        )
    parser.add_argument(
        '-D', '--DEBUG',
        action='store_const', const=True,
        help='(Modifier) Turn debugging on.'
        )
    parser.add_argument(
        '-z', '--Z',
        action='store_const', const=True,
        help='(Modifier) Skip writing out the cache at the end.'
        )

    args = parser.parse_args()

    debug = False
    if args.DEBUG:
        debug = True
        print "args: " + str(args)

    args_are_paths = True
    if args.f:
        args_are_paths = False

    use_cache = True
    if args.nocache:
        use_cache = False

    # Do the work ...

    drive_file = DriveFile(debug)
    if use_cache:
        drive_file.load_cache(debug)
    else:
        print "# Starting with empty cache."
        drive_file.init_metadata_cache(debug)

    if args.cd != None:
        drive_file.set_cwd(args.cd, debug)
        print "pwd: " + drive_file.get_cwd(debug)

    show_all = False
    if args.find != None:
        if args.all:
            show_all = True
        if args_are_paths:
            if debug:
                print "# find '" + args.find + "'"
            drive_file.show_all_children(args.find, None, show_all, debug)
        else:
            drive_file.show_all_children(None, args.find, show_all, debug)
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
    print "# call_count: "
    print "#    get: " + \
            str(drive_file.call_count['get'])
    print "#    list_children: " + \
            str(drive_file.call_count['list_children'])

    if args.Z == None:
        drive_file.dump_cache()
    else:
        print "# not writing cache."

    test_stats.print_final_report()

if __name__ == '__main__':
    main()
