*********************** kintterFind.config.py ************************
# This is an example configuration file for kintterFind.
# Encoding is utf-8. Line endings are \n.
# By default, kintterFind looks for this file in directory
#       ~/.config/kintterToys/
#
# This config file includes all available options in the same form as in the
# source file for default options "kintterToys/kintterFind_options.py".
# Options that don't need to be changed may be removed from here.
# 
# The syntax of this config file is the same as a for a Python file that has
# only module-level constants. Options are defined as follows:
#
#       option1 = expression1 line 1
#           expresssion1 line 2
#           expresssion1 line 3
#       ...
#       option2 = expression2 line 1
#       ...
#
# Where expression must be a valid Python expression: True, False, integer,
# string, list or tuple, dictionary.
#
# Lines at the start of file before the first option are ignored. Commented
# lines and blank lines are ignored.
# NOTE: This is not a Python script. It is not possible to run Python code
# here. See "kintterToys/config_file_parser.py" for details.
######################################################################
######################## kintterFind OPTIONS #########################
######################################################################

#--- Application window ----------------------------------------------

# Application window size and position on desktop in pixels:
#       WxH+X+Y, WxH-X-Y, WxH+X-Y, WxH-X+Y.
# W is width. H is height.
# +X or -X is distance from the left or right edge of desktop respectively.
# +Y or -Y is distance from the top or bottom edge of desktop respectively.
GEOMETRY = "1200x600+20+20"
# If empty string, application window is sized to about 90% of screen size.
GEOMETRY = ""

# True: bottom panel is in fixed layout.
# False: bottom panel stretches to the full width of application window.
PANEL_IS_FIXED = True

# Initial width (in characters) of combobox Directories. It determines the
# width of bottom panel when PANEL_IS_FIXED is True. 
WIDTH_DIRECTORIES = 75

# Application icon. If empty string, don't set application icon.
# This is path to a .gif file to be used as appplication icon. If path is not
# absolute, it is relative to the config directory. Examples:
#ICON = "~/.config/icons/find.gif"
#ICON = "kintterFind.gif"
ICON = ""


#--- FONTS -----------------------------------------------------------
# These are Tkinter font descriptors.
# On Linux can use: ("Monospace", 11) , ("Sans", 11) , ("Serif", 11) .
# Font families that are available on all platforms: "Courier", "Helvetica", "Times".
# 3rd item can be: "bold", "italic", "underline", "overstrike", "bold italic", etc.

# Font for typed text: comboboxes, entry boxes, Log text area. Should be fixed-width.
FONT_TEXT = ('DejaVu Sans Mono', 11)

# Font for rows in Results (Treeview widget).
# This needs to be a fixed-width font, otherwise Fit column width will not work properly.
FONT_RESULTS = ('DejaVu Sans Mono', 11)

# Font for column headings in Results (Treeview widget).
# This font should be able to display sort signs.
FONT_HEADING = ('Helvetica', 11, 'bold')

# Font for most other widgets: labels, buttons, menus.
# This font should be able to display on/off signs on filter tabs.
FONT_LABEL = ('DejaVu Sans', 11)


#--- Tk options ------------------------------------------------------
# List of (pattern, value) pairs to be applied by calling
#       root.option_add(pattern, value)
# This can be used to set menu and Log fonts (will override the above FONT
# settings), menu and Log colors.
# **WARNING**: an invalid value here will likely prevent the program from
# starting. Always start the program from terminal after changing this.
# Example:
#OPTION_ADD = [
#        ['*Text.font', ('Courier', 13, 'bold italic')],
#        ['*Text.background', 'black'],
#        ['*Text.foreground', 'white'],
#        ['*insertBackground', 'green'], # no effect on ttk.Combobox and ttk.Entry
#        ['*Menu*background', 'yellow'],
#        ['*Menu*foreground', 'green3'],
#        ['*Menu*selectColor', 'red'], # menu check and radio buttons
#        ['*Listbox*background', 'pink'],
#        ]
OPTION_ADD = []


