drive-inspector

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

The code is in drivefile.py.  Here is the help text:

usage: drivefile.py [-h] [-d] [-f] [--find FIND] [-l LS] [--stat STAT] [-D]

Use the Google Drive API (REST v3) to get information about files
to which you have access.

optional arguments:
  -h, --help      show this help message and exit
  -d, --dump      When done running, dump the DriveFile object
  -f              Modifier. Argument to stat, ls, find will be a FileID.
  --find FIND     Given a fileid, recursively traverse all subfolders.
  -l LS, --ls LS  Given a path, list the files contained in it.
  --stat STAT     Return the metadata for the node at the end of a path.
  -D, --DEBUG     Turn debugging on

A few conventions:

This tool uses a UNIX-like path from the root to a terminal node to
concisely describe a file.  The root, which Drive shows as 'My Drive,'
is represented as '/' in this system.

There are three operations in drivefile.py:

--ls - takes a path or a FileID and returns a list of the files
       contained within it.

--stat - takes a path or a FileID and returns the Drive metadata
         for it as a JSON string, prettyprinted.

--find - takes a path or a FileID and recursively descends the
         implicit folder tree 'below' it, listing all of the folders
         it encounters.

One may specify the node to ls, stat, and find by either a path, as
described above, or by the FileID.

A FileID is, according to the documentation, "a unique opaque ID.
File IDs are stable throughout the life of the file, even if the
file name changes."

The metadata is extensive.  This utility concerns itself, at present,
with a subset of the metadata:

id - the FileID
name - the string name of the file
parents - an array of zero or more FileIDs of parents (folders) of
   the file
mimeType - the MIME type of the object
owners - an array of one or more owners of the file
trashed - a flag that reflects whether the file is in the Trash

===

Some observations on the differences between Drive and the typical
UNIX file system.

UNIX Files

The UNIX file system is organized around the concept of inode.  An
inode is a metadata block that contains information about the file
along with pointers to other inodes that contain the contents of the
file.

A directory is a special file that maps names to inodes.  It is also
stored in inodes in the file system.

DRIVE

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
