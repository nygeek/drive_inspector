""" Implementation of the DriveInspector tools and utilities

Started 2018-04-20 by Marc Donner

DriveFileCached 2018-06-09 from the original DriveFile

Copyright (C) 2018 Marc Donner

This is the cached class.  It builds on top of the uncached (raw)
class.  See the heading comments in DriveFileRaw for naming and
design conventions for this code.

"""

import argparse
import datetime
import json
import os
import sys
import time

from drivefileraw import DriveFileRaw
from drivefileraw import pretty_json
from drivefileraw import TestStats

reload(sys)
sys.setdefaultencoding('utf8')

APPLICATION_NAME = 'Drive Inspector'


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


class DriveFileCached(DriveFileRaw):
    """Class to provide cached access to Google Drive object metadata."""

    STRMODE = 'full'

    def __init__(self, debug):
        self.file_data = {}
        self.file_data['path'] = {}
        self.file_data['path']['<none>'] = ""
        self.file_data['path']['root'] = "/"
        self.file_data['time'] = {}
        self.file_data['time']['<none>'] = 0
        self.file_data['ref_count'] = {}
        self.file_data['ref_count']['<none>'] = 0
        self.file_data['cwd'] = '/'
        self.cache = {}
        self.cache['path'] = "./.filedata-cache.json"
        self.cache['mtime'] = "?"
        self.cwd = "/"
        super(DriveFileCached, self).__init__(debug)

    def df_status(self):
        """Get status of DriveFileCached instance.
           Returns: List of String
        """
        if self.debug:
            print "# df_status()"
        result = super(DriveFileCached, self).df_status()
        result.append("# ========== Cache STATUS ==========\n")
        result.append("# cache['path']: '" \
            + str(self.cache['path']) + "'\n")
        result.append("# cache['mtime']: " \
            + str(self.cache['mtime']) + "\n")
        result.append("# cwd: '" \
            + str(self.file_data['cwd']) + "'\n")
        if 'metadata' in self.file_data:
            result.append("# cache size: " \
                + str(len(self.file_data['metadata'])) + " nodes\n")
        else:
            result.append("# cache size: 0\n")
        result.append("# path cache size: " + \
            str(len(self.file_data['path'])) + " paths\n")
        result.append("# ========== Cache STATUS ==========\n")
        return result

    def get(self, file_id):
        """Get the metadata for file_id.
           Returns: metadata structure
        """
        if self.debug:
            print "# get(file_id: " + file_id + ")"

        # If file_id is not in the cache, go to Raw to get it
        if file_id not in self.file_data['metadata']:
            if self.debug:
                print "# calling Google ..."
            t_start = time.time()
            file_metadata = super(DriveFileCached, self).get(file_id)
            self.file_data['time'][file_id] = time.time() - t_start
            self.__register_metadata([file_metadata])
            if file_id == "root":
                # very special case!
                self.file_data['metadata'][file_id] = file_metadata
                self.file_data['ref_count'][file_id] = 1
                self.get_path(file_id)

        # OK, now file_id is in the cache (or file_id is bogus)
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

        # Recursion ... upward!
        new_path = self.get_path(parent) + file_name

        self.file_data['path'][file_id] = new_path + '/' \
            if self.__is_folder(metadata) else new_path

        return self.file_data['path'][file_id]

    def __register_metadata(self, node_list):
        """Accept a list of raw metadata and register them in
           self.file_data.
           Returns: array of FileID
        """
        if self.debug:
            print "# __register_metadata(len: " \
                    + str(len(node_list)) + ")"

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
                self.get_path(node_id)
            results.append(node_id)
            i += 1

        if self.debug:
            print "# __register_metadata results: " + str(len(results))

        return results

    def resolve_path(self, path):
        """Given a path, find and return the FileID matching the
           terminal node.  Like the namei() syscall in Unix.
           Returns: FileID
        """
        if self.debug:
            print "# resolve_path(" + str(path) + ")"

        if path in self.file_data['path'].values():
            for file_id, test_path in self.file_data['path'].iteritems():
                if test_path == path:
                    return file_id

        # This is disgusting tech debt.  Got to handle the trailing '/'
        # better.  TODO
        if path + '/' in self.file_data['path'].values():
            for file_id, test_path in self.file_data['path'].iteritems():
                if test_path == path + '/':
                    return file_id

        path_components = path.split("/")
        # this pop drops the leading empty string
        path_components.pop(0)
        if self.debug:
            print "#    path_components: " + str(path_components)

        node_id = self.get("root")['id']
        for component in path_components:
            # if the component is a '.' (current directory) then skip it
            if component != ".":
                node = self.__get_named_child(node_id, component)
                node_id = node['id']
                if node in ["<not_found>", "<error"]:
                    print "# resolve_path(" + path + ") => not found."
                    return node
                if self.debug:
                    print "# " + component + " => (" + node_id + ")"
        return node_id

    def __get_named_child(self, file_id, component):
        """ Given a file_id (folder) and a component name, find the
            matching child, if it exists.
            Returns: metadata
            Returns: <not_found> if there is no child by that name
        """
        if self.debug:
            print "# __get_named_child[cached](file_id:" \
                + str(file_id) + ", " + component + ")"

        children = self.list_children(file_id)
        results = [item for item in children \
            if ( \
                'parents' in item \
                and file_id in item['parents'] \
                and component == item['name'] \
            )]

        # Three cases:
        #    results is empty: <not_found>
        #    results has exactly one item in it
        #    results has > 1 item in it (oops!)

        if not results:
            # no results
            response = "<not_found>"
        elif len(results) > 1:
            response = "<too_many_matches>"
        else:
            response = results[0]

        if self.debug:
            print "#    __get_named_child[cached] => " \
                + str(pretty_json(response))
        return response

    def __is_folder(self, file_metadata):
        """Test whether file_metadata represents a folder.
           Returns: Boolean
        """
        file_id = file_metadata['id']
        if self.debug:
            print "# __is_folder(file_id: " + file_id + ")"
        result = file_metadata['mimeType'] == self.FOLDERMIMETYPE \
                 and ("fileExtension" not in file_metadata)
        if self.debug:
            print "# file_metadata: " + pretty_json(file_metadata)
            print "#   => " + str(result)
        return result

    def list_children(self, node_id):
        """Get the children of node_id.
           Returns: array of metadata
        """
        if self.debug:
            print "# list_children[cached](node_id: " + node_id + ")"

        # Are there children of node_id in the cache?

        children = [self.file_data['metadata'][item] \
            for item in self.file_data['metadata'] \
                if ('parents' in self.file_data['metadata'][item] \
                    and node_id in self.file_data['metadata'][item]['parents'])]

        if not children:
            children = super(DriveFileCached, self).list_children(node_id)
            self.__register_metadata(children)

        if self.debug:
            print "#    children: " + str(len(children))
        return children

    def list_all(self):
        """Get all of the files to which I have access.
           Returns: list of metadata
        """
        if self.debug:
            print "# list_all[cached]()"

        node_list = super(DriveFileCached, self).list_all()

        if node_list:
            self.__register_metadata(node_list)

        if self.debug:
            print "# list_all node_list[cached]: " + str(len(node_list))

        return node_list

    def list_newer(self, date):
        """Find nodes that are modified more recently that
           the provided date.
           Returns: List of FileID
        """
        if self.debug:
            print "# list_newer[cached](date: " + str(date) + ")"
        results = super(DriveFileCached, self).list_newer(date)

        return results

    def show_metadata(self, file_id):
        """ Display the metadata for a node."""
        if self.debug:
            print "# show_metadata[cached](file_id: (" + file_id + "))"
        self.df_print(pretty_json(self.get(file_id)))

    def show_children(self, file_id):
        """ Display the names of the children of a node.
            This is the core engine of the --ls function.
        """
        if self.debug:
            print "# show_children[cached](file_id: (" \
                + str(file_id) + "))"
        children = self.list_children(file_id)
        if self.debug:
            print "# show_children[cached]: len(children): " \
                + str(len(children))
        for child in children:
            child_id = child['id']
            if self.debug:
                print "# child_id: " + str(child_id)
            child_name = child['name']
            if self.__is_folder(child):
                child_name += "/"
            self.df_print(child_name + '\n')

    def list_all_children(self, file_id, show_all=False):
        """Return the list of FileIDs beneath a given node.
           Return: list of metadata
        """
        if self.debug:
            print "# list_all_children[cached](" \
                + "file_id: " + str(file_id) \
                + ", show_all: " + str(show_all) + ")"
        result = []
        queue = self.list_children(file_id)
        while queue:
            node = queue.pop(0)
            node_id = node['id']
            if self.debug:
                print "#    node_id: (" + node_id + ")"
            if self.__is_folder(node):
                children = self.list_children(node_id)
                queue += children
                result.append(node)
            elif show_all:
                result.append(node)
        return result

    def show_all_children(self, file_id, show_all=False):
        """ Display all child directories of a node
            show_all:
                True: display all files.
                False: show just the folder structure.
        """
        if self.debug:
            print "# show_all_children[cached](file_id: (" + file_id + "))"
            print "#    show_all: " + str(show_all)

        children = self.list_all_children(file_id, show_all)

        num_files = 0
        num_folders = 0

        for child in children:
            child_id = child['id']
            child_name = child['name']
            num_files += 1
            if self.debug:
                print "#    child_id: (" + child_id + ") '" \
                      + child_name + "'"
            if self.__is_folder(child):
                num_folders += 1
                self.df_print(self.get_path(child_id) + '\n')
            elif show_all:
                self.df_print(self.get_path(child_id) + '\n')

        self.df_print("#    num_folders: " + str(num_folders) + '\n')
        self.df_print("#    num_files: " + str(num_files) + '\n')

    def show_all(self):
        """Display the paths to all files available in My Drive
           Returns: nothing
        """
        if self.debug:
            print "# show_all[cached]()"

        node_list = self.list_all()
        num_folders = 0
        num_files = 0
        for node in node_list:
            node_id = node['id']
            node_name = node['name']
            num_files += 1
            if self.debug:
                print "#    file_id: (" + node_id + ") '" \
                      + node_name + "'"
            if self.__is_folder(node):
                num_folders += 1
            self.df_print(self.get_path(node_id) + '\n')
        self.df_print("#    num_folders: " + str(num_folders) + '\n')
        self.df_print("#    num_files: " + str(num_files) + '\n')

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
            print "# get_cwd => " + self.file_data['cwd']
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
            print "set_debug[cached](" + str(debug) + ")"
        self.debug = debug
        if self.debug:
            print "set_debug => debug:" + str(self.debug)
        return self.debug

    def get_debug(self):
        """Return the debug flag."""
        if self.debug:
            print "# get_debug[cached] => debug:" + str(self.debug)
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


