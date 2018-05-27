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
from drivefile import handle_ls
from drivefile import handle_stat
from drivefile import handle_find

reload(sys)
sys.setdefaultencoding('utf8')

APPLICATION_NAME = 'Drive Shell'

def handle_cd(drive_file, noun, args_are_paths, show_all):
    """Handle the cd verb by calling set_cwd()."""
    if drive_file.debug:
        print "# handle_cd(noun: " + str(noun) + ","
        print "#   args_are_paths: " + str(args_are_paths) + ","
        print "#   show_all: " + str(show_all) + ","
    drive_file.set_cwd(noun)
    print "pwd: " + drive_file.get_cwd()
    return True

def handle_debug(drive_file, noun, args_are_paths, show_all):
    """Handle the debug verb by toggling the debug flag."""
    if drive_file.debug:
        print "# handle_debug(noun: " + str(noun) + ","
        print "#   args_are_paths: " + str(args_are_paths) + ","
        print "#   show_all: " + str(show_all) + ","
    drive_file.set_debug(not drive_file.get_debug())
    return True

def handle_help(drive_file, noun, args_are_paths, show_all):
    """Handle the help verb by displaying the help text."""
    if drive_file.debug:
        print "# handle_help(noun: " + str(noun) + ","
        print "#   args_are_paths: " + str(args_are_paths) + ","
        print "#   show_all: " + str(show_all) + ","
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
    return True

def handle_pwd(drive_file, noun, args_are_paths, show_all):
    """Handle the pwd verb by displaying the current working directory."""
    if drive_file.debug:
        print "# handle_pwd(noun: " + str(noun) + ","
        print "#   args_are_paths: " + str(args_are_paths) + ","
        print "#   show_all: " + str(show_all) + ","
    print "pwd: " + drive_file.get_cwd()
    return True

def handle_quit(drive_file, noun, args_are_paths, show_all):
    """Handle the quit verb by returning True."""
    if drive_file.debug:
        print "# handle_quit(noun: " + str(noun) + ","
        print "#   args_are_paths: " + str(args_are_paths) + ","
        print "#   show_all: " + str(show_all) + ","
    return False

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

    # for this to work, all of the handlers need the same signature:
    # (drive_file, noun, args_are_paths=True)
    # If a function returns False, then we will exit the main loop
    handlers = (
        ('cd', handle_cd),
        ('debug', handle_debug),
        ('find', handle_find),
        ('help', handle_help),
        ('ls', handle_ls),
        ('pwd', handle_pwd),
        ('stat', handle_stat),
        ('quit', handle_quit),
        )

    drive_file = DriveFile(False)

    # Later on add a command line argument to skip the cache
    drive_file.load_cache()

    running = True
    tokens = []
    while running:
        line = raw_input("> ")
        tokens = line.split(None, 1)
        verb = tokens[0].lower() if tokens else ""
        noun = "." if len(tokens) <= 1 else tokens[1]
        recognized = False
        for (verb_target, handler) in handlers:
            if verb == verb_target:
                running = handler(drive_file, noun, True, True)
                recognized = True
        if not recognized:
            print "Unrecognized command: " + str(verb)

    drive_file.dump_cache()

    print "# call_count: "
    print "#    get: " + str(drive_file.call_count['get'])
    print "#    list_children: " + \
        str(drive_file.call_count['list_children'])


def main():
    """Test code and basic CLI functionality engine."""

    test_stats = TestStats()
    test_stats.print_startup()

    drive_shell()

    test_stats.print_final_report()

if __name__ == '__main__':
    main()
