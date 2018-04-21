#
# This is the DriveFile class
#

#
# Started 2018-04-20 by Marc Donner
# Copyright (C) 2018 Marc Donner
#

import argparse
import datetime
import httplib2
import os
import psutil
import sys
import time

from apiclient import discovery
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage

reload(sys)
sys.setdefaultencoding('utf8')

# class DriveFile(object):

def main():

    program_name = sys.argv[0]
    print "program_name: " + program_name

    parser = argparse.ArgumentParser(description='Accept a path.')

    parser.add_argument('path', type=str, nargs='?',\
            default='root', help='Path')

    args = parser.parse_args()

    print "path: " + args.path

if __name__ == '__main__':
    main()
