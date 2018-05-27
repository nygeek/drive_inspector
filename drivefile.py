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
from apiclient import errors

from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage

# Roadmap
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
# [+] 2018-05-06 Make a flag to modify the --find operation to show
#     either just the directories or all of the files.
#         2018-05-12 Added the --all flag to do this.
# [ ] 2018-05-06 Make a render function that accepts a list of FileIDs
#     and a list of attributes and return a 2D array of values
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
# [+] 2018-05-11 Add an interactive main loop, let's call it driveshell.
#         2018-05-20 - done
# [+] 2018-05-12 list_children never relies on the cache.  Maybe I can
#     do something clever here?
#         2018-05-12 Augmented list_children to look in the cache first.
# [+] 2018-05-12 Add flags to remove the existing cache and to skip
#     writing the cache when done.
#         2018-05-13 --nocache and --Z flags added.  --Z omits writing the
#         cache, but does not actually remove the file.
# [+] 2018-05-20 Move the debug flag out of the signature of the
#     various methods and into an attribute of the DriveFile object.
# [+] 2018-05-23 Add a dirty flag to file_data so that I do not have
#     to rewrite the cache file if the cache is unchanged.
# [+] 2018-05-22 Create a one or more helper functions to manipulate
#     paths.  The hacky stuff for dealing with 'cd foo' when in '/'
#     is just plain stupid.  The result is ugly repeated code.  Ugh.
#         2018-05-24 canonicalize_path() is a helper function in drivefile

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
    # at ~/.credentials/credentials.json
    scopes = 'https://www.googleapis.com/auth/drive.metadata.readonly'
    client_secret_file = '~/.credentials/.client_secret.json'

    home_dir = os.path.expanduser('~')
    credential_dir = os.path.join(home_dir, '.credentials')
    if not os.path.exists(credential_dir):
        os.makedirs(credential_dir)
    credential_path = os.path.join(credential_dir,
                                   'credentials.json')

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


def canonicalize_path(cwd, path, debug):
    """Given a path composed by concatenating two or more parts,
       clean up and canonicalize the path."""
    #   // => /
    #   foo/bar/../whatever => foo/whatever [done]
    #   foo/bar/./whatever => foo/whatever [done]
    #   /foo/bar => /foo/bar [done]
    #   foo/bar => cwd/foo/bar [done]
    #   <empty_path> => cwd [done]
    cwd_parts = cwd.split('/')
    path_parts = path.split('/')

    new = path_parts if path and path[0] == '/' else cwd_parts + path_parts

    if debug:
        print "# canonicalize_path(cwd: '" + cwd \
            + "', path: '" + path + "')"
        print "#   cwd_parts: " + str(cwd_parts)
        print "#   path_parts: " + str(path_parts)
        print "# new: '" + str(new) + "'"

    # Now we will do some canonicalization ...
    while '..' in new:
        where = new.index('..')
        new = new[:where-1] + new[where+1:] if where >= 2 else new[where+1:]
    while '.' in new:
        where = new.index('.')
        new = new[:where] + new[where+1:] if where >= 1 else new[where+1:]
    # Get rid of trailing slashes
    while new and new[-1] == "":
        new = new[:-1]
    # Get rid of double slashes (an empty string in the middle of new)
    while '' in new[1:-1]:
        where = new[1:-1].index('')
        new = new[:where+1] + new[where+2:]
    # Make sure it's not empty
    if new and new[0] != '':
        new.insert(0, "")
    new_path = '/'.join(new)
    if not new_path:
        new_path = '/'
    if debug:
        print "# new: '" + str(new) + "'"
        print "new_path: '" + new_path + "'"
    return new_path


