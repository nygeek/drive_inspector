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

class DriveFile(object):
    """Class to provide cached access to Google Drive object metadata."""

    FOLDERMIMETYPE = 'application/vnd.google-apps.folder'
    STANDARD_FIELDS = "id, name, parents, mimeType, owners, trashed, "
    STANDARD_FIELDS += "modifiedTime, createdTime, ownedByMe, shared"
    STRMODE = 'full'

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
        self.file_data['cwd'] = '/'
        # 2
        self.call_count = {}
        self.call_count['get'] = 0
        self.call_count['list_children'] = 0
        self.call_count['list_all'] = 0
        self.call_count['list_modified'] = 0
        # 3
        self.cache = {}
        self.cache['path'] = "./.filedata-cache.json"
        self.cache['mtime'] = "?"
        self.debug = debug
        self.set_output("stdout")
        # 4
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

    def get(self, node_id):
        """Get the node for node_id.
           Returns: node
        """
        if self.debug:
            print "# get(node_id: '" + node_id + "')"
        if node_id not in self.file_data['metadata']:
            if self.debug:
                print "# calling Google ..."
            t_start = time.time()
            node = self.service.files().get(
                    fileId=node_id,
                    fields=self.STANDARD_FIELDS
                    ).execute()
            self.call_count['get'] += 1
            self.file_data['time'][node_id] = time.time() - t_start
            if self.debug:
                print "#    register_metadata(node_name: '" \
                        + node_name + "')"
            self.__register_metadata([node])
        return self.file_data['metadata'][node_id]

    def get_path(self, node_id):
        """Given a file_id, construct the path back to root.
           Returns: string
        """
        if self.debug:
            print "# get_path(" + node_id + ")"

        if node_id in self.file_data['path']:
            return self.file_data['path'][node_id]

        # If we got here, then the path is not cached
        if node_id not in self.file_data['metadata']:
            # file_id is not in the cache either
            node = self.get(node_id)
        else:
            node = self.file_data['metadata'][node_id]
        # We now have file in the variable metadata

        node_name = node['name']

        if 'parents' not in node:
            # If there is no parent AND the file is not owned by
            # me, then create a synthetic root for it.
            if 'ownedByMe' in node \
                   and not node['ownedByMe']:
                parent = "unknown/"
                if 'owners' in node:
                    parent = \
                        '~' \
                        + node['owners'][0]['emailAddress'] + \
                        '/.../'
                # Note that we're using the parent path as the fake
                # FileID for the parent's root.
                self.file_data['path'][parent] = parent
            else:
                parent = 'root'
        else:
            parent = node['parents'][0]

        # when we get here parent is either a real FileID or the
        # thing we use to refer to the My Drive of another user

        if node_name == "My Drive":
            self.file_data['path'][node_id] = "/"
            self.file_data['path']['root'] = "/"
            self.file_data['dirty'] = True
            return ""
        new_path = self.get_path(parent) + node_name
        self.file_data['path'][node_id] = new_path + '/' \
            if self.__is_folder(node) else new_path
        return self.file_data['path'][node_id]

    def __register_metadata(self, node_list):
        """Accept an array of metadata and put them in the cache.
           Returns: array of FileID
        """
        if self.debug:
            print "# __register_metadata(len: " + str(len(node_list)) + ")"
        # Now comb through and put everything in file_data.
        i = 0
        results = []
        for node in node_list:
            node_id = node['id']
            node_name = node['name']
            if self.debug:
                print "#    __register_metadata: i: " + str(i) \
                      + " (" + node_id + ") '" + node_name + "'"
            if node_id not in self.file_data['metadata']:
                if self.debug:
                    print "#    __register_metadata: adding " + node_id
                self.file_data['metadata'][node_id] = node
                self.file_data['dirty'] = True
                self.file_data['ref_count'][node_id] = 1
                if node_name == "My Drive":
                    self.file_data['metadata']["root"] = node
                    self.file_data['ref_count']["root"] = 1
                self.get_path(node_id)
            results.append(node_id)
            i += 1
        if self.debug:
            print "# __register_metadata results: " + str(len(results))
        return results

    def df_print(self, line):
        """Internal print function, just for output."""
        self.output_file.write(line)

    def set_output(self, path):
        """ Assign an output file path. """
        if self.debug:
            print "# set_output(" + str(path) + ")"
        self.output_path = path
        try:
            if path == 'stdout':
                self.output_file = sys.stdout
            else:
                self.output_file = open(self.output_path, "w")
            print "#   => " + str(self.output_path)
        except IOError as error:
            print "# Can not open" + self.output_path + "."
            print "#    IOError: " + str(error)
            self.output_file = sys.stdout
            self.output_path = 'stdout'

    def get_field_list(self):
        """Report a list of available fields.
           Returns: list of strings.
        """
        if self.debug:
            print "get_field_list()"
        return self.STANDARD_FIELDS.split(", ")

    def resolve_path(self, path):
        """Given a path, return the node_id of the terminal node.
           Returns: FileID
        """
        if self.debug:
            print "# resolve_path(" + str(path) + ")"
        if path and path[0] != "/":
            # relative path ... combine with cwd ...
            path = self.get_cwd() + "/" + path
        if path in self.file_data['path'].values():
            for file_id, dict_path in self.file_data['path'].iteritems():
                if dict_path == path:
                    return file_id
                # better not ever get here!
        path_components = path.split("/")
        path_components.pop(0)
        if self.debug:
            print "path_components: " + str(path_components)
        if 'root' not in self.file_data['metadata']:
            node = self.get('root')
        node_id = self.get('root')['id']
        for component in path_components:
            # if the component is a '.' (current directory) then skip it
            if component != ".":
                node_id = self.__get_named_child(node_id, component)
                if node_id in ["<not_found>", "<error"]:
                    print "# resolve_path(" + path + ") => not found."
                    return node_id
                if self.debug:
                    print "# " + component + " => (" + node_id + ")"
        return node_id

    def __get_named_child(self, node_id, component):
        """ Given a node_id and a component name, find the matching child.
            Returns: FileID
            Returns: <not_found> if there is no child by that name
        """
        if self.debug:
            print "# __get_named_child(node_id:" \
                + str(node_id) + ", " + component + ")"
        children = self.list_children(node_id)
        for child_id in children:
            if self.debug:
                print "#    => child_id:" + child_id + ")"
            if child_id in self.file_data['metadata']:
                child_name = self.file_data['metadata'][child_id]['name']
            else:
                child_name = self.get(child_id)['name']
            if self.debug:
                print "#    => child name:" + str(child_name) + ")"
            if child_name == component:
                return child_id
        return "<not_found>"

    def __is_folder(self, node):
        """Test whether node is a folder.
           Returns: Boolean
        """
        node_id = node['id']
        if self.debug:
            print "# __is_folder(" + node_id + ")"
        result = node['mimeType'] == self.FOLDERMIMETYPE \
                 and ("fileExtension" not in node)
        if self.debug:
            print "#   => " + str(result)
        return result

    def list_children(self, node_id):
        """Get the children of node_id.
           Returns: list of FileID
        """
        if self.debug:
            print "# list_children(node_id: " + node_id + ")"

        # Are there children of node_id in the cache?
        results = [item_id for item_id in self.file_data['metadata'] \
            if ('parents' in self.file_data['metadata'][item_id] \
                and node_id \
                in self.file_data['metadata'][item_id]['parents'])]

        if not results:
            query = "'" + node_id + "' in parents"
            fields = "nextPageToken, "
            fields += "files(" + self.STANDARD_FIELDS + ")"
            if self.debug:
                print "# query: " + query
                print "# fields: " + fields
            # No children from the cache - search Google Drive
            npt = "start"
            children = []
            while npt:
                if self.debug:
                    print "# calling Google ..."
                    print "#    => npt '" + npt + "'"
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
            print "#    => results: " + str(len(results))
        return results

    def list_all(self):
        """Get all of the nodes to which I have access.
           Returns: list of node
        """
        if self.debug:
            print "# list_all()"
        fields = "nextPageToken, "
        fields += "files(" + self.STANDARD_FIELDS + ")"
        if self.debug:
            print "# fields: " + fields
        npt = "start"
        node_list = []
        while npt:
            if self.debug:
                print "# calling Google ..."
                print "#    => npt '" + npt + "'"
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
                node_list += response.get('files', [])
            except errors.HttpError as error:
                print "HttpError: " + str(error)
                response = "not found."
                npt = None
        if node_list:
            self.__register_metadata(node_list)
        if self.debug:
            print "# list_all results: " + str(len(node_list))
        return node_list

    def list_newer(self, date):
        """Find nodes that are modified more recently than date.
           Returns: List of node
        """
        if self.debug:
            print "# list_newer(date: " + str(date) + ")"
        newer_list = []
        npt = "start"
        # modifiedTime > '2012-06-04T12:00:00'
        query = "'modifiedTime < '" + str(date) + "'"
        fields = "nextPageToken, "
        fields += "files(" + self.STANDARD_FIELDS + ")"
        while npt:
            if self.debug:
                print "# Calling Google ..."
                print "#    npt => '" + npt + "'"
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
            self.__register_metadata(newer_list)
        if self.debug:
            print "#    => newer_list " + str(len(newer_list))
        return newer_list

    def show_metadata(self, path, node_id):
        """ Display a node."""
        if path is not None:
            if self.debug:
                print "# show_metadata(path: '" + path + "')"
            node_id = self.resolve_path(path)
        else:
            if self.debug:
                print "# show_metadata(node_id: '" + node_id + "')"
        if node_id == "<not-found>":
            self.df_print("'" + path + " not found.\n")
        else:
            self.df_print(pretty_json(self.get(node_id)))

    def show_children(self, path, node_id):
        """ Display the names of the children of a node.
            This is the core engine of the --ls function.
        """
        if path is not None:
            if self.debug:
                print "# show_children(path: '" + str(path) + "')"
            node_id = self.resolve_path(path)
        else:
            if self.debug:
                print "# show_children(node_id: (" + str(node_id) + "))"
        children = self.list_children(node_id)
        if self.debug:
            print "# show_children: children: " + str(children)
        for child_id in children:
            if self.debug:
                print "# child_id: " + str(child_id)
            child = self.get(child_id)
            child_name = child['name']
            if self.__is_folder(child):
                child_name += "/"
            self.df_print(child_name + '\n')

    def list_all_children(self, node_id, show_all=False):
        """Return the list of FileIDs beneath a given node.
           Return: list of FileID
        """
        if self.debug:
            print "# list_all_children(" \
                + "node_id: " + str(node_id) \
                + ", show_all: " + str(show_all) + ")"
        result = []
        id_queue = self.list_children(node_id)
        while id_queue:
            child_id = id_queue.pop(0)
            child = self.get(child_id)
            if self.debug:
                print "# child_id: (" + child_id + ")"
            if self.__is_folder(child):
                id_queue += self.list_children(child_id)
                result.append(child_id)
            elif show_all:
                result.append(child_id)
        return result

    def show_all_children(self, path, node_id, show_all=False):
        """ Display all child directories of a node. """
        if path is not None:
            if self.debug:
                print "# show_all_children(path: '" + path + "')"
                print "#    show_all: " + str(show_all)
            node_id = self.resolve_path(path)
        else:
            if self.debug:
                print "# show_all_children(file_id: (" + node_id + "))"
                print "#    show_all: " + str(show_all)
        children = self.list_all_children(node_id, show_all)
        num_files = 0
        num_folders = 0
        for child_id in children:
            child = self.get(child_id)
            child_name = child['name']
            num_files += 1
            if self.debug:
                print "# child_id: (" + child_id + ") '" \
                      + child_name + "'"
            if self.__is_folder(child):
                num_folders += 1
                self.df_print(self.get_path(child_id) + '\n')
            elif show_all:
                self.df_print(self.get_path(child_id) + '\n')
        self.df_print("#    num_folders: " + str(num_folders) + "\n")
        self.df_print("#    num_files: " + str(num_files) + "\n")

    def show_all(self):
        """Display the paths to all files available in My Drive
           Returns: nothing
        """
        if self.debug:
            print "# show_all()"
        node_list = self.list_all()
        num_folders = 0
        num_files = 0
        for node in node_list:
            node_id = node['id']
            # metadata = self.get(node['id'])
            node_name = node['name']
            num_files += 1
            if self.debug:
                print "# node_id: (" + node_id + ") '" \
                      + node_name + "'"
            if self.__is_folder(node):
                num_folders += 1
            self.df_print(self.get_path(node_id) + '\n')
        self.df_print("#    num_folders: " + str(num_folders) + "\n")
        self.df_print("#    num_files: " + str(num_files) + "\n")

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
            self.init_metadata_cache()
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
        if self.STRMODE == 'full':
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
    if arg:
        # initialize the cache.
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
