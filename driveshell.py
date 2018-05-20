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
from drivefile import TestStats

reload(sys)
sys.setdefaultencoding('utf8')

APPLICATION_NAME = 'Drive Shell'

def drive_shell():
    """The shell supporting interactive use of the DriveFile machinery."""

    # Each command will be structured as VERB NOUN
    # The first set of verbs that we will support are:
    #    ls
    #    stat
    #    find
    #    cd
    #    pwd
    #
    # We will also support some state modification commands:
    #    debug (on | off)
    #    cache (dump | clear | reload)
    

def setup_parser():
    """Set up the arguments parser.
       Returns: parser
    """
    parser = argparse.ArgumentParser(description=\
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
        '-n', '--nocache',
        action='store_const', const=True,
        help='(Modifier)  When set, skip loading the cache.'
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
    parser.add_argument(
        '-z', '--Z',
        action='store_const', const=True,
        help='(Modifier) Skip writing out the cache at the end.'
        )
    return parser

def handle_stat(drive_file, arg, args_are_paths):
    """Handle the --stat operation."""
    if drive_file.debug:
        print "# handle_stat("
        print "#    arg: " +  str(arg)
        print "#    args_are_paths: " +  str(args_are_paths)
    if arg != None:
        if args_are_paths:
            drive_file.show_metadata(arg, None)
        else:
            drive_file.show_metadata(None, arg)

def handle_find(drive_file, arg, args_are_paths, show_all):
    """Handle the --find operation."""
    if drive_file.debug:
        print "# handle_find("
        print "#    arg: " +  str(arg)
        print "#    args_are_paths: " +  str(args_are_paths)
        print "#    show_all: " +  str(show_all)
    if arg is not None:
        if args_are_paths:
            drive_file.show_all_children(arg, None, show_all)
        else:
            drive_file.show_all_children(None, arg, show_all)


def handle_ls(drive_file, arg, args_are_paths):
    """Handle the --ls operation."""
    if drive_file.debug:
        print "# handle_ls("
        print "#    arg: " +  str(arg)
        print "#    args_are_paths: " +  str(args_are_paths)
    if arg is not None:
        if args_are_paths:
            drive_file.show_children(arg, None)
        else:
            drive_file.show_children(None, arg)

def do_work():
    """Parse arguments and handle them."""

    parser = setup_parser()
    args = parser.parse_args()

    args_are_paths = True
    if args.f:
        args_are_paths = False

    use_cache = True
    if args.nocache:
        use_cache = False

    # Do the work ...

    if args.DEBUG:
        drive_file = DriveFile(True)
        print "args: " + str(args)
    else:
        drive_file = DriveFile(False)

    if use_cache:
        drive_file.load_cache()
    else:
        print "# Starting with empty cache."
        drive_file.init_metadata_cache()

    if args.cd != None:
        drive_file.set_cwd(args.cd)
        print "pwd: " + drive_file.get_cwd()

    handle_find(drive_file, args.find, args_are_paths, args.all)

    handle_stat(drive_file, args.stat, args_are_paths)

    handle_ls(drive_file, args.ls, args_are_paths)

    # Done with the work

    if args.dump:
        print "dumping drive_file ..."
        print str(drive_file)
        print

    print
    print "# call_count: "
    print "#    get: " + \
            str(drive_file.call_count['get'])
    print "#    list_children: " + \
            str(drive_file.call_count['list_children'])

    if args.Z is None:
        drive_file.dump_cache()
    else:
        print "# not writing cache."


def main():
    """Test code and basic CLI functionality engine."""

    test_stats = TestStats()
    test_stats.print_startup()

    do_work()

    test_stats.print_final_report()

if __name__ == '__main__':
    main()