FOLDERMIMETYPE = 'application/vnd.google-apps.folder'
STANDARD_FIELDS = "id, name, parents, mimeType, owners, trashed, "
STANDARD_FIELDS += "modifiedTime, createdTime, ownedByMe, shared"
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
        self.cache_path = "./.filedata-cache.json"
        self.debug = debug
        self.service = discovery.build(
            'drive',
            'v3',
            http=get_credentials().authorize(httplib2.Http())
            )

    def get(self, file_id):
        """Get the metadata for file_id.
           Returns: metadata structure
        """
        if self.debug:
            print "# get(file_id: " + file_id + ")"
        # if 'metadata' in self.file_data and \
        #     file_id not in self.file_data['metadata']:
        if file_id not in self.file_data['metadata']:
            if self.debug:
                print "# calling Google ..."
            t_start = time.time()
            file_metadata = \
                self.service.files().get(
                    fileId=file_id,
                    fields=STANDARD_FIELDS
                    ).execute()
            self.call_count['get'] += 1
            self.file_data['time'][file_id] = time.time() - t_start
            self.register_metadata([file_metadata])
            if file_id == "root":
                # very special case!
                self.file_data['metadata'][file_id] = file_metadata
                self.file_data['ref_count'][file_id] = 1
                self.get_path(file_id)
        return self.file_data['metadata'][file_id]

    def resolve_path(self, path):
        """Given a path, find and return the FileID matching the
           terminal node.
           Returns: FileID
        """
        if self.debug:
            print "# resolve_path(" + str(path) + ")"
        # for now the path should begin with /
        if path and path[0] != "/":
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
        if self.debug:
            print "path_components: " + str(path_components)
        node = self.get("root")['id']
        for component in path_components:
            # if the component is a '.' (current directory) then skip it
            if component != ".":
                node = self.get_named_child(node, component)
                if node in ["<not_found>", "<error"]:
                    print "# resolve_path(" + path + ") => not found."
                    return node
                if self.debug:
                    print "# " + component + " => (" + node + ")"
        return node

    def get_named_child(self, file_id, component):
        """ Given a file_id (folder) and a component name, find the
            matching child, if it exists.
            Returns: FileID
            Returns: <not_found> if there is no child by that name
        """
        if self.debug:
            print "# get_named_child(file_id:" \
                + str(file_id) + ", " + component + ")"
        children = self.list_children(file_id)
        for child_id in children:
            if self.debug:
                print "# get_named_child: child_id:" + child_id + ")"
            if child_id in self.file_data['metadata']:
                child_name = self.file_data['metadata'][child_id]['name']
            else:
                child_name = self.get(child_id)['name']
            if self.debug:
                print "# get_named_child: child name:" \
                        + str(child_name) + ")"
            if child_name == component:
                # found it!
                return child_id
        return "<not_found>"

    def is_folder(self, file_id):
        """Test whether file_id is a folder.
           Returns: Boolean
        """
        if self.debug:
            print "# is_folder(" + file_id + ")"
        file_metadata = self.get(file_id)
        result = file_metadata['mimeType'] == FOLDERMIMETYPE \
                 and ("fileExtension" not in file_metadata)
        if self.debug:
            print "#   => " + str(result)
        return result

    def list_subfolders(self, file_id):
        """Get the folders that have a given file_id as a parent.
           Returns: array of FileID
        """
        if self.debug:
            print "# list_subfolders(file_id: " + file_id + ")"
        children = self.list_children(file_id)
        # now filter out the non-folders and only return the FileIDs
        # of folders
        subfolders = []
        i = 0
        for item_id in children:
            if self.debug:
                print "# i: " + str(i) + " item_id: (" + str(item_id) + ")"
            if self.is_folder(item_id):
                subfolders.append(item_id)
                i += 1
        return subfolders

    def list_children(self, file_id):
        """Get the children of file_id.
           Returns: array of FileID
        """
        if self.debug:
            print "# list_children(file_id: " + file_id + ")"
        results = []
        # Are there children of file_id in the cache?
        for item_id in self.file_data['metadata']:
            metadata = self.file_data['metadata'][item_id]
            if 'parents' in metadata and file_id in metadata['parents']:
                results.append(item_id)
        if not results:
            query = "'" + file_id + "' in parents"
            fields = "nextPageToken, "
            fields += "files(" + STANDARD_FIELDS + ")"
            if self.debug:
                print "# query: " + query
                print "# fields: " + fields
            # No children from the cache - search Google Drive
            npt = "start"
            children = []
            while npt:
                if self.debug:
                    print "# list_children: npt: (" + npt + ")"
                try:
                    if npt == "start":
                        response = self.service.files().list(
                            q=query,
                            fields=fields
                            ).execute()
                    else:
                        response = self.service.files().list(
                            pageToken=npt,
                            q=query,
                            fields=fields
                            ).execute()
                    self.call_count['list_children'] += 1
                    npt = response.get('nextPageToken')
                    children += response.get('files', [])
                except errors.HttpError as error:
                    print "HttpError: " + str(error)
                    response = "not found."
                    npt = None
            if children:
                results = self.register_metadata(children)
        if self.debug:
            print "# list_children results: " + str(len(results))
        return results

    def register_metadata(self, metadata_array):
        """Accept an array of raw metadata and register them in
           self.file_data.
           Returns: array of FileID
        """
        if self.debug:
            print "# register_metadata(len: " \
                    + str(len(metadata_array)) + ")"
        # Now comb through and put everything in file_data.
        i = 0
        results = []
        for node in metadata_array:
            item_id = node['id']
            item_name = node['name']
            if self.debug:
                print "# register_metadata: i: " + str(i) \
                      + " (" + item_id + ") '" + item_name + "'"
            if item_id not in self.file_data['metadata']:
                if self.debug:
                    print "# register_metadata: item_id: " + item_id
                self.file_data['metadata'][item_id] = node
                self.file_data['dirty'] = True
                self.file_data['ref_count'][item_id] = 1
                self.get_path(item_id)
            results.append(item_id)
            i += 1
        if self.debug:
            print "# register_metadata results: " + str(len(results))
        return results

    def get_parents(self, file_id):
        """Given a file_id, get the list of parents.
           Returns: array of FileID
        """
        if self.debug:
            print "# get_parents(" + file_id + ")"
        # check the cache
        if file_id not in self.file_data['metadata']:
            _ = self.get(file_id)
        if 'parents' in _:
            results = _['parents']
        else:
            results = ['<none>']
        if self.debug:
            print "# get_parents: " + str(results)
        return results

    def get_path(self, file_id):
        """Given a file_id, construct the path back to root.
           Returns: string
        """
        if self.debug:
            print "# get_path(" + file_id + ")"
        if file_id in self.file_data['path']:
            return self.file_data['path'][file_id]
        else:
            if file_id not in self.file_data['metadata']:
                # Oops ... we are not in the file data either
                _ = self.get(file_id)
            file_name = self.file_data['metadata'][file_id]['name']
            if 'parents' not in self.file_data['metadata'][file_id]:
                parent = 'root'
            else:
                parent = self.file_data['metadata'][file_id]['parents'][0]
            if file_name == "My Drive":
                self.file_data['path'][file_id] = "/"
                self.file_data['dirty'] = True
                return ""
            self.file_data['path'][file_id] = \
                self.get_path(parent) + file_name
            if self.is_folder(file_id):
                self.file_data['path'][file_id] += "/"
            return self.file_data['path'][file_id]

    def show_metadata(self, path, file_id):
        """ Display the metadata for a node."""
        if path is not None:
            if self.debug:
                print "# show_metadata(path: '" + path + "')"
            file_id = self.resolve_path(path)
        else:
            if self.debug:
                print "# show_metadata(file_id: (" + file_id + "))"
        if file_id == "<not-found>":
            print "'" + path + " not found."
        else:
            print pretty_json(self.get(file_id))

    def show_children(self, path, file_id):
        """ Display the names of the children of a node.
            This is the core engine of the --ls function.
        """
        if path is not None:
            if self.debug:
                print "# show_children(path: '" + str(path) + "')"
            file_id = self.resolve_path(path)
        else:
            if self.debug:
                print "# show_children(file_id: (" + str(file_id) + "))"
        children = self.list_children(file_id)
        if self.debug:
            print "# show_children: children: " + str(children)
        for child in children:
            if self.debug:
                print "# child: " + str(child)
            child_name = self.get(child)['name']
            if self.is_folder(child):
                child_name += "/"
            print child_name

    def show_all_children(
            self, path, file_id, show_all=False):
        """ Display all child directories of a node
            This is the core engine of the --find function.
            One of path or file_id should be set, the other None.
            If show_all is True, then display all files.  If False
            then show only the folder structure.
        """
        if path is not None:
            if self.debug:
                print "# show_all_children(path: '" + path + "')"
                print "#    show_all: " + str(show_all)
            file_id = self.resolve_path(path)
        else:
            if self.debug:
                print "# show_all_children(file_id: (" + file_id + "))"
                print "#    show_all: " + str(show_all)
        queue = self.list_children(file_id)
        num_files = 0
        num_folders = 0
        while queue:
            file_id = queue.pop(0)
            file_metadata = self.get(file_id)
            file_name = file_metadata['name']
            num_files += 1
            if self.debug:
                print "# file_id: (" + file_id + ") '" \
                      + file_name + "'"
            if self.is_folder(file_id):
                num_folders += 1
                children = self.list_children(file_id)
                queue += children
                print self.get_path(file_id)
            elif show_all:
                print self.get_path(file_id)
        print "# num_folders: " + str(num_folders)
        print "# num_files: " + str(num_files)

    def set_cwd(self, path):
        """Set the current working directory string
           Returns: nothing
        """
        if self.debug:
            print "# set_cwd: " + path
        new_path = canonicalize_path(
            self.file_data['cwd'],
            path,
            self.debug)
        self.file_data['cwd'] = new_path
        self.file_data['dirty'] = True

    def get_cwd(self):
        """Return the value of the current working directory
           Returns: string
        """
        if self.debug:
            print "# get_cwd: " + self.file_data['cwd']
        return self.file_data['cwd']

    def load_cache(self):
        """Load the cache from stable storage."""
        if self.debug:
            print "# load_cache: " + str(self.cache_path)
        try:
            cache_file = open(self.cache_path, "r")
            self.file_data = json.load(cache_file)
            for file_id in self.file_data['metadata'].keys():
                self.file_data['ref_count'][file_id] = 0
            print "# Loaded " + str(len(self.file_data['metadata'])) \
                + " cached nodes."
            self.file_data['dirty'] = False
        except IOError as error:
            print "# Starting with empty cache. IOError: " + str(error)
            self.init_metadata_cache()

    def init_metadata_cache(self):
        """Initialize the self.file_data cache['metadata']."""
        if self.debug:
            print "# init_metadata_cache()"
        self.file_data['metadata'] = {}
        self.file_data['metadata']['<none>'] = {}
        self.file_data['dirty'] = False

    def dump_cache(self):
        """Write the cache out to a file. """
        if self.file_data['dirty']:
            try:
                cache_file = open(self.cache_path, "w")
                json.dump(
                    self.file_data,
                    cache_file, indent=3,
                    separators=(',', ': ')
                )
                print "# Wrote " \
                    + str(len(self.file_data['metadata'])) \
                    + " nodes to " + self.cache_path + "."
            except IOError as error:
                print "IOError: " + str(error)
        else:
            print "Cache clean, not rewritten."

    def set_debug(self, debug):
        """Set the debug flag."""
        if self.debug:
            print "set_debug(" + str(debug) + ")"
        self.debug = debug
        if self.debug:
            print "set_debug: debug:" + str(self.debug)
        return self.debug

    def get_debug(self):
        """Return the debug flag."""
        if self.debug:
            print "set_debug: debug:" + str(self.debug)
        return self.debug

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
                    result += "time: " \
                        + str(self.file_data['time'][file_id]) + "\n"
                result += "path: " \
                    + self.file_data['path'][file_id] + "\n"
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
        print "# program_name: " + self.program_name
        print "# iso_time_stamp: " + self.iso_time_stamp

    def print_final_report(self):
        """Print the final report form the test run."""
        cpu_time_1 = psutil.cpu_times()
        print "# " + self.program_name + ": User time: " +\
            str(cpu_time_1[0] - self.cpu_time_0[0]) + " S"
        print "# " + self.program_name + ": System time: " +\
            str(cpu_time_1[2] - self.cpu_time_0[2]) + " S"


