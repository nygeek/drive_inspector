""" Implementation of the DriveInspector tools and utilities

Started 2018-04-20 by Marc Donner

DriveFileRaw derived 2018-06-08 from the original DriveFile.

Copyright (C) 2018 Marc Donner

This is the uncached (raw) class for basic read-only access to a
Drive collection.  It is intended to be the superclass for a cached
class.

The design is intended to support the same signatures as the cached
class.  This class is inherently inefficient and should not be used
except for forensic and diagnostic purposes.

Design and naming conventions:
    get_ :: these methods retrieve a node from the Drive API.
            Results are Drive node structures or lists of
            such structures.
    list_ :: these methods search the Drive for nodes that meet
            various search criteria.  Results are lists of nodes.
    df_ :: these methods are used to interact with the DriveFile
            class metadata.
    show_ :: these methods use df_print() to display file names and
            metadata.

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
# googleapiclient.discovery.service()
#
# pylint: disable=no-member
#

from googleapiclient import discovery
from googleapiclient import errors

from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage

# Roadmap

# reload(sys)
# sys.setdefaultencoding('utf8')

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
        credentials = tools.run_flow(flow, store)
        print('Storing credentials to ' + credential_path)
    return credentials


def pretty_json(json_object):
    """Return a pretty-printed string of a JSON object (string)."""
    return json.dumps(json_object, indent=4, separators=(',', ': '))


class DriveFileRaw(object):
    """Class to provide uncached access to Google Drive object nodes."""

    FOLDERMIMETYPE = 'application/vnd.google-apps.folder'
    STANDARD_FIELDS = "id, name, parents, mimeType, size, owners, "
    STANDARD_FIELDS += "trashed, modifiedTime, createdTime, ownedByMe, "
    STANDARD_FIELDS += "shared"

    def __init__(self, debug):
        self.time_data = {}
        self.call_count = {}
        self.call_count['get'] = 0
        self.call_count['list_children'] = 0
        self.call_count['list_all'] = 0
        self.call_count['list_modified'] = 0
        self.call_count['list_newer'] = 0
        self.call_count['__get_named_child'] = 0
        self.debug = debug
        self.df_set_output("stdout")
        self.service = discovery.build(
            'drive',
            'v3',
            http=get_credentials().authorize(httplib2.Http())
            )

    # Meta methods

    def df_status(self):
        """Get status of DriveFile instance.
           Returns: List of String
        """
        if self.debug:
            print("# df_status[raw]()")
        result = []
        result.append("# ========== RAW STATUS ==========\n")
        result.append("# debug: " + str(self.debug) + "\n")
        result.append("# output_path: '" + str(self.output_path) + "'\n")
        for key in self.call_count:
            result.append("# call_count: " + key + ": " + \
            str(self.call_count[key]) + "\n")
        result.append("# ========== RAW STATUS ==========\n")
        return result

    def df_print(self, line):
        """Internal print function, just for output."""
        self.output_file.write(line)

    def df_set_output(self, path):
        """Assign an output file path."""
        if self.debug:
            print("# df_set_output[raw](" + str(path) + ")")
        self.output_path = path
        try:
            if path == 'stdout':
                self.output_file = sys.stdout
            else:
                self.output_file = open(self.output_path, "w")
            self.output_path = path
            print("# writing output to: " + str(self.output_path))
        except IOError as error:
            print("# Can not open" + self.output_path + ".")
            print("#    IOError: " + str(error))
            self.output_file = sys.stdout
            self.output_path = 'stdout'

    def df_field_list(self):
        """Report a list of available fields.
           Returns a list of strings.
        """
        if self.debug:
            print("df_field_list[raw]()")
        return self.STANDARD_FIELDS.split(", ")

    def set_debug(self, debug):
        """Set the debug flag."""
        if self.debug:
            print("set_debug[raw](" + str(debug) + ")")
        self.debug = debug
        if self.debug:
            print("    => " + str(self.debug))
        return self.debug

    def get_debug(self):
        """Return the debug flag."""
        if self.debug:
            print("get_debug[raw]() => " + str(self.debug))
        return self.debug

    # Get methods

    def get(self, node_id):
        """Get the node for node_id.
           Returns: node
        """
        if self.debug:
            print("# get[raw](node_id: " + node_id + ")")
        t_start = time.time()
        node = \
            self.service.files().get(
                fileId=node_id,
                fields=self.STANDARD_FIELDS
                ).execute()
        self.call_count['get'] += 1
        self.time_data[node_id] = time.time() - t_start
        return node

    def __get_named_child(self, node_id, component):
        """ Given the node_id of a folder and a component name, find the
            matching child, if it exists.
            Returns: node
        """
        if self.debug:
            print("# __get_named_child[raw](node_id:" \
                + str(node_id) + ", " + component + ")")

        # children = self.list_children(node_id)
        query = "'" + node_id + "' in parents"
        query += "and name = '" + component +"'"
        fields = "nextPageToken, "
        fields += "files(" + self.STANDARD_FIELDS + ")"

        if self.debug:
            print("# query: " + query)
            print("# fields: " + fields)

        npt = "start"
        children = []
        while npt:
            if self.debug:
                print("# __get_named_child: npt: (" + npt + ")")
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
                self.call_count['__get_named_child'] += 1
                npt = response.get('nextPageToken')
                children += response.get('files', [])
            except errors.HttpError as error:
                print("HttpError: " + str(error))
                response = "not found."
                npt = None

        return children

    # Logic methods

    def __is_folder(self, node):
        """Test whether node represents a folder.
           Returns: Boolean
        """
        node_id = node['id']
        if self.debug:
            print("# __is_folder[raw](" + node_id + ")")
        result = node['mimeType'] == self.FOLDERMIMETYPE \
                 and ("fileExtension" not in node)
        if self.debug:
            print("# node: " + pretty_json(node))
            print("#   => " + str(result))
        return result

    # List methods

    def list_children(self, node_id):
        """Get the children of node_id.  Limited to immediate children.
           Returns: list of node
        """
        if self.debug:
            print("# list_children[raw](node_id: " + node_id + ")")
        query = "'" + node_id + "' in parents"
        fields = "nextPageToken, "
        fields += "files(" + self.STANDARD_FIELDS + ")"
        if self.debug:
            print("# query: " + query)
            print("# fields: " + fields)
        npt = "start"
        children = []
        while npt:
            if self.debug:
                print("#    list_children: npt: (" + npt + ")")
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
                print("HttpError: " + str(error))
                response = "not found."
                npt = None
        if self.debug:
            print("#    => len: " + str(len(children)))
        return children

    def list_all_children(self, node_id, show_all=False):
        """Return the entire list of nodes beneath a given node.
           Return: list of node
        """
        if self.debug:
            print("# list_all_children[raw](" \
                + "node_id: " + str(node_id) \
                + ", show_all: " + str(show_all) + ")")
        result = []
        queue = self.list_children(node_id)
        while queue:
            node = queue.pop(0)
            node_id = node['id']
            if self.debug:
                print("#    node_id: (" + node_id + ")")
            if self.__is_folder(node):
                children = self.list_children(node_id)
                queue += children
                result.append(node)
            elif show_all:
                result.append(node)
        return result

    def list_all(self):
        """Get all of the files to which I have access.
           Returns: list of node
        """
        if self.debug:
            print("# list_all[raw]()")
        fields = "nextPageToken, "
        fields += "files(" + self.STANDARD_FIELDS + ")"
        if self.debug:
            print("# fields: " + fields)
        npt = "start"
        node_list = []
        while npt:
            if self.debug:
                print("#    npt: (" + npt + ")")
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
                print("HttpError: " + str(error))
                response = "not found."
                npt = None
        if self.debug:
            print("#     => len: " + str(len(node_list)))
        return node_list

    def list_newer(self, date):
        """Find nodes that are modified more recently that
           the provided date.
           Returns: list of node
        """
        if self.debug:
            print("# list_newer[raw](date: " + str(date) + ")")
        newer_node_list = []
        fields = "nextPageToken, "
        fields += "files(" + self.STANDARD_FIELDS + ")"
        npt = "start"
        query = "modifiedTime > '" + str(date) + "'"
        while npt:
            if self.debug:
                print("# list_newer: npt: (" + npt + ")")
                print("#    query: '" + str(query) + "'")
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
                newer_node_list += response.get('files', [])
            except errors.HttpError as error:
                print("HttpError: " + str(error))
                response = "not found."
                npt = None
        if self.debug:
            print("#    => len: " + str(len(newer_node_list)))
        return newer_node_list

    # Show methods
    # Probably need to rewrite all using a render() method
    # that should be part of the DriveFileReport class

    def show_node(self, node_id):
        """ Display the node for a node."""
        if self.debug:
            print("# show_node[raw](" + node_id + ")")
        self.df_print(pretty_json(self.get(node_id)))

    def show_children(self, node_id):
        """ Display the names of the children of a node.
            This is the core engine of the --ls function.
        """
        if self.debug:
            print("# show_children[raw](" + str(node_id) + ")")
        children = self.list_children(node_id)
        if self.debug:
            print("# show_children: len(children): " + str(len(children)))
        for child in children:
            child_id = child['id']
            if self.debug:
                print("# child: " + str(child_id))
            child_name = child['name']
            if self.__is_folder(child):
                child_name += "/"
            self.df_print(child_name + '\n')

    def show_all_children(self, node_id, show_all=False):
        """ Display all child directories of a node
            If show_all is True, then display all files.  If False
            then show only the folder structure.
        """
        if self.debug:
            print("# show_all_children[raw](" + node_id + ",")
            print("#    show_all: " + str(show_all) + ")")

        children = self.list_all_children(node_id, show_all)

        num_files = 0
        num_folders = 0

        for child in children:
            child_id = child['id']
            child_name = child['name']
            num_files += 1
            if self.debug:
                print("# child_id: (" + child_id + ") '" \
                      + child_name + "'")
            if self.__is_folder(child):
                num_folders += 1
                self.df_print(child_name + '/\n')
            elif show_all:
                self.df_print(child_name + '\n')

    def show_all(self):
        """Display the names of all files available in My Drive
           Returns: nothing
        """
        if self.debug:
            print("# show_all[raw]()")
        node_list = self.list_all()
        num_folders = 0
        num_files = 0
        for node in node_list:
            node_id = node['id']
            node_name = node['name']
            num_files += 1
            if self.debug:
                print("#    node_id: (" + node_id + ") '" \
                      + node_name + "'")
            if self.__is_folder(node):
                num_folders += 1
                self.df_print(node_name + '/\n')
            else:
                self.df_print(node_name + '\n')
        self.df_print("# num_folders: " + str(num_folders) + "\n")
        self.df_print("# num_files: " + str(num_files) + "\n")

    def __str__(self):
        result = []
        return result


class TestStats(object):
    """Organize and display stats for the running of the program."""

    def __init__(self):
        self.cpu_time_0 = psutil.cpu_times()
        self.start_iso_time_stamp = \
            time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
        self.end_iso_time_stamp = ""
        self.program_name = sys.argv[0]

    def report_startup(self):
        """Construct start-of-run information."""
        result = "# command line: '" + " ".join(sys.argv[0:]) + "'\n"
        result += "# program_name: " + self.program_name + "\n"
        result += "# start_iso_time_stamp: " \
            + self.start_iso_time_stamp + "\n"
        return result

    def report_wrapup(self):
        """Print the final report form the test run."""
        self.end_iso_time_stamp = \
            time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
        cpu_time_1 = psutil.cpu_times()
        result = "# " + self.program_name + ": User time: " +\
            str(cpu_time_1[0] - self.cpu_time_0[0]) + " S\n"
        result += "# " + self.program_name + ": System time: " +\
            str(cpu_time_1[2] - self.cpu_time_0[2]) + " S\n"
        result += "# end_iso_time_stamp: " \
            + self.end_iso_time_stamp + "\n"
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
        action='store_true',
        help='(Modifier)  When running a find, show all files.'
        )
    parser.add_argument(
        '--find',
        type=str,
        help='Given a fileid, recursively traverse all subfolders.'
        )
    parser.add_argument(
        '--ls',
        type=str,
        help='Given a fileid, list the files contained in it.'
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
        help="Display the node."
        )
    parser.add_argument(
        '--status',
        action='store_true',
        help="Report out the status of the DriveFile object."
        )
    parser.add_argument(
        '-D', '--DEBUG',
        action='store_true',
        help='(Modifier) Turn debugging on.'
        )
    return parser


def handle_stat(drive_file, arg, show_all):
    """Handle the --stat operation."""
    if drive_file.debug:
        print("# handle_stat(")
        print("#    arg: '" +  str(arg) + "',")
        print("#    show_all: " +  str(show_all))
    if arg is not None:
        drive_file.show_node(arg)
    return True


def handle_find(drive_file, arg, show_all):
    """Handle the --find operation."""
    if drive_file.debug:
        print("# handle_find(")
        print("#    arg: '" +  str(arg) + "',")
        print("#    show_all: " +  str(show_all))
    if arg is not None:
        drive_file.show_all_children(arg, show_all)
    return True


def handle_showall(drive_file, show_all):
    """Handle the --listall operation."""
    if drive_file.debug:
        print("# handle_showall(" + \
            "show_all: " + str(show_all) + \
            ")")
    drive_file.show_all()
    return True


def handle_ls(drive_file, arg, show_all):
    """Handle the --ls operation."""
    if drive_file.debug:
        print("# handle_ls(")
        print("#    arg: '" +  str(arg) + "',")
        print("#    show_all: " + str(show_all))
    if arg is not None:
        drive_file.show_children(arg)
    return True


def handle_newer(drive_file, arg, show_all):
    """Handle the --newer operation."""
    if drive_file.debug:
        print("# handle_newer(")
        print("#    arg: '" +  str(arg) + "',")
        print("#    show_all: " + str(show_all))
    drive_file.show_newer(arg, show_all)


def handle_status(drive_file, arg, show_all):
    """Handle the --status operation."""
    if drive_file.debug:
        print("# handle_status()")
        print("#    arg: '" +  str(arg) + "',")
        print("#    show_all: " + str(show_all))
    status = drive_file.df_status()
    for _ in status:
        drive_file.df_print(_)
    return True


def do_work(teststats):
    """Parse arguments and handle them."""

    startup_report = teststats.report_startup()

    parser = setup_parser()
    args = parser.parse_args()

    # handle modifiers
    output_path = args.output if args.output else "stdout"

    # Do the work ...

    drive_file = DriveFileRaw(True) if args.DEBUG else DriveFileRaw(False)

    drive_file.df_set_output(output_path)
    drive_file.df_print(startup_report)

    print("# output going to: " + drive_file.output_path)

    _ = handle_find(drive_file, args.find, args.all) \
            if args.find else ""

    _ = handle_stat(drive_file, args.stat, args.all) \
            if args.stat else ""

    _ = handle_ls(drive_file, args.ls, args.all) \
            if args.ls else ""

    _ = handle_showall(drive_file, args.showall) \
            if args.showall else ""

    _ = handle_status(drive_file, args.status, args.all) \
            if args.status else ""

    # Done with the work

    wrapup_report = teststats.report_wrapup()
    drive_file.df_print(wrapup_report)


def main():
    """Test code and basic CLI functionality engine."""
    test_stats = TestStats()
    do_work(test_stats)


if __name__ == '__main__':
    main()
