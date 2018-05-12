""" Implementation of the interactive DriveInspector using the DriveFile
    class implemented in drivefile.py

Started 2018-05-12 by Marc Donner

Copyright (C) 2018 Marc Donner

"""

import argparse
import json
import os
import sys
import time

import psutil
import httplib2

from drivefile import DriveFile

reload(sys)
sys.setdefaultencoding('utf8')

APPLICATION_NAME = 'Drive Shell'

class TestStats(object):
    """Organize and display stats for the running of the program."""

    def __init__(self):
        self.cpu_time_0 = psutil.cpu_times()
        self.iso_time_stamp = \
            time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
        self.program_name = sys.argv[0]

    def print_startup(self):
        """Display start-of-run information."""
        print
        print "# program_name: " + self.program_name
        print "# iso_time_stamp: " + self.iso_time_stamp
        print

    def print_final_report(self):
        """Print the final report form the test run."""
        cpu_time_1 = psutil.cpu_times()
        print
        print "# " + self.program_name + ": User time: " +\
            str(cpu_time_1[0] - self.cpu_time_0[0]) + " S"
        print "# " + self.program_name + "y: System time: " +\
            str(cpu_time_1[2] - self.cpu_time_0[2]) + " S"

def main():
    """Test code and basic CLI functionality engine."""

    debug = False
    args_are_paths = True

    test_stats = TestStats()
    test_stats.print_startup()

    parser = argparse.ArgumentParser(description=\
        "Use the Google Drive API (REST v3) to get information " + \
        "about files to which you have access."\
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
        '--stat',
        type=str,
        help="Return the metadata for the node at the end of a path."
        )
    parser.add_argument(
        '-D', '--DEBUG',
        action='store_const', const=True,
        help='(Modifier) Turn debugging on.'
        )

    args = parser.parse_args()

    if args.DEBUG:
        debug = True
        print "args: " + str(args)

    if args.f:
        args_are_paths = False

    # Do the work ...

    drive_file = DriveFile(debug)

    if args.cd != None:
        drive_file.set_cwd(args.cd, debug)
        print "pwd: " + drive_file.get_cwd(debug)

    if args.find != None:
        if args_are_paths:
            if debug:
                print "# find '" + args.find + "'"
            drive_file.show_all_children(args.find, None, debug)
        else:
            drive_file.show_all_children(None, args.find, debug)
    elif args.ls != None:
        if args_are_paths:
            if debug:
                print "# ls '" + args.ls + "'"
            drive_file.show_children(args.ls, None, debug)
        else:
            drive_file.show_children(None, args.ls, debug)
    elif args.stat != None:
        if args_are_paths:
            drive_file.show_metadata(args.stat, None, debug)
        else:
            drive_file.show_metadata(None, args.stat, debug)

    # Done with the work

    if args.dump:
        print "dumping drive_file ..."
        print str(drive_file)
        print

    print
    print "# call_count: " + str(drive_file.call_count)

    drive_file.dump_cache()

    test_stats.print_final_report()

if __name__ == '__main__':
    main()