#--- Ttk Themes ------------------------------------------------------
# List of preferred Ttk themes, in order of preference. The first available
# theme on the list will be applied during startup.
# Linux has 4 themes:
#       'alt', 'clam', 'classic', 'default' (default)
# Windows has the above 4 plus:
#       'vista' (default), 'winnative', 'xpnative'
# Example:
#TTK_THEMES = ['winnative', 'clam']
TTK_THEMES = []


#--- Dropdown lists for comboboxes. ----------------------------------
# The first item on the list, if any, will be inserted into combobox during startup.
# Set the first item to "" if you want combobox initially empty.

# Combobox "Directories:".
DROPDOWN_DIRECTORIES = [
    "$HOME",
    "~/.config | ~/.local",
    "/usr",
    "/usr/share | /usr/local/share | /etc/xdg | ~/.config | ~/.local",
    "/usr/share/applications | /usr/local/share/applications | ~/.local/share/applications",
        ]

# Fiter "Skipped dirs", combobox "Skip directories:".
DROPDOWN_SKIP_DIRECTORIES = ['', '/media | /mnt', ]

# Filter "Skipped dirs", combobox "Skip dirs with names:".
DROPDOWN_SKIP_DIRS_WITH_NAME = ['', '.', ]

# Filter "Name", 1st combobox "Names:".
DROPDOWN_NAME_1 = ['',]

# Filter "Name", 2nd combobox "Names:".
DROPDOWN_NAME_2 = ['',]

# Filter "Path", 1st combobox "Paths:".
DROPDOWN_PATH_1 = ['',]

# Filter "Path", 2nd combobox "Paths:".
DROPDOWN_PATH_2 = ['',]

# Filter "Type", combobox "Extenstions:".
DROPDOWN_EXTENSION = ['',
    '""|.txt|.md|.vim|.py|.sh|.bat', # text files
    '.png|.svg|.gif|.jpg|.jpeg|.xpm|.bmp', # images
    '.avi|.mpg|.mpeg|.mkv|.mp4|.wmv', # video
        ]

# Filter "Misc", combobox "MODE:".
DROPDOWN_MODE = ['',
    '-rw-r--r--|drwxr-xr-x',
    '^....*[xst]',
    '^[^dl]...*[xst]',
    ]

# Filter "Content", combobox "encoding=".
# List of encodings. A short comment may be included after "#".
# The total length of each string item should not exceed 50 chars.
# https://docs.python.org/3/library/codecs.html#standard-encodings
DROPDOWN_ENCODING = [
    'utf-8',
    'ascii',
    'latin-1', # iso-8859-1; Western Europe
    'cp1252', # Windows-1252; Western Europe
    'utf-16-le', # UTF-16LE; Windows default for Unicode (e.g., exported .reg files)
    'cp1251 #Cyrillic', # Windows-1251; Bulgarian, Byelorussian, Macedonian, Russian, Serbian 
    ]


#--- Column max width for Fit "with Max" (in pixels). ----------------
# When doing Fit "with Max", the column width will not exceed this value.
FIT_MAX_WIDTH = 400


#--- Columns to display in Results. ----------------------------------
# List of columns to display in Results after startup. Columns will be
# displayed in the given order. Invalid and duplicate names will be ignored.

# All available columns in default order:
#DISPLAYCOLUMNS = (
#    'FileType', 'Directory', 'Name', 'Ext', 'SIZE', 'Size',
#    'MTIME', 'CTIME', 'ATIME',
#    'LinkTo',
#    'MODE', 'UID', 'GID', 'NLINK', 'INO',
#    )

DISPLAYCOLUMNS = (
    'FileType',
    'Directory',
    'Name',
    'Ext',
    'Size',
    'MTIME', 
    )


#--- Results (Treeview widget) appearance. ---------------------------
# When color or style option is "", it is not configured.

# Background color of empty Treeview area. No effect if a Windows theme.
RESULTS_FIELD_BG = ''

# Default background and foreground colors of rows in Results.
# background color of even rows (Treeview bg)
RESULTS_BG = 'gray97'
# background color of odd rows for stripy view
RESULTS_STRIPE_BG = '#e0eeee' # #e0eeee azure2
# foreground color of regular files (Treeview fg)
RESULTS_FG = 'black'

