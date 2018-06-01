drive-inspector

Started: 2018-05-06
Language: Python 2.7

As a passionate and energetic user of Google Drive over the last
several years, I have accumulated a lot of files in My Drive.

One of the questions that I have asked myself from time to time is
how to browse an inventory of all of my files.

There is no simple way to do this in Drive.  Some years ago I tried
writing one in AppScript, but there were limitations in the API and
there were performance problems, so I ultimately abandoned the effort.

Recently I found the RESTful API to Google Drive (v3)
[https://developers.google.com/drive/v3/web/about-sdk]
and decided to try again using Python.

This utility is intended as a read-only tool to allow you to inspect
and analyze the metadata about your Drive portfolio.

The code is in drivefile.py.  Here is the help text:

```
usage: drivefile.py [-h] [-d] [-f] [--find FIND] [--ls LS] [--stat STAT] [-D]

Use the Google Drive API (REST v3) to get information about files to which you
have access.

optional arguments:
  -h, --help     show this help message and exit
  -a, --all      (Modifier) When running a find, show all files.
  --cd CD        Change the working directory.
  -d, --dump     When done running, dump the DriveFile object
  -f             (Modifier) Argument to stat, ls, find will be a FileID.
  --find FIND    Given a fileid, recursively traverse all subfolders.
  --ls LS        Given a path, list the files contained in it.
  -n, --nocache  (Modifier) When set, skip loading the cache.
  --stat STAT    Return the metadata for the node at the end of a path.
  -D, --DEBUG    (Modifier) Turn debugging on.
  -z, --Z        (Modifier) Skip writing out the cache at the end.
```

A few conventions:

This tool uses a UNIX-like path from the root to a terminal node to
concisely describe a file.  The root, which Drive shows as 'My Drive,'
is represented as '/' in this system.

There are three operations in drivefile.py:

Operation | Description
--------- | -----------
ls | takes a path or a FileID and returns a list of the files contained within it.
stat | takes a path or a FileID and returns the Drive metadata for it as a JSON string, prettyprinted.
find | takes a path or a FileID and recursively descends the implicit folder tree 'below' it, listing all of the folders it encounters.

One may specify the node to ls, stat, and find by either a path, as
described above, or by the FileID.

A FileID is, according to the documentation, "a unique opaque ID.
File IDs are stable throughout the life of the file, even if the
file name changes."

The metadata is extensive.  This utility concerns itself, at present,
with a subset of the metadata:

**id** - the FileID

**name** - the string name of the file

**parents** - an array of zero or more FileIDs of parents (folders) of the file

**mimeType** - the MIME type of the object

**owners** - an array of one or more owners of the file

**trashed** - a flag that reflects whether the file is in the Trash

**modifiedTime** - when the file was last modified

**createdTime** - when the file was created

**ownedByMe** - True if the file is owned by me

**shared** - True if the file is shared with one or more others

===

Some observations on the differences between Drive and the typical
UNIX file system.

**UNIX Files**

The UNIX file system is organized around the concept of inode.  An
inode is a metadata block that contains information about the file
along with pointers to other inodes that contain the contents of the
file.

A directory is a special file that maps names to inodes.  It is also
stored in inodes in the file system.

Fundamentally, the UNIX file system is built around data structures
that point down at their children.

**DRIVE**

In Drive everything is a File.  A folder is just a node with no extension
and with a mimeType of "application/vnd.google-apps.folder".

Folders have no representation of their children.  Instead, each
file has a list of parents.  Each parent is, presumably, a folder.

Traversing the imputed tree structure imposed on Drive involves getting
the FileID of the root node and then finding all files that include
the root node in the parents array.  Applied recursively this results
in a complete traversal of all files that have parents.

According to the documentation, every file should have one or more
parents, though some files created in the past may lack parents.

By contrast, the Drive system is organized around files that point
upward at their parents.

===

Some samples:

*This will show all of the files at the top level of your Drive.*
*In terms of the GUI, it's what you see when you click on 'My Drive'*

`python drivefile.py --ls /`

*This will show the metadata for the 'My Drive' object at the root*
*of your Drive.*

`python drivefile.py --stat /`

*This will display the folder hierarchy for your Drive*

`python drivefile.py --find /`

The inspector works both with paths and with FileIDs.  FileIDs are
opaque immutable strings that uniquely identify specific files.
The FileID 'root' is treated synonymously with whatever FileID your
particular drive has as the ID of the "My Drive" folder.

The flag -f tells the inspector to interpret the argument to ls, find, and stat as a FileID.

*find from the 'My Drive' folder downward*

`python drivefile.py -f --find root`

===

Authentication and authorization rely on OAuth2 and are fairly
tricky to get right.  There are two important steps:

1. Generate an OAuth2 credential for yourself.  The code for
drivefile.py expects to find this in a subdirectory of your Unix
home directory.  The subdirectory should be called .credentials.
This file should be called .client_secret.json ... you can download
the credential from the Google site, but then you'll need to rename
it and appropriately store it.

You can generate your own client secret file by going to the Google
developers console (https://console.developers.google.com/apis/dashboard)
and download your own key from the Credentials tab.  The result will
be a json file that you should rename .client_secret.json and move to
your ~/.credentials directory where the drive-inspector code will find
it.

2. Authorize access to the Drive space for a specific user that you
control.  When you first run drivefile.sh with one of the options that
accesses Drive, the Google API will open a web page that will allow
you to select a specific Google account to authorize.  This will create
a file called credentials.json in the ~/.credentials folder.

After the client secret is in place, run drivefile.py with one of the
operators that accesses your Drive (--ls, --stat, --find).  A window
of your default browser will be directed to a Google authorization
dialog page.  From there you should select an identity and, if needed,
authenticate yourself.  This will result in creation of the relevant
credentials.json file in the same ~/.credentials folder where the
client secret file is stored.

Until both of these files are valid and in place you will not be able
to use drivefile.py or driveshell.py to inspect your Drive files.

The credentials.json file will grant you access to only one Drive account.
If you want to change to a different Drive you will need to remove the
credentials.json file and go through the authorization flow again.

===

Future plans:

1. I plan to build a 'shell' option that drops you into an interactive
main loop that will support ls, find, and stat along with pwd and cd
to let you browse around the implicit file system.  [Done]

1. I plan to expand the function of the --find operator to report
all of the files in the system, with fully qualified paths. [Done]

1. I plan to augment the display of file names and paths with other
metadata:
   1. owner or owners [done]
   1. creation time [done]
   1. modification time [done]
   1. viewed by me date

1. I plan to support some filtering conveniences:
   1. files owned by me
   1. files owned by others
   1. files with multiple parents
   1. Docs, Sheets, Slides and other Google Apps
   1. Files created by third-party applications
   1. Sizes of files created by third-party applications (4e)

A framework program, drivereport.py, now generates a table for a find
rooted at the CWD.  You can seet the CWD either using the --cd command
to drivefile.py or the cd command in driveshell.py.  You may select
either HTML or TSV (tab separated values) output by making the obvious
change to the drivereport.py program.
