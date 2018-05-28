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

    def __init__(self, debug):
        self.debug = debug
        self.drive_file = DriveFile(self.debug)
        self.fields = self.drive_file.get_field_list()
        self.drive_file.load_cache()

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

    drive_report = DriveReport(True)
    print str(drive_report)

    test_stats.print_final_report()


if __name__ == '__main__':
    main()