# background and foreground colors of directories
RESULTS_DIR_BG = ''
RESULTS_DIR_FG = 'blue3'
# background and foreground colors of symbolic links
RESULTS_LINK_BG = ''
RESULTS_LINK_FG = 'magenta4'
# background and foreground colors of items other than regular files, directories, or symbolic links
RESULTS_OTHER_BG = ''
RESULTS_OTHER_FG = 'red'

# Font style of items in Results: "bold", "italic", "underline", "overstrike", "bold italic", etc.
RESULTS_DIR_STYLE = 'bold'
RESULTS_LINK_STYLE = 'italic'
RESULTS_OTHER_STYLE = ''


#=== File and Directory openers ======================================
#
# Commands for opening file items in Results with external applications.
# These are commands in the mouse right-click menu.
#
# Each command is a string. It is split into arguments with shlex.split(),
# placeholders are expanded, arguments are passed to subprocess.Popen(args).
# If OS is Windows, / should be used as path separator, not \ .
#
# Use the following placeholders for file's Path, Directory, and Name
# respectively (do not put them in quotes):   %P    %D    %N

#--- Open ------------------------------------------------------------
# Command for opening a file with its associated program.
# When this is empty:
# If OS is Windows, file's Path is opened with Python os.startfile().
# If OS is non-Windows, file's Path is opened with 'xdg-open'.
OPEN = ''

# On non-Windows the default is equivalent to:
#OPEN = 'xdg-open %P'

# Xfce:
#OPEN = 'exo-open %P'

# OPEN is also invoked by Return and mouse left double-click.
# Set this to False to disable opening files with mouse left double-click.
DOUBLECLICK_IS_ENABLED = True


#--- Open in File Manager --------------------------------------------
# Command for opening a file in File Manager.
# When this is empty:
# If OS is Windows, file's Directory is opened with Python os.startfile().
# If OS is non-Windows, file's Directory is opened with 'xdg-open'.
OPEN_FM = ''

# On non-Windows the default is equivalent to:
#OPEN_FM = 'xdg-open %D'

# Dolphin:
#OPEN_FM = 'dolphin --select %P'

# Thunar:
#OPEN_FM = 'thunar %D'

# SpaceFM, reuse current tab:
#OPEN_FM = 'spacefm -r %D'

# Windows file managers: space before %P is needed
# Windows Explorer:
#OPEN_FM = 'explorer.exe /select, %P'
# XYplorer:
#OPEN_FM = '"C:/Programs/XYplorer/XYplorer.exe" /select= %P'


#--- Extra Open commands ---------------------------------------------
# Additional Open commands to insert into the right-click menu
# after "Open in File Manager". Optional. Set to [] to ignore it.
# Format: [ [label1, command1], [label2, command2], ... ]
# 1st string is menu label. 2nd string is the corresponding command.
# Example:
#OPEN_EXTRA = [
#        ['Edit', 'gvim %P'],
#        ]
OPEN_EXTRA = []


#--- Menu "Open With" ------------------------------------------------
# Commands in the right-click submenu "Open With".
# If this option is [], submenu will not be created.
# Format: [ [label1, command1], [label2, command2], ... ]
# 1st string is menu label. 2nd string is the corresponding command.
OPEN_WITH = [
        ['GVim', 'gvim -p --remote-tab-silent %P'],
        ['GVim (new)', 'gvim %P'],
        ['Mousepad', 'mousepad %P'],
        ['XTerm', 'xterm -fa Monospace -fs 12 -e "cd %D; bash"'],
        ['URxvt', 'urxvt -fn xft:monospace:size=11 -rv -sr -cd %D'],
        ['Xfce Terminal', 'xfce4-terminal --hold --working-directory %D'],
        ]

# Windows programs: use / as path separator.
#OPEN_WITH = [
#        ['Firefox', '"C:/Program Files (x86)/Firefox/firefox.exe" %P'],
#        ]


# Windows programs: use / as path separator.
#OPEN_WITH = [
#        ['Firefox', '"C:/Program Files (x86)/Firefox/firefox.exe" %P'],
#        ]


#=== File Operations =================================================
# If False, menu command Edit -> Delete will not delete files.
# Set to True to enable Delete. NOTE: files are deleted PERMANENTLY!
DELETE_IS_ENABLED = False


# The End
