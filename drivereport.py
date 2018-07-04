""" Implementation of the DriveReport tools and utilities

Started 2018-05-28 by Marc Donner

Copyright (C) 2018 Marc Donner

This class and the test code in the main() function at the bottom
are written to provide the ability to generate straightforward tabular
reports from the Google Drive metadata that the DriveFile class provides.

"""

import sys

from drivefilecached import DriveFileCached
from drivefileraw import TestStats

reload(sys)
sys.setdefaultencoding('utf8')

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
            'trashed': self.get_trashed,
            }
        super(DriveReport, self).__init__(debug)
        self.fields = self.df_field_list()
        self.fields.append("path")

    def get_id(self, node_id):
        """Return the node_id.  Side effect is to ensure that
           the relevant metadata is in the cache.
           Returns: node_id
        """
        if self.debug:
            print "# get_id(node_id: " + str(node_id) + ")"
        node = self.get(node_id)
        if self.debug:
            print "#    => " + str(node['id'])
        return node['id']

    def get_name(self, node_id):
        """Return the file name.
           Returns: string
        """
        if self.debug:
            print "# get_name(node_id: " + str(node_id) + ")"
        node = self.get(node_id)
        if self.debug:
            print "#    => " + str(node['name'])
        return node['name']

    def get_parents(self, node_id):
        """Return paths to parents
           Returns: string (comma-delimited list of parent paths)
        """
        if self.debug:
            print "# get_parents(node_id: " + str(node_id) + ")"
        node = self.get(node_id)
        # now get the path to each of the parents ...
        results = [self.get_path(parent_id) for parent_id in node['parents']] \
                  if 'parents' in node else []
        if self.debug:
            print "#    => " + str(results)
        return ', '.join(results)

    def get_parent_count(self, node_id):
        """Return number of parents
           Returns: integer
        """
        if self.debug:
            print "# get_parents(node_id: " + str(node_id) + ")"
        node = self.get(node_id)
        # now get the path to each of the parents ...
        results = len(node['parents']) if 'parents' in node else 0
        if self.debug:
            print "#    => " + str(results)
        return results

    def get_mimetype(self, node_id):
        """Return the mimeType
           Returns: string
        """
        if self.debug:
            print "# get_mimetype(node_id: " + str(node_id) + ")"
        node = self.get(node_id)
        if self.debug:
            print "#    => " + str(node['mimeType'])
        return node['mimeType']

    def get_owners(self, node_id):
        """Return the list of owners
           Returns: comma-delimited list of owner email addresses
        """
        if self.debug:
            print "# get_owners(node_id: " + str(node_id) + ")"
        node = self.get(node_id)
        # We will return a list of email addresses
        owner_list = [owner['emailAddress'] for owner in node['owners']] \
                     if 'owners' in node else []
        results = ", ".join(owner_list)
        if self.debug:
            print "#    => " + str(node['owners'])
            print "#    => " + str(results)
        return results

    def get_trashed(self, node_id):
        """Return the trashed flag
           Returns: Boolean
        """
        if self.debug:
            print "# get_trashed(node_id: " + str(node_id) + ")"
        node = self.get(node_id)
        if self.debug:
            print "#    => " + str(node['trashed'])
        return node['trashed']

    def get_modified_time(self, file_id):
        """Return the modifiedTime string
           Returns: string
        """
        if self.debug:
            print "# get_modified_time(file_id: " + str(file_id) + ")"
        node = self.get(file_id)
        if self.debug:
            print "#    => " + str(node['modifiedTime'])
        return node['modifiedTime']

    def get_created_time(self, node_id):
        """Return the createdTime string
           Returns: string
        """
        if self.debug:
            print "# get_created_time(node_id: " + str(node_id) + ")"
        node = self.get(node_id)
        if self.debug:
            print "#    => " + str(node['createdTime'])
        return node['createdTime']

    def get_ownedbyme(self, node_id):
        """Return the ownedByMe flag
           Returns: Boolean
        """
        if self.debug:
            print "# get_ownedbyme(node_id: " + str(node_id) + ")"
        node = self.get(node_id)
        if self.debug:
            print "#    => " + str(node['ownedByMe'])
        return node['ownedByMe']

    def get_shared(self, node_id):
        """Return the shared flag
           Returns: Boolean
        """
        if self.debug:
            print "# get_shared(node_id: " + str(node_id) + ")"
        node = self.get(node_id)
        if self.debug:
            print "#    => " + str(node['shared'])
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
            print "# retrieve_item(" + str(node_id) + ")"
        result = []
        for field in self.render_list:
            if field in self.handlers.keys():
                result.append(self.handlers[field](node_id))
            else:
                result.append(field)
        if self.debug:
            print "#   =>" + str(result)
        return result

    def retrieve_items(self, node_id_list):
        """Given a list of node_ids, retrieve the render fields for each one.
           Returns: list of list of strings
        """
        if self.debug:
            print "# render_items(" + str(len(node_id_list)) + ")"
        result = []
        for node_id in node_id_list:
            result.append(self.retrieve_item(node_id))
        if self.debug:
            print "#   =>" + str(result)
        return result

    def render_items_html(self, node_id_list):
        """Given a list of FileIDs, render each one as HTML.
           Returns: list of list of string
        """
        # should make this an iterator!
        if self.debug:
            print "# render_items_html(len: " + str(len(node_id_list)) + ")"
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
            print "# render_items_tsv(len: " + str(len(node_id_list)) + ")"
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

def main():
    """Test code."""

    teststats = TestStats()
    startup_report = teststats.report_startup()

    drive_report = DriveReport(False)
    drive_report.init_cache()

    # Pick either TSV or HTML here and further down
    # drive_report.df_set_output("./dr_output.tsv")
    drive_report.df_set_output("./dr_output.html")

    drive_report.df_print(startup_report)

    drive_report.set_render_fields(
        [
            'id',
            'name',
            'path',
            'mimeType',
            'owners',
            'createdTime',
            'shared',
            'ownedByMe',
            'parents',
            'parentCount',
        ]
    )

    cwd = drive_report.get_cwd()
    cwd_node_id = drive_report.resolve_path(cwd)

    drive_report.df_print("# cwd: " + str(cwd))
    drive_report.df_print("# cwd_fileid: " + str(cwd_node_id))

    node_id_list = [node['id'] for node in drive_report.list_all()]

    print "# len(node_id_list): " + str(len(node_id_list))

    drive_report.df_print(
        # Pick either TSV or HTML here and above
        # drive_report.render_items_tsv(node_id_list))
        drive_report.render_items_html(node_id_list))

    wrapup_report = teststats.report_wrapup()
    drive_report.df_print(wrapup_report)


if __name__ == '__main__':
    main()
