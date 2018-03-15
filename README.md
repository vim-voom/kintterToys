**kintterToys** contains one program: **kintterFind**.

AUTHOR: see file AUTHOR

LICENSE: GNU General Public License Version 3

WEBSITE: <https://github.com/vim-voom/kintterToys>


kintterFind
===========

**kintterFind** is a [Python](https://www.python.org/) program with
[Tk/Ttk](http://www.tcl.tk/) GUI (Tkinter) for finding files. It uses
[scandir()](https://pypi.python.org/pypi/scandir) to traverse the file system
every time a search is performed (non-indexing search, like Unix `find`).
It is intended for the so-called Linux desktop. It also works on Windows.
It is naturally lightweight, portable, desktop-independent, and telemetry-free.

![](./html_files/kintterFind.png)


Requirements
------------

**Python 3** and **Tkinter** (which implies Tcl/Tk/Ttk) are required.
Python version >=3.4 is required. Python version >=3.5 is recommended.

Most Linux distros have Python 3 installed by default. Run command `python3` in
terminal and check version number. If it is >=3.5, you only need to install
Tkinter. To see if Tkinter is installed, try the following commands in python3
shell:

    >>> import tkinter
    >>> tkinter._test()

Linux distros usually do not install Tkinter by default. Commands to install it:

    Arch:
        $ sudo pacman -S tk
    Debian:
        $ sudo apt-get install python3-tk
    Fedora:
        $ sudo dnf install python3-tkinter
    PCLinuxOS:
        $ su -c 'apt-get install tkinter3'
    Slackware:
        $ su -c 'slackpkg install tcl tk'

If you are stuck with Python version 3.4, you will also need to install Python
module `scandir` from PyPI via `pip`. Commands for Debian 8 ("jessie"):

    $ sudo apt-get install python3-pip python3-dev
    $ sudo pip3 install scandir
    $ sudo apt-get remove python3-pip python3-dev

[DejaVu fonts](https://dejavu-fonts.github.io/) or another font family with
good coverage of Unicode symbols should be installed in order to display sort
signs in column headings (triangles) and check marks on filter tabs (squares).


Installing and starting
-----------------------

**kintterToys** is self-contained and portable. Download and extract it
anywhere you have permission to write, e.g., ~/Scripts/kintterToys.
Open terminal in the program directory and start **kintterFind** with the
following command:

    $ python3 start_kintterFind.py

If there are no errors and GUI appears, it's working.

An example .desktop file is included: [examples/kintterFind.desktop](./examples/kintterFind.desktop) .

To install kintterToys to /opt for all users, see [examples/install_kintterToys.sh](./examples/install_kintterToys.sh) .


Config file and config directory
--------------------------------

By default, during startup kintterFind looks for config file
`kintterFind.config.py` in config directory `~/.config/kintterToys/`.

To create config files in the default location, copy example config directory
`examples/config/kintterToys/` to `~/.config/`.

All available configuration options are documented in the example config file
[kintterFind.config.py](./examples/config/kintterToys/kintterFind.config.py) .

For maximum enjoyment, the config file should be viewed and edited in a text
editor with Python syntax highlighting. An invalid config file option usually
will not prevent the program from starting and will be reported in the Log.
It is still advisable after changing config file to start kintterFind from
terminal and watch for errors.

The name of config file is always "kintterFind.config.py". The config directory
where this file is located can be changed from the default via command line
option `--configdir`. Config directory and config file may be symbolic links.


Command line options
--------------------

`start_kintterFind.py` accepts two command line options (may be abbreviated to
`--c` and `--d`):

* `--configdir {path-to-config-directory}` Config directory to use instead of
  the default `~/.config/kintterToys/`. This is directory where kintterFind
  looks for the config file "kintterFind.config.py" during startup. If the path
  is not an absolute path (after expanding ~, $HOME, etc.) it is assumed to be
  relative to the program folder, that is directory of "start_kintterFind.py".
  This makes it possible to run kintterFind in portable mode. For example, to
  have config file just outside of the program folder, start kintterFind with
  the following command:

        $ python3 <path>/start_kintterFind.py --c ..

* `--directory {path}` Directory path or any other string to insert into
  combobox "Directories:" on startup. Useful for integration with a file
  manager.


Usage
-----

* Directories in fields "Directories:" and "Skip directories:" should be typed
  as absolute paths. `~` and environment variables such as `$HOME` may be used.
  To specify multiple directories, separate them with `|`.

* Directories specified in filter "Skipped dirs" are ***pruned***, that is not
  descended into.

* To select/deselect a filter, right-click on its tab. If no filters are
  selected, the entire directory listing will be produced.

* When searching, selected filters are applied in the order in which they are
  arranged in tabs: from left tab to right tab, top row first within the tab.

* Symbolic links are never followed during the search.

* Character `|` works as a separator in most fields. It separates directories
  and search queries. This is described in details below.

* Leading and trailing whitespace does not matter when entering text in fields.
  In cases where it may be necessary to include leading or trailing space,
  surround the string with "".

* Since this is Python 3, all strings are Unicode strings. File paths are
  converted by Python into Unicode strings. Unusual file names, such as file
  names with newlines or invalid encoding, should be avoided even though they
  seem to be well tolerated.


### Keyboard and mouse

`Ctrl-l` puts the focus into combobox Directories.

Standard Tkinter behavior: `Tab` and `Shift-Tab` traverse visible widgets,
`Space` toggles check marks and presses buttons.

Menus "Columns", "Ttk Theme" are detachable for enhanced clicking experience.

***Filters***

Filters are organized in tabs at the bottom. To turn a filter on/off,
`right-click` on its tab with the mouse. Alternatively, first select the filter
tab with left single-click, then left `double-click` it or press `Space`. Tabs
can also be traversed with `Ctrl-Tab` and `Shift-Ctrl-Tab`.

***Results (Treeview widget)***

There are in two mouse right-click menus: one for headings, one for items.

To sort a column, left-click on its heading. Or use heading's right-click menu.

`Return` and mouse left `double-click` open the current item with associated
program. Same as command Open in the right-click menu.

`Alt-Return` shows item properties. Same as Properties in the right-click menu.

To select one or more items: mouse `left-click`, `Ctrl-click`, `Shift-click`.
Select all: `Ctrl-a`.

Scrolling: `Up`, `Down`, `PgUp`, `PgDn`, `Home`, `End` will do the right thing.

***Log text area***

In addition to the right-click menu, standard key combinations should do the
expected thing: `Ctrl-c`, `Ctrl-v`, `Ctrl-a`, `Ctrl-z`, `Ctrl-y`.

`Ctrl-Tab` switches between Log and Results.


### "|" separates multiple search queries

Character `|` is used to separate multiple queries when specifying directories
and search queries except when match mode is RegExp. This applies to the
following fields:

* "**Directories:**". `|` separates multiple directories to search.
  Example: `~/.config | ~/.local` .

* "**Skip directories:**" in filter "Skipped dirs". Same as for
  "**Directories:**".

* "**Name:**" in filter "Name". `|` separates multiple strings or WildCard
  patterns to match in the same file name. For example, to find files with
  names containing "foo" or "bar", enter `foo|bar` and select Contains.
  *NOTE: This does not apply when match mode RegExp is selected.*

* "**Path:**" in filter "Path". Same as for "**Name:**".

* "**Skip dirs with name:**" in filter "Skipped dirs". Same as for "**Name:**".

* "**Extension:**" in filter "Type". `|` separates multiple extensions.
  Example: `.png|.svg|.gif|.jpg` .

* "**UID:**" and "**GID:**", "**MODE:**" in filter "Misc".

Leading and trailing whitespace is stripped. Whitespace around `|` is also
stripped when it is a separator. Blank items are ignored. One set of enclosing
"" is removed. Thus `foo  ||  bar |` or `"foo" | "bar"` are the same as
`foo|bar`.

To specify leading or trailing whitespace, enclose the string in "".
For example, to find files with names containing foo or bar followed by a
space, enter `"foo "|"bar "` in "Name:" and select Contains.

Empty strings specified as `""` are ignored: `""|foo|""|` is the same as `foo`.
The only exception from this rule is combobox "**Extension:**" where `""` may
be entered to specify file names without an extension, for example
`""|.txt|.py`.

_**NOTE 1**_: `|` is NOT a separator when RegExp match mode is selected. It is
instead a part of regular expression. That is, RegExp mode always uses entered
string as one regular expression. Leading and trailing whitespace is stripped
and one set of enclosing "" is removed, so to find file names ending with a
space enter `" $"` .

_**NOTE 2**_: `|` is NOT a separator in field "**Line:**" in filter "Content".
This is to allow searching files for literal `|`.

If it is not clear how the input text was processed for searching, take a look
at the Log.


### Match modes

The following explains how string matching modes work. The target string that
is being matched depends on the field. In comboboxes "Name:" and "Skip dirs
with name:" file names are matched. In comboboxes "Path:" whole file paths are
matched. And so on. Examples assume that file names are being matched.


**Exact** -- target string matches the search string exactly. Examples:

    foo       -- find files with name foo
    foo|bar   -- find files with names foo or bar


**Contains** -- target string contains the search string. Examples:

    foo       -- find files with names containing foo
    foo|bar   -- find files with names containing foo or bar


**StartsWith** -- target string starts with the search string. Examples:

    foo|bar     -- find files with names starting with foo or bar
    .           -- find dotfiles


**EndsWith** -- target string ends with the search string. Examples:

    .png|.svg   -- find files with names ending with .png or .svg 


**WildCard** -- wildcard matching on the whole target string. This uses Python
function fnmatch.fnmatchcase() plus casefold() when IgnoreCase is checked.
Reference: <https://docs.python.org/3/library/fnmatch.html#module-fnmatch> .

When matching file names, the pattern should be the same as what one enters
after `-name` or `-iname` when running GNU `find`, except that there is no need
to shell-escape anything, and multiple patterns can be separated with `|`.
Examples:

    foo           -- find files with name foo
    foo|bar       -- find files with names foo or bar
    *foo*|*bar*   -- find files with names containing foo or bar


**RegExp** -- search target string for regular expression.
Reference: <https://docs.python.org/3/library/re.html#regular-expression-syntax> .

Note that the target string is *searched* for a regex. (This is different from
WildCard mode which matches the whole string.) Examples:

    foo            -- find files with names containing foo
    ^foo$          -- find files with name foo
    ^(foo|bar)$    -- find files with names foo or bar
    \.(png|gif|jpe?g)$    -- find files with names ending in .png, .gif, .jpg, .jpeg
    \bfoo\b          -- find files with names containing word foo
    \b(foo|bar)\b    -- find files with names containing words foo or bar

As explained above, `|` here is part of regular expression, not a separator of
independent search strings.


### IgnoreCase

Checking the box "IgnoreCase" makes string matching case-insensitive.

When match mode is RegExp, this is achieved by compiling regex with option
re.IGNORECASE.
Reference: <https://docs.python.org/3/library/re.html#re.IGNORECASE> .

For all other match modes this is achieved by converting strings to lower case
with casefold().
Reference: <https://docs.python.org/3/library/stdtypes.html#str.casefold> .


### File name extensions

File name extensions may be specified in combobox **Extension:** in filter
"Type". For example: `.py` or `.htm|.html`.

Note that the leading dot must be included with each extension.

File name extensions are always matched in case-insensitive manner via
casefold().

To match file names without an extension, that is when extension is an empty
string, enter `""`. For example: `""|.txt|.md` .

Extension cannot be the whole file name: dotfiles such as .vim, .emacs, .config
have no extension.


### Filter "Misc"

**UID:** and **GID:** are for specifying file owner's User ID and Group ID
respectively. Input will be converted into a list of integers. Use `|` to
specify several numbers, e.g, `0|1000|1003` .

**NLINK>** is for specifying the minimum number of hard links. Input will be
converted into integer.

**MODE:** is for specifying the pattern of file mode. File mode is displayed in
the column MODE. It is a string of 10 characters in the form:

    drwxr-xr-x
    -rw-r--r--

Reference: <https://wiki.archlinux.org/index.php/File_permissions_and_attributes#Viewing_permissions> .

**MODE:** may be used to find files that have or lack certain permissions.
WildCard and RegExp matching works as described above. (Multiple WildCard
patterns separated with `|` may be specified.) For example, RegExp `^..*[xst]`
should find files that are executable by somebody (their owner, or their group,
or anybody else).

Note that **File type:** in filter "Type" is applied before **MODE:** in filter
"Misc" and is recommended for selecting directories, regular files, etc.


### Filter "Content"

When filter "Content" is selected, files are opened for reading in text mode
and read and searched for a string or pattern line-by-line. The user is
responsible for specifying correct file encoding, how to handle encoding
errors, and the format of line endings (options in the second row).

The content search is always done last, so other filters can be used to
pre-select text files by name or extension. Files other than regular files are
automatically rejected, there is no need to use "File type:" in filter "Type".

The search text in field "Line:" is always interpreted as one string or pattern
(`|` is not a separator). Leading and trailing whitespace is stripped and one
set of enclosing "" is removed. Match modes work as described above.

The content of each file is read and searched line-wise. A line can end with
`\n`, `\r` or `\r\n` depending on the file and option "newline". This means in
order to find lines ending with "foo" one should use RegExp `foo\s*$`.
Option "newline=None" enables universal newline mode: `\n`, `\r`, `\r\n` are
all treated as newline and translated into `\n`.

Options in the second row control how files are opened for reading. They
correspond to keyword arguments `encoding`, `errors`, `newline` for Python
function `open()`.
Reference: <https://docs.python.org/3/library/functions.html#open> .

Reference for encodings:
<https://docs.python.org/3/library/codecs.html#standard-encodings> .


### Handling or errors during find

There are 3 kinds of errors (Python exceptions) that are caught and logged
during each find process. Their count is displayed on the status line in the
form `N+N+N errors`, e.g., `0+0+0 errors` if no errors. Each kind is printed in
the Log as a separate list:

1. `**OSError** (during file system traversal)`. Exceptions from scandir().
   These are almost always exceptions PermissionError when you do not have
   permission to enter a directory. Running kintterFind as root should make
   them go away.

2. `**OSError** (during item processing)`. Exceptions while obtaining
   properties of an item returned by scandir(). These never happen.

3. `**Exception** (during file content search)`. Errors while opening or
   reading files when filter Content is selected. These are usually exceptions
   UnicodeDecodeError meaning the file could not be read because option
   "encoding" does not match the file's encoding or it is a binary file.
   To skip over encoding errors, set option "errors" to something other than
   "strict".

Other errors during find, if caught, will produce status line message
`ERROR OCCURRED DURING FIND, SEE LOG FOR TRACEBACK`.
This is likely due to a program bug and should be reported to the author.


### Columns

Columns may be customized by clicking in menu View -> Columns or by editing
option DISPLAYCOLUMNS in config file.

Columns **FileType**, **Directory**, **Name**, **Ext**, **SIZE**, **Size** are
always available internally. This means hiding/unhiding them has no effect of
scanning speed or memory consumption. In contrast, all other columns are
populated with data only if they are displayed during find.

Column **FileType** (first column by default, no heading) contains the first
character from the file mode string: `-` for regular file, `d` for directory,
`l` for symbolic link, `s` for socket file, etc.

Columns **Directory**, **Name**, **Ext**: self-explanatory.

Column **SIZE** shows the exact size in bytes. Column **Size** shows
approximate size in human-readable format. When sorting column **Size**, the
sorting is actually done by values in column **SIZE**, that is by exact size.

Column **LinkTo** shows the path to which the symbolic link points. `[-]`,
`[d]`, `[l]`, etc. indicate the type of the target. `[!]` means the target path
does not exist. If the target is another symbolic link, click Properties to see
the final target and all intermediate links.

Other columns with uppercase names (**MTIME**, **UID**, etc.) correspond to the
attributes of Python object `os.stat_result` (st_mtime, st_uid, etc.).
According to Python docs, these attributes "correspond roughly to the members
of the `stat` structure."
Reference: <https://docs.python.org/3/library/os.html#os.stat_result> .

Timestamps in columns **MTIME**/**CTIME**/**ATIME** do not show fractional
seconds, if there are any. This should be kept in mind when finding files by
timestamp. The exact time as reported by Python and used by filter "Time" can
be seen in file Properties.

Command Properties in the right-click menu for one file prints *current*
information about the file. This information may differ from what is displayed
in columns if the file at this path has changed since the last search.

File size units K, M, G, T, P are kibi-, mebi-, etc. (power of 1024 bytes).
File size units k, m, g, t, p are kilo-, mega-, etc. (power of 1000 bytes).


### File operations

Commands for file operations are in the menu Edit. There is currently only
Delete: it deletes selected files PERMANENTLY. **Delete cannot be undone!** For
this reason command Delete is disabled by default. To enable Delete, set config
file option `DELETE_IS_ENABLED` to True.

The universal approach to operate on found files is to copy their
Path/Directory/Name to the clipboard, switch to terminal, and then use command
line tools. For example, to move files to trash use
[trash-cli](https://github.com/andreafrancia/trash-cli) or similar tool.

Mouse right-click menu provides various ways to copy Path/Directory/Name of
selected files to the clipboard:

*right-click -> Copy Path/Directory/Name*: for the current item under the cursor.

*right-click -> Copy All -> Copy Paths/Directories/Names*: for all selected
items. Values are quoted and joined by space into one line, ready for pasting
into a terminal.

*right-click -> Copy All -> Copy Linewise -> Copy Paths/Directories/Names*: for
all selected items. Each value is put on a separate line. This can be pasted
into a file for further processing or to be used as an input.

NOTE: commands Copy Path/Directory/Name assume that Path/Directory/Name has no
newlines.


### Miscellaneous notes

When OS is Windows, paths of directories may be entered in "Directories:" and
"Skip directories:" with `\` or `/` as path separator. However, during search
path separators are normalized to `\`. Thus use `\` in filter "Path".

When OS is Windows, the following columns seem to always have value 0: SIZE of
directories, UID, GID, NLINK, INO.

--- The End ---
