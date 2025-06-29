#!./bin/python3
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
# import sys
import time

from drivefileraw import DriveFileRaw
from drivefileraw import handle_find
from drivefileraw import handle_ls
from drivefileraw import handle_newer
from drivefileraw import handle_showall
from drivefileraw import handle_stat
from drivefileraw import handle_status
from drivefileraw import pretty_json
from drivefileraw import TestStats

# These two break under Python 3 ... and they may not be needed
# reload(sys)
# sys.setdefaultencoding('utf8')

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

    # Since we construct cwd from a node_id now, it always ends in /,
    # so trim off the last empty string in cwd_parts
    cwd_parts = cwd.split('/')[:-1]
    path_parts = path.split('/')

    new = path_parts if path and path[0] == '/' else cwd_parts + path_parts

    if debug:
        print("# canonicalize_path(cwd: '" + cwd \
            + "', path: '" + path + "')")
        print("#   cwd_parts: " + str(cwd_parts))
        print("#   path_parts: " + str(path_parts))
        print("# new: '" + str(new) + "'")

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
        print("# new: '" + str(new) + "'")
        print("new_path: '" + new_path + "'")
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
        # super(DriveFileCached, self).__init__(debug)
        super().__init__(debug)

    def df_status(self):
        """Get status of DriveFileCached instance.
           Returns: List of String
        """
        if self.debug:
            print("# df_status()")
        # result = super(DriveFileCached, self).df_status()
        result = super().df_status()
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

    def get(self, node_id):
        """Get the node for node_id.
           Returns: node
        """
        if self.debug:
            print("# get(node_id: " + node_id + ")")

        # If node_id is not in the cache, go to Raw to get it
        if node_id not in self.file_data['metadata']:
            if self.debug:
                print("# calling Google ...")
            t_start = time.time()
