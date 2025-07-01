#!./bin/python3
""" Implementation of the DriveReport tools and utilities

Started 2018-05-28 by Marc Donner
Forked from drivereport.py on 2025-06-28

Copyright (C) 2018-2025 Marc Donner

This class and the test code in the main() function at the bottom
are written to provide the ability to generate straightforward tabular
reports from the Google Drive metadata that the DriveFile class provides.

"""

# To do:
# [ ] 2025-06-28 When a tab is found in a value, escape it so it does
#     not screw up TSV output
# [ ] 2025-06-28 Add a JSON output format, in addition to HTML and TSV

# import sys
import argparse
import datetime

from drivefilecached import canonicalize_path
from drivefilecached import DriveFileCached
from drivefileraw import TestStats
from drivefileraw import handle_status

# These two break in Python 3 and may not be needed anyway
# reload(sys)
# sys.setdefaultencoding('utf8')

APPLICATION_NAME = 'Drive Report'

class DriveReport(DriveFileCached):
    """Class to render tables of Google Drive object metadata."""

    def __init__(self, debug=False):
        self.render_list = []
        self.handlers = {
            'createdTime': self.get_created_time,
            'id': self.get_id,
            'mimeType': self.get_mimetype,
            'modifiedTime': self.get_modified_time,
            'name': self.get_name,
            'ownedByMe': self.get_ownedbyme,
            'owners': self.get_owners,
            'parents': self.get_parents,
            'parentCount': self.get_parent_count,
            'path': self.get_path,
            'shared': self.get_shared,
            'size': self.get_size,
            'trashed': self.get_trashed,
            }
        super().__init__(debug)
        self.format = "HTML";
        self.fields = self.df_field_list()
        self.fields.append("path")

    def get_id(self, node_id):
        """Return the node_id.  Side effect is to ensure that
           the relevant metadata is in the cache.
           Returns: node_id
        """
        if self.debug:
            print("# get_id(node_id: " + str(node_id) + ")")
        node = self.get(node_id)
        if self.debug:
            print("#    => " + str(node['id']))
        return node['id']

    def get_name(self, node_id):
        """Return the file name.
           Returns: string
        """
        if self.debug:
            print("# get_name(node_id: " + str(node_id) + ")")
        node = self.get(node_id)
        if self.debug:
            print("#    => " + str(node['name']))
        return node['name']

    def get_parents(self, node_id):
        """Return paths to parents
           Returns: string (comma-delimited list of parent paths)
        """
        if self.debug:
            print("# get_parents(node_id: " + str(node_id) + ")")
        node = self.get(node_id)
        # now get the path to each of the parents ...
        results = [self.get_path(parent_id) for parent_id in node['parents']] \
                  if 'parents' in node else []
        if self.debug:
            print("#    => " + str(results))
        return ', '.join(results)

    def get_parent_count(self, node_id):
        """Return number of parents
           Returns: integer
        """
        if self.debug:
            print("# get_parents(node_id: " + str(node_id) + ")")
        node = self.get(node_id)
        # now get the path to each of the parents ...
        results = len(node['parents']) if 'parents' in node else 0
        if self.debug:
            print("#    => " + str(results))
        return results

    def get_size(self, node_id):
        """Return size in bytes of file
           Returns: integer
        """
        if self.debug:
            print("# get_size(node_id: " + str(node_id) + ")")
        node = self.get(node_id)
        if 'size' in node:
            result = node['size']
        else:
            result = 0
        if self.debug:
            print("#    => " + str(result))

    def get_mimetype(self, node_id):
        """Return the mimeType
           Returns: string
        """
        if self.debug:
            print("# get_mimetype(node_id: " + str(node_id) + ")")
        node = self.get(node_id)
        if self.debug:
            print("#    => " + str(node['mimeType']))
        return node['mimeType']

    def get_owners(self, node_id):
        """Return the list of owners
           Returns: comma-delimited list of owner email addresses
        """
        if self.debug:
            print("# get_owners(node_id: " + str(node_id) + ")")
        node = self.get(node_id)
        # We will return a list of email addresses
        owner_list = [owner['emailAddress'] for owner in node['owners']] \
                     if 'owners' in node else []
        results = ", ".join(owner_list)
        if self.debug:
            print("#    => " + str(node['owners']))
            print("#    => " + str(results))
        return results

    def get_trashed(self, node_id):
        """Return the trashed flag
           Returns: Boolean
        """
        if self.debug:
            print("# get_trashed(node_id: " + str(node_id) + ")")
        node = self.get(node_id)
        if self.debug:
            print("#    => " + str(node['trashed']))
        return node['trashed']

    def get_modified_time(self, file_id):
        """Return the modifiedTime string
           Returns: string
        """
        if self.debug:
            print("# get_modified_time(file_id: " + str(file_id) + ")")
        node = self.get(file_id)
        if self.debug:
            print("#    => " + str(node['modifiedTime']))
        return node['modifiedTime']

    def get_created_time(self, node_id):
        """Return the createdTime string
           Returns: string
        """
        if self.debug:
            print("# get_created_time(node_id: " + str(node_id) + ")")
        node = self.get(node_id)
        if self.debug:
            print("#    => " + str(node['createdTime']))
        return node['createdTime']

    def get_ownedbyme(self, node_id):
        """Return the ownedByMe flag
           Returns: Boolean
        """
        if self.debug:
            print("# get_ownedbyme(node_id: " + str(node_id) + ")")
        node = self.get(node_id)
        if self.debug:
            print("#    => " + str(node['ownedByMe']))
        return node['ownedByMe']

    def get_shared(self, node_id):
        """Return the shared flag
           Returns: Boolean
        """
        if self.debug:
            print("# get_shared(node_id: " + str(node_id) + ")")
        node = self.get(node_id)
        if self.debug:
            print("#    => " + str(node['shared']))
        return node['shared']

    def set_render_fields(self, field_list):
        """Set the render field list.
           Returns: integer (length of render list)
        """
        self.render_list = field_list
        return len(self.render_list)

    def retrieve_item(self, node_id):
        """Given a node_id, retrieve the render fields for it.
           Returns: list of strings
        """
        if self.debug:
            print("# retrieve_item(" + str(node_id) + ")")
        result = []
        for field in self.render_list:
            if field in self.handlers:
                result.append(self.handlers[field](node_id))
            else:
                result.append(field)
        if self.debug:
            print("#   =>" + str(result))
        return result

    def retrieve_items(self, node_id_list):
        """Given a list of node_ids, retrieve the render fields
           for each one.
           Returns: list of list of strings
        """
        if self.debug:
            print("# render_items(" + str(len(node_id_list)) + ")")
        result = []
        for node_id in node_id_list:
            result.append(self.retrieve_item(node_id))
        if self.debug:
            print("#   =>" + str(result))
        return result

    def render_items_html(self, node_id_list):
        """Given a list of FileIDs, render each one as HTML.
           Returns: list of list of string
        """
        # should make this an iterator!
        if self.debug:
            print("# render_items_html(len: " \
                    + str(len(node_id_list)) + ")")
        result = ""
        result += "<table>\n"
        result += "<tr>"
        for field in self.render_list:
            result += "<th>" + field + "</th>"
        result += "</tr>\n"
        for node_id in node_id_list:
            result += "<tr>"
            for value in self.retrieve_item(node_id):
                result += "<td>" + str(value) + "</td>"
            result += "</tr>\n"
        result += "</table>\n"
        return result

    def render_items_tsv(self, node_id_list):
        """Given a list of node_ids, render each one as TSV.
           Returns: list of list of string
        """
        if self.debug:
            print("# render_items_tsv(len: " + str(len(node_id_list)) + ")")
        result = ""
        for field in self.render_list:
            result += field + "\t"
        result += "\n"
        for node_id in node_id_list:
            for value in self.retrieve_item(node_id):
                result += str(value) + "\t"
            result += "\n"
        return result

    def __str__(self):
        result = "DriveReport:\n"
        result += "debug: " + str(self.debug) + "\n"
        result += "fields: " + str(self.fields) + "\n"
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
        '--cd',
        type=str,
        help='Change the working directory.'
        )
    parser.add_argument(
        '-f',
        action='store_true',
        help='(Modifier)  Argument to cd will be a NodeID instead of a path.'
        )
    parser.add_argument(
        '--html',
        type=str,
        help='Generate HTML output.'
        )
    parser.add_argument(
        '--json',
        type=str,
        help='Generate JSON output.'
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
        help='(Modifier) Update the cache.  For use with the --newer operator.'
        )
    parser.add_argument(
        '--showall',
        action='store_true',
        help="Show all files in My Drive."
        )
    parser.add_argument(
        '--status',
        action='store_true',
        help="Display the status of the DriveFile object."
        )
    parser.add_argument(
        '--tsv',
        type=str,
        help='Generate TSV output.'
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


    def df_status(self):
        """Get status of DriveFile instance.
           Returns: List of String
        """
        if self.debug:
            print("# df_status()")
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


def do_work():
    """Parse arguments and handle them."""

    parser = setup_parser()
    args = parser.parse_args()

    teststats = TestStats()
    startup_report = teststats.report_startup()

    # Do the work ...

    # set the DEBUG flag if desired.
    drive_file = DriveFileCached(True) if args.DEBUG \
                else DriveFileCached(False)
    drive_report = DriveReport(True) if args.DEBUG \
                else DriveReport(False)
    drive_report.init_cache()

    # at this point we have drive_file, drive_report, and parser, 
    # so now we can set up a run

    # Establish the output destination
    _ = drive_file.df_set_output(args.output) if args.output else "stdout"
    drive_file.df_print(startup_report)
    print("# output going to: " + drive_file.output_path)

    # Now start doing the work.
    # First do things that do *not* require scanning the drive tree

    # drive_report.df_set_output("./dr_output.tsv")
    # drive_report.df_set_output("./dr_output.html")

    drive_report.df_print(startup_report)

    drive_report.set_render_fields(
        [
            'id',
            'name',
            'path',
            'mimeType',
            'size',
            'owners',
            'createdTime',
            'shared',
            'ownedByMe',
            'parents',
            'parentCount',
        ]
    )

    if args.tsv:
        drive_report.format = "TSV"
    # JSON output is not actually handled yet
    if args.json:
        drive_report.format = "JSON"

    # Either start with the existing cwd, or switch to the --cd argument
    if args.cd:
        print("args.cd: " + args.cd)
        cd_path = canonicalize_path(
                drive_file.get_cwd(),
                args.cd,
                drive_file.debug)
        print("cd_path: " + cd_path)
        cd_node_id = drive_file.resolve_path(cd_path)
        drive_file.set_cwd(cd_node_id)
    cwd = drive_report.get_cwd()
    cwd_node_id = drive_report.resolve_path(cwd)

    drive_report.df_print("# cwd: " + str(cwd) + "\n")
    drive_report.df_print("# cwd_fileid: " + str(cwd_node_id) + "\n")

    _ = drive_file.init_cache() if args.nocache else drive_file.load_cache()

    if args.status:
        result = drive_file.df_status()
        for _ in result:
            drive_file.df_print(_)
        exit()

    node_id_list = [node['id'] for node in drive_report.list_all()]

    print("# len(node_id_list): " + str(len(node_id_list)))
    if drive_report.format == "TSV":
        drive_report.df_print(drive_report.render_items_tsv(node_id_list))
    elif drive_report.format == "JSON":
        # JSON is not handled yet
        drive_report.render_items_tsv(node_id_list)
    else:
        drive_report.render_items_HTML(node_id_list)

    # Done with the work

    drive_file.df_print("# call_count: " + '\n')
    for call_type, count in drive_file.call_count.items():
        drive_file.df_print("#    " + call_type + ": " + str(count) + '\n')

    if not args.Z:
        drive_file.dump_cache()
    else:
        print("# skip writing cache.")

    wrapup_report = teststats.report_wrapup()
    drive_report.df_print(wrapup_report)


def main():
    """ Main """

    do_work()


if __name__ == '__main__':
    main()
