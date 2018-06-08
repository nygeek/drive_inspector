""" Implementation of the DriveInspector tools and utilities

Started 2018-04-20 by Marc Donner

Copyright (C) 2018 Marc Donner

This class and the test code in the main() function at the bottom
are written to provide me with the ability to construct a systematic
inventory of the files in my Google Drive.

"""

import argparse
import datetime
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
# [+] 2018-05-06 Make a render function that accepts a list of FileIDs
#     and a list of attributes and return a 2D array of values
#         2018-05-28 Created drivereport.py that does this.
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
# [+] 2018-06-02 Build a list method that uses the API list function but
#     does it without filtering by parent.  This will replicate the
#     experimental stuff I did early with the dls.py prototype and help
#     me find and understand the things I found with odd parents.
#         2018-06-02 --showall command line option added.  Relevant
#         functionality added to handlers, parser, and DriveFile class
# [+] 2018-06-02 Make the path construction machinery smarter.  In
#     particular, if there is no parent file and the owner is not me
#     then infer a parent folder that is the owner's "home directory"
#     ... we can not see their folder structure, so we will simply say
#     something like "~foo@bar.org/.../" to suggest the appropriate
#     root.
#         2018-6-03 The new path magic is now working with shared files.
# [+] 2018-06-03 Establish an output file so that the reports and
#     so forth can be put in specific files -o --output for drivefile
#     and output <path> for driveshell.
#         2018-06-05 added output management stuff to both drivefile
#         and driveshell.
# [X] 2018-06-03 Build a table of handlers in drivefile like the one
#     in driveshell to streamline (or eliminate) the do_work() helper
#     function.
# [ ] 2018-06-06 Review the drive inspector classes and see if I can
#     design a coherent structure of inheritance that unifies them
#     all.

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
        # 1
        self.file_data = {}
        self.file_data['path'] = {}
        self.file_data['path']['<none>'] = ""
        self.file_data['path']['root'] = "/"
        self.file_data['time'] = {}
        self.file_data['time']['<none>'] = 0
        self.file_data['ref_count'] = {}
        self.file_data['ref_count']['<none>'] = 0
        # 2
        self.call_count = {}
        self.call_count['get'] = 0
        self.call_count['list_children'] = 0
        self.call_count['list_all'] = 0
        self.call_count['list_modified'] = 0
        # 3
        self.file_data['cwd'] = '/'
        # 4
        self.cache = {}
        self.cache['path'] = "./.filedata-cache.json"
        self.cache['mtime'] = "?"
        self.debug = debug
        # 5
        self.set_output("stdout")
        # 6
        self.service = discovery.build(
            'drive',
            'v3',
            http=get_credentials().authorize(httplib2.Http())
            )

    def get_status(self):
        """Get status of DriveFile instance.
           Returns: List of String
        """
        if self.debug:
            print "# get_status()"
        result = []
        result.append("# ========== >>> STATUS ==========")
        result.append("# cache['path']: '" + str(self.cache['path']) + "'")
        result.append("# cache['mtime']: " + str(self.cache['mtime']))
        result.append("# cwd: '" + str(self.file_data['cwd']) + "'")
        result.append("# debug: " + str(self.debug))
        result.append("# output_path: '" + str(self.output_path) + "'")
        if 'metadata' in self.file_data:
            result.append("# cache size: " + \
                str(len(self.file_data['metadata'])) + " nodes")
        else:
            result.append("# cache size: 0")
        result.append(# path cache size: " + \
            str(len(self.file_data['path'])) + " paths")
        result.append("# ========== STATUS >>> ==========")
        return result

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
            self.__register_metadata([file_metadata])
            if file_id == "root":
                # very special case!
                self.file_data['metadata'][file_id] = file_metadata
                self.file_data['ref_count'][file_id] = 1
                self.get_path(file_id)
        return self.file_data['metadata'][file_id]

    def get_path(self, file_id):
        """Given a file_id, construct the path back to root.
           Returns: string
        """
        if self.debug:
            print "# get_path(" + file_id + ")"

        if file_id in self.file_data['path']:
            return self.file_data['path'][file_id]

        # If we got here, then the path is not cached
        if file_id not in self.file_data['metadata']:
            # file_id is not in the cache either
            metadata = self.get(file_id)
        else:
            metadata = self.file_data['metadata'][file_id]
        # We now have file in the variable metadata

        file_name = metadata['name']

        if 'parents' not in metadata:
            # If there is no parent AND the file is not owned by
            # me, then create a synthetic root for it.
            if 'ownedByMe' in metadata \
                   and not metadata['ownedByMe']:
                parent = "unknown/"
                if 'owners' in metadata:
                    parent = \
                        '~' \
                        + metadata['owners'][0]['emailAddress'] + \
                        '/.../'
                # Note that we're using the parent path as the fake
                # FileID for the parent's root.
                self.file_data['path'][parent] = parent
            else:
                parent = 'root'
        else:
            parent = metadata['parents'][0]

        # when we get here parent is either a real FileID or the
        # thing we use to refer to the My Drive of another user

        if file_name == "My Drive":
            self.file_data['path'][file_id] = "/"
            self.file_data['dirty'] = True
            return ""
        new_path = self.get_path(parent) + file_name
        self.file_data['path'][file_id] = new_path + '/' \
            if self.__is_folder(file_id) else new_path
        return self.file_data['path'][file_id]

    def __register_metadata(self, metadata_array):
        """Accept an array of raw metadata and register them in
           self.file_data.
           Returns: array of FileID
        """
        if self.debug:
            print "# __register_metadata(len: " \
                    + str(len(metadata_array)) + ")"
        # Now comb through and put everything in file_data.
        i = 0
        results = []
        for node in metadata_array:
            item_id = node['id']
            item_name = node['name']
            if self.debug:
                print "# __register_metadata: i: " + str(i) \
                      + " (" + item_id + ") '" + item_name + "'"
            if item_id not in self.file_data['metadata']:
                if self.debug:
                    print "# __register_metadata: item_id: " + item_id
                self.file_data['metadata'][item_id] = node
                self.file_data['dirty'] = True
                self.file_data['ref_count'][item_id] = 1
                self.get_path(item_id)
            results.append(item_id)
            i += 1
        if self.debug:
            print "# __register_metadata results: " + str(len(results))
        return results

    def df_print(self, line):
        """Internal print function, just for output."""
        self.output_file.write(line)

    def set_output(self, path):
        """Assign an output file path."""
        if self.debug:
            print "# set_output(" + str(path) + ")"
        self.output_path = path
        try:
            if path == 'stdout':
                self.output_file = sys.stdout
            else:
                self.output_file = open(self.output_path, "w")
            print "# writing output to: " + str(self.output_path)
        except IOError as error:
            print "# Can not open" + self.output_path + "."
            print "#    IOError: " + str(error)
            self.output_file = sys.stdout
            self.output_path = 'stdout'

    def get_field_list(self):
        """Report a list of available fields.
           Returns a list of strings.
        """
        if self.debug:
            print "get_field_list()"
        return STANDARD_FIELDS.split(", ")

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
                node = self.__get_named_child(node, component)
                if node in ["<not_found>", "<error"]:
                    print "# resolve_path(" + path + ") => not found."
                    return node
                if self.debug:
                    print "# " + component + " => (" + node + ")"
        return node

    def __get_named_child(self, file_id, component):
        """ Given a file_id (folder) and a component name, find the
            matching child, if it exists.
            Returns: FileID
            Returns: <not_found> if there is no child by that name
        """
        if self.debug:
            print "# __get_named_child(file_id:" \
                + str(file_id) + ", " + component + ")"
        children = self.list_children(file_id)
        for child_id in children:
            if self.debug:
                print "# __get_named_child: child_id:" + child_id + ")"
            if child_id in self.file_data['metadata']:
                child_name = self.file_data['metadata'][child_id]['name']
            else:
                child_name = self.get(child_id)['name']
            if self.debug:
                print "# __get_named_child: child name:" \
                        + str(child_name) + ")"
            if child_name == component:
                # found it!
                return child_id
        return "<not_found>"

    def __is_folder(self, file_id):
        """Test whether file_id is a folder.
           Returns: Boolean
        """
        if self.debug:
            print "# __is_folder(" + file_id + ")"
        file_metadata = self.get(file_id)
        result = file_metadata['mimeType'] == FOLDERMIMETYPE \
                 and ("fileExtension" not in file_metadata)
        if self.debug:
            print "#   => " + str(result)
        return result

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
                results = self.__register_metadata(children)
        if self.debug:
            print "# list_children results: " + str(len(results))
        return results

    def list_all(self):
        """Get all of the files to which I have access.
           Returns: array of FileID
        """
        if self.debug:
            print "# list_all()"
        results = []
        fields = "nextPageToken, "
        fields += "files(" + STANDARD_FIELDS + ")"
        if self.debug:
            print "# fields: " + fields
        npt = "start"
        file_list = []
        while npt:
            if self.debug:
                print "# list_all: npt: (" + npt + ")"
            try:
                if npt == "start":
                    response = self.service.files().list(
                        fields=fields
                        ).execute()
                else:
                    response = self.service.files().list(
                        pageToken=npt,
                        fields=fields
                        ).execute()
                self.call_count['list_all'] += 1
                npt = response.get('nextPageToken')
                file_list += response.get('files', [])
            except errors.HttpError as error:
                print "HttpError: " + str(error)
                response = "not found."
                npt = None
        if file_list:
            results = self.__register_metadata(file_list)
        if self.debug:
            print "# list_all results: " + str(len(results))
        return results

    def list_newer(self, date):
        """Find nodes that are modified more recently that
           the provided date.
           Returns: List of FileID
        """
        if self.debug:
            print "# list_newer(date: " + str(date) + ")"
        newer_list = []
        npt = "start"
        # modifiedTime > '2012-06-04T12:00:00'
        query = "'modifiedTime < '" + str(date) + "'"
        fields = "nextPageToken, "
        fields += "files(" + STANDARD_FIELDS + ")"
        while npt:
            if self.debug:
                print "# list_newer: npt: (" + npt + ")"
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
                self.call_count['list_newer'] += 1
                npt = response.get('nextPageToken')
                newer_list += response.get('files', [])
            except errors.HttpError as error:
                print "HttpError: " + str(error)
                response = "not found."
                npt = None
        if newer_list:
            results = self.__register_metadata(newer_list)
        if self.debug:
            print "# list_newer results: " + str(len(results))
        return results


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
            self.df_print("'" + path + " not found.\n")
        else:
            self.df_print(pretty_json(self.get(file_id)))

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
            if self.__is_folder(child):
                child_name += "/"
            self.df_print(child_name + '\n')

    def list_all_children(self, file_id, show_all=False):
        """Return the list of FileIDs beneath a given node.
           Return: list of FileID
        """
        if self.debug:
            print "# list_all_children(" \
                + "file_id: " + str(file_id) \
                + ", show_all: " + str(show_all) + ")"
        result = []
        queue = self.list_children(file_id)
        while queue:
            file_id = queue.pop(0)
            _ = self.get(file_id)
            if self.debug:
                print "# file_id: (" + file_id + ")"
            if self.__is_folder(file_id):
                children = self.list_children(file_id)
                queue += children
                result.append(file_id)
            elif show_all:
                result.append(file_id)
        return result

    def show_all_children(self, path, file_id, show_all=False):
        """ Display all child directories of a node
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

        children = self.list_all_children(file_id, show_all)

        num_files = 0
        num_folders = 0

        for child_id in children:
            metadata = self.get(child_id)
            child_name = metadata['name']
            num_files += 1
            if self.debug:
                print "# child_id: (" + child_id + ") '" \
                      + child_name + "'"
            if self.__is_folder(child_id):
                num_folders += 1
                self.df_print(self.get_path(child_id) + '\n')
            elif show_all:
                self.df_print(self.get_path(child_id) + '\n')

        print "# num_folders: " + str(num_folders)
        print "# num_files: " + str(num_files)

    def show_all(self):
        """Display the paths to all files available in My Drive
           Returns: nothing
        """
        if self.debug:
            print "# show_all()"
        file_list = self.list_all()
        num_folders = 0
        num_files = 0
        for file_id in file_list:
            metadata = self.get(file_id)
            file_name = metadata['name']
            num_files += 1
            if self.debug:
                print "# file_id: (" + file_id + ") '" \
                      + file_name + "'"
            if self.__is_folder(file_id):
                num_folders += 1
            self.df_print(self.get_path(file_id) + '\n')
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
            print "# load_cache: " + str(self.cache['path'])
        try:
            mtime = os.path.getmtime(self.cache['path'])
            self.cache['mtime'] = \
                datetime.datetime.utcfromtimestamp(mtime).isoformat()
        except OSError as error:
            print "# OSError: " + str(error)
            return
        try:
            cache_file = open(self.cache['path'], "r")
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
                cache_file = open(self.cache['path'], "w")
                json.dump(
                    self.file_data,
                    cache_file, indent=3,
                    separators=(',', ': ')
                )
                print "# Wrote " \
                    + str(len(self.file_data['metadata'])) \
                    + " nodes to " + self.cache['path'] + "."
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

    def report_startup(self):
        """Construct start-of-run information."""
        result = "# command line: '" + " ".join(sys.argv[0:]) + "'\n"
        result += "# program_name: " + self.program_name + "\n"
        result += "# iso_time_stamp: " + self.iso_time_stamp + "\n"
        return result

    def report_wrapup(self):
        """Print the final report form the test run."""
        cpu_time_1 = psutil.cpu_times()
        result = "# " + self.program_name + ": User time: " +\
            str(cpu_time_1[0] - self.cpu_time_0[0]) + " S\n"
        result += "# " + self.program_name + ": System time: " +\
            str(cpu_time_1[2] - self.cpu_time_0[2]) + " S\n"
        return result


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
        '--output', '-o',
        type=str,
        help='Send the output to a specific file.'
        )
    parser.add_argument(
        '--showall',
        action='store_const', const=True,
        help="Show all files in My Drive."
        )
    parser.add_argument(
        '--stat',
        type=str,
        help="Return the metadata for the node at the end of a path."
        )
    parser.add_argument(
        '--status',
        action='store_const', const=True,
        help="Report out the status of the DriveFile object."
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
    if arg is not None:
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


def handle_show_all(drive_file, show_all):
    """Handle the --listall operation."""
    if drive_file.debug:
        print "# handle_show_all(" + \
            "show_all: " + str(show_all) + \
            ")"
    if show_all:
        drive_file.show_all()
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


def handle_status(drive_file, arg, args_are_paths, show_all):
    """Handle the --status operation."""
    if drive_file.debug:
        print "# handle_status()"
        print "#    arg: " +  str(arg)
        print "#    args_are_paths: " +  str(args_are_paths)
        print "#    show_all: " + str(show_all)
    # Trick - the cache will not have been loaded, so let's
    # initialize it to avoid confusion.
    if arg:
        drive_file.init_metadata_cache()
        status = drive_file.get_status()
        for _ in status:
            print _
    return True


def do_work(teststats):
    """Parse arguments and handle them."""

    startup_report = teststats.report_startup()

    parser = setup_parser()
    args = parser.parse_args()

    # handle modifiers
    args_are_paths = False if args.f else True
    use_cache = False if args.nocache else True
    output_path = args.output if args.output else "stdout"

    # Do the work ...

    drive_file = DriveFile(True) if args.DEBUG else DriveFile(False)

    drive_file.set_output(output_path)
    drive_file.df_print(startup_report)

    print "# output going to: " + drive_file.output_path

    if use_cache:
        drive_file.load_cache()
    else:
        print "# Starting with empty cache."
        drive_file.init_metadata_cache()

    if args.cd is not None:
        drive_file.set_cwd(args.cd)
        drive_file.df_print("# pwd: " + drive_file.get_cwd() + '\n')

    handle_find(drive_file, args.find, args_are_paths, args.all)

    handle_stat(drive_file, args.stat, args_are_paths, args.all)

    handle_ls(drive_file, args.ls, args_are_paths, args.all)

    handle_show_all(drive_file, args.showall)

    handle_status(drive_file, args.status, args_are_paths, args.all)

    # Done with the work

    drive_file.df_print("# call_count: " + '\n')
    drive_file.df_print("#    get: " + \
            str(drive_file.call_count['get']) + '\n')
    drive_file.df_print("#    list_children: " + \
            str(drive_file.call_count['list_children']) + '\n')

    if not args.Z:
        drive_file.dump_cache()
    else:
        print "# skip writing cache."

    wrapup_report = teststats.report_wrapup()
    drive_file.df_print(wrapup_report)


def main():
    """Test code and basic CLI functionality engine."""
    test_stats = TestStats()
    do_work(test_stats)


if __name__ == '__main__':
    main()