def handle_stat(drive_file, file_id, show_all):
    """Handle the --stat operation."""
    if drive_file.debug:
        print "# handle_stat[cached]("
        print "#    show_all: " +  str(show_all)
    if file_id is not None:
        drive_file.show_metadata(file_id)
    return True


def handle_find(drive_file, file_id, show_all):
    """Handle the --find operation."""
    if drive_file.debug:
        print "# handle_find[cached]("
        print "#    file_id: " +  str(file_id)
        print "#    show_all: " +  str(show_all)
    if file_id is not None:
        drive_file.show_all_children(file_id, show_all)
    return True


def handle_show_all(drive_file, show_all):
    """Handle the --listall operation."""
    if drive_file.debug:
        print "# handle_show_all[cached]()"
        print "#    show_all: " + str(show_all)
    drive_file.show_all()
    return True


def handle_ls(drive_file, file_id, show_all):
    """Handle the --ls operation."""
    if drive_file.debug:
        print "# handle_ls[cached]("
        print "#    show_all: " + str(show_all)
    if file_id is not None:
        drive_file.show_children(file_id)
    return True


def handle_status(drive_file, show_all):
    """Handle the --status operation."""
    if drive_file.debug:
        print "# handle_status[cached]()"
        print "#    show_all: " + str(show_all)
    # Trick - the cache will not have been loaded, so let's
    # initialize it to avoid confusion.
    drive_file.init_metadata_cache()
    status = drive_file.df_status()
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

    drive_file = DriveFileCached(True) if args.DEBUG \
                 else DriveFileCached(False)

    drive_file.df_set_output(output_path)
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

    if args_are_paths:
        if args.stat:
            path = canonicalize_path(
                drive_file.get_cwd(),
                args.stat,
                drive_file.debug
            )
        elif args.ls:
            path = canonicalize_path(
                drive_file.get_cwd(),
                args.ls,
                drive_file.debug
            )
        elif args.find:
            path = canonicalize_path(
                drive_file.get_cwd(),
                args.find,
                drive_file.debug
            )
        else:
            path = drive_file.get_cwd()
        file_id = drive_file.resolve_path(path)
    else:
        if args.stat:
            file_id = args.stat
        elif args.ls:
            file_id = args.ls
        elif args.find:
            file_id = args.find
        else:
            file_id = drive_file.resolve_path(drive_file.get_cwd())

    if args.ls:
        handle_ls(drive_file, file_id, args.all)

    if args.find:
        handle_find(drive_file, file_id, args.all)

    if args.stat:
        handle_stat(drive_file, file_id, args.all)

    if args.showall:
        handle_show_all(drive_file, args.all)

    if args.status:
        handle_status(drive_file, args.all)

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