# Helper functions - framework for the main() function
def setup_parser():
    """Set up the arguments parser.
       Returns: parser
    """
    parser = argparse.ArgumentParser(
        description=\
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
    return parser


def handle_stat(drive_file, arg, args_are_paths, show_all):
    """Handle the --stat operation."""
    if drive_file.debug:
        print "# handle_stat("
        print "#    arg: " +  str(arg)
        print "#    args_are_paths: " +  str(args_are_paths)
        print "#    show_all: " +  str(show_all)
    if arg != None:
        if args_are_paths:
            path = canonicalize_path(
                drive_file.get_cwd(),
                arg,
                drive_file.debug
            )
            drive_file.show_metadata(path, None)
        else:
            drive_file.show_metadata(None, arg)
    return True


def handle_find(drive_file, arg, args_are_paths, show_all):
    """Handle the --find operation."""
    if drive_file.debug:
        print "# handle_find("
        print "#    arg: " +  str(arg)
        print "#    args_are_paths: " +  str(args_are_paths)
        print "#    show_all: " +  str(show_all)
    if arg is not None:
        if args_are_paths:
            path = canonicalize_path(
                drive_file.get_cwd(),
                arg,
                drive_file.debug
            )
            drive_file.show_all_children(path, None, show_all)
        else:
            drive_file.show_all_children(None, arg, show_all)
    return True


def handle_ls(drive_file, arg, args_are_paths, show_all):
    """Handle the --ls operation."""
    if drive_file.debug:
        print "# handle_ls("
        print "#    arg: " +  str(arg)
        print "#    args_are_paths: " +  str(args_are_paths)
        print "#    show_all: " + str(show_all)
    if arg is not None:
        if args_are_paths:
            # truncate path if it ends in '/'
            path = canonicalize_path(
                drive_file.get_cwd(),
                arg,
                drive_file.debug
            )
            drive_file.show_children(path, None)
        else:
            drive_file.show_children(None, arg)
    return True


def do_work():
    """Parse arguments and handle them."""

    parser = setup_parser()
    args = parser.parse_args()

    args_are_paths = True
    if args.f:
        args_are_paths = False

    use_cache = True
    if args.nocache:
        use_cache = False

    # Do the work ...

    if args.DEBUG:
        print "args: " + str(args)
        drive_file = DriveFile(True)
    else:
        drive_file = DriveFile(False)

    if use_cache:
        drive_file.load_cache()
    else:
        print "# Starting with empty cache."
        drive_file.init_metadata_cache()

    if args.cd != None:
        drive_file.set_cwd(args.cd)
        print "pwd: " + drive_file.get_cwd()

    handle_find(drive_file, args.find, args_are_paths, args.all)

    handle_stat(drive_file, args.stat, args_are_paths, args.all)

    handle_ls(drive_file, args.ls, args_are_paths, args.all)

    # Done with the work

    if args.dump:
        print "dumping drive_file ..."
        print str(drive_file)
        print

    print "# call_count: "
    print "#    get: " + \
            str(drive_file.call_count['get'])
    print "#    list_children: " + \
            str(drive_file.call_count['list_children'])

    if args.Z is None:
        drive_file.dump_cache()
    else:
        print "# not writing cache."


def main():
    """Test code and basic CLI functionality engine."""

    test_stats = TestStats()
    test_stats.print_startup()

    do_work()

    test_stats.print_final_report()


if __name__ == '__main__':
    main()
