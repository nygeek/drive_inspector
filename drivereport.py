""" Implementation of the DriveReport tools and utilities

Started 2018-05-28 by Marc Donner

Copyright (C) 2018 Marc Donner

This class and the test code in the main() function at the bottom
are written to provide the ability to generate straightforward tabular
reports from the Google Drive metadata that the DriveFile class provides.

"""

import sys

from drivefile import DriveFile
from drivefile import TestStats

reload(sys)
sys.setdefaultencoding('utf8')

APPLICATION_NAME = 'Drive Report'

class DriveReport(object):
    """Class to render tables of Google Drive object metadata."""

    def __init__(self, debug=False):
        self.debug = debug
        self.drive_file = DriveFile(self.debug)
        self.fields = self.drive_file.get_field_list()
        self.fields.append("path")
        self.render_list = []
        self.drive_file.load_cache()
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
            'path': self.drive_file.get_path,
            'shared': self.get_shared,
            'trashed': self.get_trashed,
            }

    def get_id(self, file_id):
        """Return the file_id.  Side effect is to ensure that
           the relevant metadata is in the cache.
           Returns: string
        """
        if self.debug:
            print "# get_id(file_id: " + str(file_id) + ")"
        metadata = self.drive_file.get(file_id)
        if self.debug:
            print "#    => " + str(metadata['id'])
        return metadata['id']

    def get_name(self, file_id):
        """Return the file name.
           Returns: string
        """
        if self.debug:
            print "# get_name(file_id: " + str(file_id) + ")"
        metadata = self.drive_file.get(file_id)
        if self.debug:
            print "#    => " + str(metadata['name'])
        return metadata['name']

    def get_parents(self, file_id):
        """Return paths to parents
           Returns: list of string
        """
        if self.debug:
            print "# get_parents(file_id: " + str(file_id) + ")"
        metadata = self.drive_file.get(file_id)
        # now get the path to each of the parents ...
        results = []
        for parent_id in metadata['parents']:
            results.append(self.drive_file.get_path(parent_id))
        if self.debug:
            print "#    => " + str(metadata['parents'])
            print "#    => " + results
        return ', '.join(results)
    
    def get_parent_count(self, file_id):
        """Return number of parents
           Returns: list of string
        """
        if self.debug:
            print "# get_parents(file_id: " + str(file_id) + ")"
        metadata = self.drive_file.get(file_id)
        # now get the path to each of the parents ...
        results = len(metadata['parents'])
        if self.debug:
            print "#    => " + str(metadata['parents'])
            print "#    => " + results
        return results
    
    def get_mimetype(self, file_id):
        """Return the mimeType
           Returns: string
        """
        if self.debug:
            print "# get_mimetype(file_id: " + str(file_id) + ")"
        metadata = self.drive_file.get(file_id)
        if self.debug:
            print "#    => " + str(metadata['mimeType'])
        return metadata['mimeType']

    def get_owners(self, file_id):
        """Return the list of owners
           Returns: list of strings
        """
        if self.debug:
            print "# get_owners(file_id: " + str(file_id) + ")"
        metadata = self.drive_file.get(file_id)
        # We will return a list of email addresses
        owner_list = []
        for owner in metadata['owners']:
            owner_list.append(owner['emailAddress'])
        results = ", ".join(owner_list)
        if self.debug:
            print "#    => " + str(metadata['owners'])
            print "#    => " + str(results)
        return results

    def get_trashed(self, file_id):
        """Return the trashed flag
           Returns: Boolean
        """
        if self.debug:
            print "# get_trashed(file_id: " + str(file_id) + ")"
        metadata = self.drive_file.get(file_id)
        if self.debug:
            print "#    => " + str(metadata['trashed'])
        return metadata['trashed']

    def get_modified_time(self, file_id):
        """Return the modifiedTime string
           Returns: string
        """
        if self.debug:
            print "# get_modified_time(file_id: " + str(file_id) + ")"
        metadata = self.drive_file.get(file_id)
        if self.debug:
            print "#    => " + str(metadata['modifiedTime'])
        return metadata['modifiedTime']

    def get_created_time(self, file_id):
        """Return the createdTime string
           Returns: string
        """
        if self.debug:
            print "# get_created_time(file_id: " + str(file_id) + ")"
        metadata = self.drive_file.get(file_id)
        if self.debug:
            print "#    => " + str(metadata['createdTime'])
        return metadata['createdTime']

    def get_ownedbyme(self, file_id):
        """Return the ownedByMe flag
           Returns: Boolean
        """
        if self.debug:
            print "# get_ownedbyme(file_id: " + str(file_id) + ")"
        metadata = self.drive_file.get(file_id)
        if self.debug:
            print "#    => " + str(metadata['ownedByMe'])
        return metadata['ownedByMe']

    def get_shared(self, file_id):
        """Return the shared flag
           Returns: Boolean
        """
        if self.debug:
            print "# get_shared(file_id: " + str(file_id) + ")"
        metadata = self.drive_file.get(file_id)
        if self.debug:
            print "#    => " + str(metadata['shared'])
        return metadata['shared']

    def set_render_fields(self, field_list):
        """Set the render field list.
           Returns: integer (length of render list)
        """
        self.render_list = field_list
        return len(self.render_list)

    def retrieve_item(self, file_id):
        """Given a FileID, render it.
           Returns: list of string
        """
        if self.debug:
            print "# render_item(" + str(file_id) + ")"
        result = []
        for field in self.render_list:
            if field in self.handlers.keys():
                result.append(self.handlers[field](file_id))
            else:
                result.append(field)
        if self.debug:
            print "#   =>" + str(result)
        return result

    def retrieve_items(self, fileid_list):
        """Given a list of FileIDs, render each one.
           Returns: list of list of string
        """
        if self.debug:
            print "# render_items(" + str(fileid_list) + ")"
        result = []
        for file_id in fileid_list:
            result.append(self.retrieve_item(file_id))
        if self.debug:
            print "#   =>" + str(result)
        return result

    def render_items_html(self, fileid_list):
        """Given a list of FileIDs, render each one as HTML.
           Returns: list of list of string
        """
        if self.debug:
            print "# render_items_html(" + str(fileid_list) + ")"
        result = ""
        result += "<table>\n"
        result += "<tr>"
        for field in self.render_list:
            result += "<th>" + field + "</th>"
        result += "</tr>\n"
        for file_id in fileid_list:
            result += "<tr>"
            for value in self.retrieve_item(file_id):
                result += "<td>" + str(value) + "</td>"
            result += "</tr>\n"
        result += "</table>\n"
        return result
    
    def render_items_tsv(self, fileid_list):
        """Given a list of FileIDs, render each one as TSV.
           Returns: list of list of string
        """
        if self.debug:
            print "# render_items_tsv(" + str(fileid_list) + ")"
        result = ""
        for field in self.render_list:
            result += field + "\t"
        result += "\n"
        for file_id in fileid_list:
            for value in self.retrieve_item(file_id):
                result += str(value) + "\t"
            result += "\n"
        return result
    
    def __str__(self):
        result = "DriveReport:\n"
        result += "debug: " + str(self.debug) + "\n"
        result += "fields: " + str(self.fields) + "\n"
        result += "drive_file: " + str(self.drive_file) + "\n"
        return result

def main():
    """Test code."""

    test_stats = TestStats()
    test_stats.print_startup()

    drive_report = DriveReport(False)
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

    cwd_fileid = drive_report.drive_file.resolve_path(
        drive_report.drive_file.get_cwd())
    print "cwd_fileid: " + str(cwd_fileid)
    fileid_list = drive_report.drive_file.list_all_children(cwd_fileid, True)
    # print "# fileid_list: " + str(fileid_list)
    print drive_report.render_items_tsv(fileid_list)
    # print drive_report.render_items_html(fileid_list)

    # print str(drive_report)

    test_stats.print_final_report()


if __name__ == '__main__':
    main()