#            node = super(DriveFileCached, self).get(node_id)
            node = super().get(node_id)
            self.file_data['time'][node_id] = time.time() - t_start
            self.__register_node([node])
            if node_id == "root":
                # very special case!
                self.file_data['metadata'][node_id] = node
                self.file_data['ref_count'][node_id] = 1
                self.get_path(node_id)

        # OK, now node_id is in the cache (or node_id is bogus)
        return self.file_data['metadata'][node_id]

    def get_path(self, node_id):
        """Given a node_id, construct the path back to root.
           Returns: string
        """
        if self.debug:
            print("# get_path(" + node_id + ")")

        if node_id in self.file_data['path']:
            result = self.file_data['path'][node_id]
        else:
            # If we got here, then the path is not cached
            node = self.file_data['metadata'][node_id] \
                   if node_id in self.file_data['metadata'] \
                   else self.get(node_id)

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
                self.file_data['path']["root"] = "/"
                self.file_data['dirty'] = True
                result = ""
            else:
                # Recursion ... upward!
                new_path = self.get_path(parent) + node_name
                self.file_data['path'][node_id] = \
                    new_path + '/' if self.__is_folder(node) else new_path
                result = self.file_data['path'][node_id]

        if self.debug:
            print("#    => " + result)
        return result

    def __register_node(self, node_list):
        """Accept a list of node and register them in
           self.file_data.
           Returns: array of node_id
        """
        if self.debug:
            print("# __register_node(len: " \
                    + str(len(node_list)) + ")")

        # Now comb through and put everything in file_data.
        i = 0
        results = []
        for node in node_list:
            node_id = node['id']
            node_name = node['name']
            if self.debug:
                print("#    __register_node: i: " + str(i) \
                      + " (" + node_id + ") '" + node_name + "'")
            if node_id not in self.file_data['metadata']:
                if self.debug:
                    print("#    __register_node: adding " + node_id)
                self.file_data['metadata'][node_id] = node
                self.file_data['dirty'] = True
                self.file_data['ref_count'][node_id] = 1
                self.get_path(node_id)
            results.append(node_id)
            i += 1

        if self.debug:
            print("# __register_node results: " + str(len(results)))

        return results

    def resolve_path(self, path):
        """Given a path, find and return the FileID matching the
           terminal node.  Like the namei() syscall in Unix.
           Returns: FileID
        """
        if self.debug:
            print("# resolve_path(" + str(path) + ")")

        if path in self.file_data['path'].values():
            # for node_id, test_path in self.file_data['path'].iteritems():
            # dict.iteritems() in Pyton 2 becomes dict.items() in Python 3
            for node_id, test_path in self.file_data['path'].items():
                if test_path == path:
                    return node_id

        # This is disgusting tech debt.  Got to handle the trailing '/'
        # better.  TODO
        if path + '/' in self.file_data['path'].values():
            # for node_id, test_path in self.file_data['path'].iteritems():
            # dict.iteritems() in Python 2 becomes dict.items() in Python 3
            for node_id, test_path in self.file_data['path'].items():
                if test_path == path + '/':
                    return node_id

        path_components = path.split("/")
        # this pop drops the leading empty string
        path_components.pop(0)
        if self.debug:
            print("#    path_components: " + str(path_components))

        node_id = self.get("root")['id']
        for component in path_components:
            # if the component is a '.' (current directory) then skip it
            if component != ".":
                node = self.__get_named_child(node_id, component)
                if node in ["<not_found>", "<error"]:
                    print("# resolve_path(" + path + ") => not found.")
                    return node
                node_id = node["id"]
                if self.debug:
                    print("# " + component + " => (" + node_id + ")")
        return node_id

    def __get_named_child(self, node_id, component):
        """ Given a node_id (folder) and a component name, find the
            matching child, if it exists.
            Returns: node
            Returns: <not_found> if there is no child by that name
        """
        if self.debug:
            print("# __get_named_child[cached](node_id:" \
                + str(node_id) + ", " + component + ")")

        children = self.list_children(node_id)
        results = [item for item in children \
            if ( \
                'parents' in item \
                and node_id in item['parents'] \
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
            print("#    __get_named_child[cached] => " \
                + str(pretty_json(response)))
        return response

    def __is_folder(self, node):
        """Test whether node represents a folder.
           Returns: Boolean
        """
        node_id = node['id']
        if self.debug:
            print("# __is_folder(node_id: " + node_id + ")")
        result = node['mimeType'] == self.FOLDERMIMETYPE \
                 and ("fileExtension" not in node)
        if self.debug:
            # print("# node: " + pretty_json(node))
            print("#    => " + str(result))
        return result

    def list_children(self, node_id):
        """Get the children of node_id.
           Returns: array of node
        """
        if self.debug:
            print("# list_children[cached](node_id: " + node_id + ")")

        # Are there children of node_id in the cache?

        children = [self.file_data['metadata'][item] \
            for item in self.file_data['metadata'] \
                if ('parents' in self.file_data['metadata'][item] \
                    and node_id \
                    in self.file_data['metadata'][item]['parents'])]

        if not children:
#            children = super(DriveFileCached, self).list_children(node_id)
            children = super().list_children(node_id)
            self.__register_node(children)

        if self.debug:
            print("#    children: " + str(len(children)))
        return children

    def list_all(self):
        """Get all of the files to which I have access.
           Returns: list of node
        """
        if self.debug:
            print("# list_all[cached]()")

#        node_list = super(DriveFileCached, self).list_all()
        node_list = super().list_all()

        if node_list:
            self.__register_node(node_list)

        if self.debug:
            print("# list_all node_list[cached]: " + str(len(node_list)))

        return node_list

    def list_newer(self, date):
        """Find nodes that are modified more recently that
           the provided date.
           Returns: list of node
        """
        if self.debug:
            print("# list_newer[cached](date: " + str(date) + ")")
#        results = super(DriveFileCached, self).list_newer(date)
        results = super().list_newer(date)

        return results

    def show_newer(self, date, refresh):
        """ Display paths to all nodes newer than a given date. """
        if self.debug:
            print("# show_newer[cached](")
            print("#    date: '" + str(date) + "'")
            print("#    refresh: '" + str(refresh) + "'")
            print("# )")
        newer_nodes = self.list_newer(date)
        if refresh:
            self.__register_node(newer_nodes)
        for node in newer_nodes:
            node_id = node['id']
            path = self.get_path(node_id)
            self.df_print(str(path) + '\n')

    def show_node(self, node_id):
        """ Display a node."""
        if self.debug:
            print("# show_node[cached](node_id: (" + node_id + "))")
        self.df_print(pretty_json(self.get(node_id)))

    def show_children(self, node_id):
        """ Display the names of the children of a node.
            This is the core engine of the --ls function.
        """
        if self.debug:
            print("# show_children[cached](node_id: (" \
                + str(node_id) + "))")
        children = self.list_children(node_id)
        if self.debug:
            print("# show_children[cached]: len(children): " \
                + str(len(children)))
        for child in children:
            child_id = child['id']
            if self.debug:
                print("# child_id: " + str(child_id))
            child_name = child['name']
            if self.__is_folder(child):
                child_name += "/"
            self.df_print(child_name + '\n')

    def list_all_children(self, node_id, show_all=False):
        """Return the list of FileIDs beneath a given node.
           Return: list of node
        """
        if self.debug:
            print("# list_all_children[cached](" \
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

    def show_all_children(self, node_id, show_all=False):
        """ Display all child directories of a node
            show_all:
                True: display all files.
                False: show just the folder structure.
        """
        if self.debug:
            print("# show_all_children[cached](node_id: (" + node_id + "))")
            print("#    show_all: " + str(show_all))

        children = self.list_all_children(node_id, show_all)

        num_files = 0
        num_folders = 0

        for child in children:
            child_id = child['id']
            child_name = child['name']
            num_files += 1
            if self.debug:
                print("#    child_id: (" + child_id + ") '" \
                      + child_name + "'")
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
            print("# show_all[cached]()")

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
            self.df_print(self.get_path(node_id) + '\n')
        self.df_print("#    num_folders: " + str(num_folders) + '\n')
        self.df_print("#    num_files: " + str(num_files) + '\n')

    def set_cwd(self, node_id):
        """Set the current working directory string
           Returns: nothing
        """
        if self.debug:
            print("# set_cwd: " + node_id)
        path = self.get_path(node_id)
        self.file_data['cwd'] = path
        self.file_data['dirty'] = True
        if self.debug:
            print("#    => " + path)

    def get_cwd(self):
        """Return the value of the current working directory
           Returns: string
        """
        if self.debug:
            print("# get_cwd => " + self.file_data['cwd'])
        return self.file_data['cwd']

    def load_cache(self):
        """Load the cache from stable storage."""
        if self.debug:
            print("# load_cache: " + str(self.cache['path']))
        try:
            mtime = os.path.getmtime(self.cache['path'])
            self.cache['mtime'] = \
                datetime.datetime.utcfromtimestamp(mtime).isoformat()
                # datetime.datetime.fromtimestamp(timestamp, datetime.UTC).
                # datetime.datetime.utcfromtimestamp(mtime).isoformat()

        except OSError as error:
            print("# OSError: " + str(error))
            self.init_cache()
            return
        try:
            with open(self.cache['path'], "r", encoding="utf-8") as cache_file:
                self.file_data = json.load(cache_file)
                for node_id in self.file_data['metadata'].keys():
                    self.file_data['ref_count'][node_id] = 0
                print("# Loaded " + str(len(self.file_data['metadata'])) \
                      + " cached nodes.")
                self.file_data['dirty'] = False
        except IOError as error:
            print("# Starting with empty cache. IOError: " + str(error))
            self.init_cache()

    def init_cache(self):
        """Initialize the self.file_data cache['metadata']."""
        if self.debug:
            print("# init_cache()")
        self.file_data['metadata'] = {}
        self.file_data['metadata']['<none>'] = {}
        self.file_data['dirty'] = False

    def dump_cache(self):
        """Write the cache out to a file. """
        if self.file_data['dirty']:
            try:
                with open(self.cache['path'], "w", encoding="utf-8") \
                     as cache_file:
                    json.dump(
                        self.file_data,
                        cache_file, indent=3,
                        separators=(',', ': ')
                    )
                print("# Wrote " \
                    + str(len(self.file_data['metadata'])) \
                    + " nodes to " + self.cache['path'] + ".")
            except IOError as error:
                print("IOError: " + str(error))
        else:
            print("Cache clean, not rewritten.")

    def set_debug(self, debug):
        """Set the debug flag."""
        if self.debug:
            print("set_debug[cached](" + str(debug) + ")")
        self.debug = debug
        if self.debug:
            print("set_debug => debug:" + str(self.debug))
        return self.debug

    def get_debug(self):
        """Return the debug flag."""
        if self.debug:
            print("# get_debug[cached] => debug:" + str(self.debug))
        return self.debug

    def __str__(self):
        if self.STRMODE == 'full':
            result = pretty_json(self.file_data)
        else:
            result = "cwd: " + self.file_data['cwd'] + "\n"
            for node_id in self.file_data['metadata']:
                result += "(" + node_id + "):\n"
                result += pretty_json(
                    self.file_data['metadata'][node_id]) + "\n"
                if node_id in self.file_data['time']:
                    result += "time: " \
                        + str(self.file_data['time'][node_id]) + "\n"
                result += "path: " \
                    + self.file_data['path'][node_id] + "\n"
                result += "refs: " + \
                    str(self.file_data['ref_count'][node_id]) + "\n"
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
        help='(Modifier)  When running a find, show all nodes.'
        )
    parser.add_argument(
        '--cd',
        type=str,
        help='Change the working directory.'
        )
    parser.add_argument(
        '--dirty',
        action='store_true',
        help='List all nodes that have been modified since the cache file was written.'
        )
    parser.add_argument(
        '-f',
        action='store_true',
        help='(Modifier)  Argument to stat, ls, find will be a NodeID instead of a path.'
        )
    parser.add_argument(
        '--find',
        type=str,
        help='Given a node, recursively list all subfolders (and contents if -a).'
        )
    parser.add_argument(
        '--ls',
        type=str,
        help='List a node or, if it represents a folder, the nodes in it.'
        )
    parser.add_argument(
        '--newer',
        type=str,
        help='List all nodes modified since the specified date.'
        )
    parser.add_argument(
        '-n', '--nocache',
        action='store_true',
        help='(Modifier)  Skip loading the cache.'
        )
    parser.add_argument(
        '--output', '-o',
        type=str,
        help='Send the output to the specified local file.'
        )
    parser.add_argument(
        '-R', '--refresh',
        action='store_true',
        help='(Modifier) Update the cache.  For use with the --newer and --dirty operators.'
        )
    parser.add_argument(
        '--showall',
        action='store_true',
        help="Show all files in My Drive."
        )
    parser.add_argument(
        '--stat',
        type=str,
        help="Pretty print the JSON metadata for a node."
        )
    parser.add_argument(
        '--status',
        action='store_true',
        help="Display the status of the DriveFile object."
        )
    parser.add_argument(
        '-D', '--DEBUG',
        action='store_true',
        help='(Modifier) Turn on debugging output.'
        )
    parser.add_argument(
        '-z', '--Z',
        action='store_true',
        help='(Modifier) Do not rewrite the cache file on exiting.'
        )
    return parser


def do_work(teststats):
    """Parse arguments and handle them."""

    startup_report = teststats.report_startup()

    parser = setup_parser()
    args = parser.parse_args()

    # Do the work ...

    drive_file = DriveFileCached(True) if args.DEBUG \
                 else DriveFileCached(False)

    _ = drive_file.df_set_output(args.output) if args.output else "stdout"
    drive_file.df_print(startup_report)

    print("# output going to: " + drive_file.output_path)

    _ = drive_file.init_cache() if args.nocache else drive_file.load_cache()

    if args.cd:
        drive_file.set_cwd(args.cd)
        drive_file.df_print("# pwd: " + drive_file.get_cwd() + '\n')

    path = canonicalize_path(
        drive_file.get_cwd(),
        args.stat,
        drive_file.debug
        ) if args.stat and not args.f else drive_file.get_cwd()

    path = canonicalize_path(
        drive_file.get_cwd(),
        args.ls,
        drive_file.debug
        ) if args.ls and not args.f else path

    path = canonicalize_path(
        drive_file.get_cwd(),
        args.find,
        drive_file.debug
        ) if args.find and not args.f else path

    node_id = drive_file.resolve_path(path)

    node_id = args.stat if args.stat and args.f else node_id
    node_id = args.ls if args.ls and args.f else node_id
    node_id = args.find if args.find and args.f else node_id

    _ = handle_newer(drive_file, drive_file.cache['mtime'], args.refresh) \
            if args.dirty else False

    _ = handle_find(drive_file, node_id, args.all) if args.find else False

    _ = handle_ls(drive_file, node_id, args.all) if args.ls else False

    _ = handle_newer(drive_file, args.newer, args.refresh) if args.newer else False

    _ = handle_showall(drive_file, args.all) if args.showall else False

    _ = handle_stat(drive_file, node_id, args.all) if args.stat else False

    _ = handle_status(drive_file, args.status, args.all) if args.status else False

    # Done with the work

    drive_file.df_print("# call_count: " + '\n')
    for call_type, count in drive_file.call_count.items():
        drive_file.df_print("#    " + call_type + ": " + str(count) + '\n')

    if not args.Z:
        drive_file.dump_cache()
    else:
        print("# skip writing cache.")

    wrapup_report = teststats.report_wrapup()
    drive_file.df_print(wrapup_report)


def main():
    """Test code and basic CLI functionality engine."""
    test_stats = TestStats()
    do_work(test_stats)


if __name__ == '__main__':
    main()
