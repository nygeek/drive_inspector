""" Implementation of the interactive DriveInspector using the DriveFile
    class implemented in drivefile.py

Started 2018-05-12 by Marc Donner

Copyright (C) 2018 Marc Donner

"""

# Wish List
#
# [ ] 2018-05-21 Rewrite the command parser to run from a table rather
#     than a sequence of if ... elif ... elif ... else

import sys

from drivefile import DriveFile
from drivefile import TestStats
from drivefile import canonicalize_path

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
    #    debug
    #    cache (dump | clear | reload)
    #
    # and, of course:
    #    quit

    drive_file = DriveFile(False)

    use_cache = True
    # Later on I will add a command line flag to skip the cache
    if use_cache:
        drive_file.load_cache()
    else:
        print "# Starting with empty cache."
        drive_file.init_metadata_cache()

    running = True
    tokens = []
    while running:
        line = raw_input("> ")
        tokens = line.split(None, 1)
        verb = "" if len(tokens) == 0 else tokens[0].lower()
        noun = "." if len(tokens) <= 1 else tokens[1]
        if drive_file.debug:
            print "verb: '" + str(verb) + "' noun: '" + str(noun) + "'"
        if verb == "quit":
            break
        elif verb == "cd":
            drive_file.set_cwd(noun)
            print "pwd: " + drive_file.get_cwd()
        elif verb == "ls":
            handle_ls(drive_file, noun, True)
        elif verb == "pwd":
            print "pwd: " + drive_file.get_cwd()
        elif verb == "find":
            handle_find(drive_file, noun, True, True)
        elif verb == "stat":
            handle_stat(drive_file, noun, True)
        elif verb == "debug":
            drive_file.set_debug(not drive_file.get_debug())
        elif verb == "help":
           print "driveshell"
           print
           print "Commands:"
           print "   cd <path>"
           print "   debug [Toggles the debug flag.]"
           print "   find <path>"
           print "   help [displays this help text.]"
           print "   ls <path>"
           print "   stat <path>"
           print "   pwd"
           print "   quit"
        else:
            print "Unrecognized command: " + str(verb)

    drive_file.dump_cache()

    print "# call_count: "
    print "#    get: " + \
            str(drive_file.call_count['get'])
    print "#    list_children: " + \
            str(drive_file.call_count['list_children'])


def handle_stat(drive_file, arg, args_are_paths):
    """Handle the --stat operation."""
    if drive_file.debug:
        print "# handle_stat("
        print "#    arg: " +  str(arg)
        print "#    args_are_paths: " +  str(args_are_paths)
    if arg != None:
        if args_are_paths:
            path = canonicalize_path(
                drive_file.get_cwd(),
                arg,
                drive_file.debug)
            drive_file.show_metadata(path, None)
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
            path = canonicalize_path(
                drive_file.get_cwd(),
                arg,
                drive_file.debug)
            drive_file.show_all_children(path, None, show_all)
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
            path = canonicalize_path(
                drive_file.get_cwd(),
                arg,
                drive_file.debug)
            drive_file.show_children(path, None)
        else:
            drive_file.show_children(None, arg)


def main():
    """Test code and basic CLI functionality engine."""

    test_stats = TestStats()
    test_stats.print_startup()

    drive_shell()

    test_stats.print_final_report()

if __name__ == '__main__':
    main()
