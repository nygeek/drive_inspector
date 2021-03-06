<p>Memo to: File</p>
<p>From: <b>Marc Donner</b></p>
<p>Contact: <b>marc.donner@gmail.com</b></p>
<p>Subject: <b>DriveInspector roadmap</b></p>
<p>Date: <b>2018-06-17</b></p>

The roadmap comments from drivefile.py and other Drive Inspector
files are scattered and confusing.  Moving them here.

[+] 2018-04-29 Create a function Path => FileID (namei, basically)

[x] 2018-04-29 Normalize the DrivePath functions - two sorts
    one that returns a list of file metadata objects and one
    the returns just a list of FileIDs.
        2018-05-06 - replacing this with a render / view approach

[+] 2018-04-29 Naming convention for functions that return
    metadata versus FileID list

[+] 2018-04-29 Add a local store for state.  Needed for the
    PWD and CD functionality and for cache persistence

[+] 2018-04-29 Figure out how to fix the PyLint errors that come
    from the oauth2client.file.Storage ... this is a dynamic method
    and PyLint reports an error (false positive) from it.
        2018-05-05 put in a '# pylint: ' directive to stop the messages

[+] 2018-04-29 Implement an ls function - Path => FileID => list
[+] 2018-05-04 Figure out convention so that we can pass either a
    a path OR a FileID to one of the main methods (find, ls, ...)
        2018-05-06 did this with a kluge.  Not happy ... I'd prefer
        some clever polymorphism that diagnoses what string is a
        path and what is a FileID.

[+] 2018-05-06 Make each search function return a list of FileIDs
[+] 2018-05-06 Make a flag to modify the --find operation to show
    either just the directories or all of the files.
        2018-05-12 Added the --all flag to do this.

[+] 2018-05-06 Make a render function that accepts a list of FileIDs
    and a list of attributes and return a 2D array of values
        2018-05-28 Created drivereport.py that does this.

[+] 2018-05-07 Handle relative paths
        2018-05-09 - done

[+] 2018-05-07 Implement a PWD / CWD and CD function
        2018-05-09 - done

[+] 2018-05-07 Consolidate all of the FileID cache data so that
    we only need a single structure (self.file_data{}).  It would
    have four things under each FileID: metadata, path, time, ref_count
        2018-05-08 - done.

[+] 2018-05-07 Rewrite get_subfolders() to call get_children() and
    just filter out the non-children.
        2018-05-08 - done.

[+] 2018-05-11 Add an interactive main loop, let's call it driveshell.
        2018-05-20 - done

[+] 2018-05-12 list_children never relies on the cache.  Maybe I can
    do something clever here?
        2018-05-12 Augmented list_children to look in the cache first.

[+] 2018-05-12 Add flags to remove the existing cache and to skip
    writing the cache when done.
        2018-05-13 --nocache and --Z flags added.  --Z omits writing the
        cache, but does not actually remove the file.

[+] 2018-05-20 Move the debug flag out of the signature of the
    various methods and into an attribute of the DriveFile object.

[+] 2018-05-21 Rewrite the command parser to run from a table rather
    than a sequence of if ... elif ... elif ... else
        2018-05-26 Done

[+] 2018-05-23 Add a dirty flag to file_data so that I do not have
    to rewrite the cache file if the cache is unchanged.

[+] 2018-05-22 Create a one or more helper functions to manipulate
    paths.  The hacky stuff for dealing with 'cd foo' when in '/'
    is just plain stupid.  The result is ugly repeated code.  Ugh.
        2018-05-24 canonicalize_path() is a helper function in drivefile

[ ] 2018-05-28 Incorporate the machinery from drivereport.py into the
    CLI here.

[+] 2018-06-02 Build a list method that uses the API list function but
    does it without filtering by parent.  This will replicate the
    experimental stuff I did early with the dls.py prototype and help
    me find and understand the things I found with odd parents.
        2018-06-02 --showall command line option added.  Relevant
        functionality added to handlers, parser, and DriveFile class

[+] 2018-06-02 Make the path construction machinery smarter.  In
    particular, if there is no parent file and the owner is not me
    then infer a parent folder that is the owner''s "home directory"
    ... we can not see their folder structure, so we will simply say
    something like "~foo@bar.org/.../" to suggest the appropriate
    root.
        2018-6-03 The new path magic is now working with shared files.

[+] 2018-06-03 Establish an output file so that the reports and
    so forth can be put in specific files -o --output for drivefile
    and output <path> for driveshell.
        2018-06-05 added output management stuff to both drivefile
        and driveshell.

[X] 2018-06-03 Build a table of handlers in drivefile like the one
    in driveshell to streamline (or eliminate) the do_work() helper
    function.

[X] 2018-06-06 Review the drive inspector classes and see if I can
    design a coherent structure of inheritance that unifies them
    all.
        2018-06-22 DriveFileRaw is superclass for DriveFileCached
                   Next work on DriveShell and DriveReport
        2018-06-24 DriveShell now works with DriveFileCached

[ ] 2018-06-10 Review the design of namei(7) and revise the design
    of resolve_path() to return more informative error
    codes.

[ ] 2018-06-24 Make retrieve_items() in DriveReport into an iterator
    and then make render_items_html() and render_items_tsv()
    smart enough to iterate over the results.  Measure the
    wss impact of the change.

[ ] 2018-07-06 Enrich the messaging when first running the program
    and one has not yet created the .credentials directory and the
    .client_secret file within it.  The process of doing this is
    non-obvious and poorly documented, creating a severe barrier
    to usage.

[ ] 2018-07-06 Fix bug with --dirty.  It seems to update the mtime
    for the cache, so that the normal usage flow of --dirty followed
    by --dirty -R does not actually do the job.
