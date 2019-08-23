""" Implementation of the interactive DriveInspector using the DriveFile
    class implemented in drivefile.py

Started 2018-05-12 by Marc Donner

Copyright (C) 2018 Marc Donner

"""

import sys

from drivefilecached import DriveFileCached
from drivefilecached import canonicalize_path
from drivefileraw import TestStats
from drivefileraw import handle_ls
from drivefileraw import handle_stat
from drivefileraw import handle_status
from drivefileraw import handle_find

# This may not be needed in Python 3.  Check carefully.
# reload(sys)
# sys.setdefaultencoding('utf8')

APPLICATION_NAME = 'Drive Shell'

def handle_cd(drive_file, node_id, show_all):
    """Handle the cd verb by calling set_cwd()."""
    if drive_file.debug:
        print("# handle_cd(node_id: " + str(node_id) + ",")
        print("#   show_all: " + str(show_all))
    drive_file.set_cwd(node_id)
    print("pwd: " + drive_file.get_cwd())
    return True


def handle_debug(drive_file, node_id, show_all):
    """Handle the debug verb by toggling the debug flag."""
    if drive_file.debug:
        print("# handle_debug(node_id: " + str(node_id) + ",")
        print("#   show_all: " + str(show_all))
    drive_file.set_debug(not drive_file.get_debug())
    return True


def handle_help(drive_file, node_id, show_all):
    """Handle the help verb by displaying the help text."""
    if drive_file.debug:
        print("# handle_help(node_id: " + str(node_id) + ",")
        print("#   show_all: " + str(show_all))
    print("driveshell")
    print("\n")
    print("Commands:")
    print("   cd <path>")
    print("   debug [Toggles the debug flag.]")
    print("   find <path>")
    print("   help [displays this help text.]")
    print("   ls <path>")
    print("   output <path> [set the output file path.]")
    print("   pwd")
    print("   quit")
    print("   stat <path>")
    print("   status [Report the DriveFileCached object status.]")
    return True


def handle_output(drive_file, node_id, show_all):
    """Handle the output verb by setting an output file path and
       opening a new output file."""
    if drive_file.debug:
        print("# handle_pwd(node_id: " + str(node_id) + ",")
        print("#   show_all: " + str(show_all))
    drive_file.df_set_output(node_id)
    print("# output path now: '" + drive_file.output_path + "'")
    return True


def handle_pwd(drive_file, node_id, show_all):
    """Handle the pwd verb by displaying the current working directory."""
    if drive_file.debug:
        print("# handle_pwd(node_id: " + str(node_id) + ",")
        print("#   show_all: " + str(show_all))
    print("pwd: " + drive_file.get_cwd())
    return True


def handle_quit(drive_file, node_id, show_all):
    """Handle the quit verb by returning True."""
    if drive_file.debug:
        print("# handle_quit(node_id: " + str(node_id) + ",")
        print("#   show_all: " + str(show_all))
    return False


def drive_shell(teststats):
    """The shell supporting interactive use of the DriveFileCached
       machinery.
    """

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
    # (drive_file, node_id, show_all)
    # If a function returns False, then we will exit the main loop
    # As of now, only the quit command returns False

    # 2018-06-24 Ick ... replacing noun with node_id makes life
    # ugly for implementation of cache (dump | clear | reload)
    # I *could* break the handlers into two groups - nodeid_handlers
    # and noun_handlers and proceed that way.  I could leave cd as a
    # nodeid handler, since making that change actually improved a
    # bunch of stuff in the DriveFileCached class.

    startup_report = teststats.report_startup()
    print(startup_report)

    node_id_handlers = {
        'cd': handle_cd,
        'find': handle_find,
        'ls': handle_ls,
        'stat': handle_stat,
        }

    noun_handlers = {
        'debug': handle_debug,
        'help': handle_help,
        'output': handle_output,
        'pwd': handle_pwd,
        'status': handle_status,
        'quit': handle_quit,
        }

    drive_file = DriveFileCached(False)
    drive_file.df_set_output('stdout')

    # Later on add a command line argument to skip the cache
    drive_file.load_cache()

    running = True
    tokens = []
    while running:
        try:
            # Python 3 input() behaves as Python 2 raw_input()
            # To get Python 2 input() behavior do eval(input())
            # line = raw_input("> ")
            line = input("> ")
            tokens = line.split(None, 1)
            verb = tokens[0].lower() if tokens else ""
            noun = "." if len(tokens) <= 1 else tokens[1]
            if verb in node_id_handlers.keys():
                # Resolve the noun to a node_id
                path = canonicalize_path(
                    drive_file.get_cwd(),
                    noun,
                    drive_file.debug
                    )
                node_id = drive_file.resolve_path(path)
                running = node_id_handlers[verb](drive_file, node_id, True)
            elif verb in noun_handlers.keys():
                running = noun_handlers[verb](drive_file, noun, True)
            else:
                print("Unrecognized command: " + str(verb))
        except EOFError:
            print("\n# EOF ...")
            running = False

    drive_file.dump_cache()

    print("# call_count: ")
    print("#    get: " + str(drive_file.call_count['get']))
    print("#    list_children: " + \
        str(drive_file.call_count['list_children']))

    wrapup_report = teststats.report_wrapup()
    print(wrapup_report)


def main():
    """Test code and basic CLI functionality engine."""
    test_stats = TestStats()
    drive_shell(test_stats)


if __name__ == '__main__':
    main()
