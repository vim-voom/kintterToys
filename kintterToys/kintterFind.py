# -*- coding: utf-8 -*-

import sys, os, re, fnmatch, time
import threading
import stat # _stat
import subprocess, shlex
import tkinter as tk
import tkinter.ttk as ttk
import tkinter.font as tkFont
import tkinter.filedialog as tkFileDialog
import tkinter.messagebox as tkMessageBox
import traceback # already in sys.modules
shutil = None # lazy import

# os.scandir() is available in Python >=3.5
# users of Python 3.4 can install scandir from PyPI via pip
_scandir = getattr(os, 'scandir', None)
if not _scandir:
    import scandir
    _scandir = scandir.scandir

# pwd, grp (non-Windows)
try:
    import pwd, grp
except ImportError:
    _getpwuid = _getgrgid = lambda s: ('n/a',)
else:
    _getpwuid, _getgrgid = pwd.getpwuid, grp.getgrgid

if not (getattr(os, 'major', None) and getattr(os, 'minor', None)):
    os.major = os.minor = lambda s: 'n/a'

# local imports
from . import PROGRAMDIR
from . import kintterFind_options as OPT
from . import config_file_parser

# frequently used
_sep = os.sep
_path = os.path
_join = os.path.join
_normcase = os.path.normcase
_time = time.time
_strftime = time.strftime
_localtime = time.localtime
_filemode = stat.filemode

if getattr(os, 'geteuid', None) and os.geteuid() == 0:
    TITLE = '[ROOT] kintterFind'
else:
    TITLE = 'kintterFind'

FT_DESCRIP = {'-': 'regular file', 'd': 'directory', 'l': 'symbolic link',
              'c': 'character device', 'b': 'block device', 'p': 'named pipe', 's': 'socket file',
              'D': 'door', 'P': 'event port', 'w': 'whiteout',
              '?': 'unknown', '!': 'does not exist', }

LHR = '=' * 70 # Log horizontal ruler
LD1, LD2 = '--- ', ' ---' # Log headline decorators

TIME_FORMAT = '%Y-%m-%d %H:%M:%S' # "YYYY-MM-DD HH:MM:SS", must be sortable

# sort signs appended to headline text: Low-to-High, High-to-Low
#SL2H, SH2L = ' <', ' >'
SL2H, SH2L = ' ▲', ' ▼'

# on/off signs prepended to text on tabs in notebook Filters
#TAB_ON, TAB_OFF = '* ', '  '
#TAB_ON, TAB_OFF = '■ ', '□ ' # too big
TAB_ON, TAB_OFF = '◼ ', '◻ '


######################################################################

class Application:
    def __init__(self, root, configDir, startupDir, startupLog):
        self.root = root
        root.title(TITLE)
        root.resizable(width=True, height=True)
        # disable close button on app window during FIND
        root.protocol('WM_DELETE_WINDOW', self.c_quit_app)

        self._isBusy = False # True during FIND process
        self._isCancelled = False # True after CANCEL button pressed during FIND

        self.RSLTS = []

        # location of last mouse right-click; these are for Treeview popup menus
        self._popCID = '' # column id; this is column name (not '#1', '#2', etc)
        self._popIID = '' # item id of item under the cursor (clicked upon)
        self._popIIDS = () # items id's of all selected items when click happened

        # column id of last sorted column (has SL2H or SH2L at the end of heading)
        self._sortedCID = ''

        self.tags = {'d': 'd', 'l': 'l'}

        self.startupLog = startupLog
        startupLog.append('Starting...')
        startupLog.append('program directory:\n    %s' %(quoted(PROGRAMDIR)))

        if not configDir:
            configDir = OPT.CONFIGDIR
        configDir = full_path(configDir, basedir=PROGRAMDIR)
        x = '' if _path.isdir(configDir) else ' (NOT FOUND)'
        startupLog.append('config directory%s:\n    %s' %(x, quoted(configDir)))
        # parse config file, replace options in OPT with user options
        self.do_configfile(configDir, 'kintterFind.config.py')

        # set up application icon, if any
        if OPT.ICON:
            icon_path = full_path(OPT.ICON, basedir=configDir)
            try:
                icon = tk.PhotoImage(file=icon_path)
                root.tk.call('wm', 'iconphoto', root._w, icon)
            except tk.TclError as e:
                startupLog.append('**tkinter.TclError** while setting application icon (option ICON):\n    %s' %e)

        # configure tkinter fonts
        self.configure_tkFonts()

        # configure ttk style and themes
        self.ttkStyle = ttk.Style()
        self.ttkThemes = list(self.ttkStyle.theme_names())
        self.ttkThemes.sort()
        #print(self.ttkThemes)
        # apply user-preferred theme
        th0 = self.ttkStyle.theme_use()
        for th in OPT.TTK_THEMES:
            if th == th0:
                break
            elif th in self.ttkThemes:
                self.c_apply_ttkTheme(th)
                break
        self.configure_ttkStyle()

        # invalid value cannot be caught here, it will cause error later
        for p, v in OPT.OPTION_ADD:
            self.root.option_add(p, v)

        # create all widgets
        self.init_widgets(startupDir)
        self.ntbkFilters.select(1)

        # clickable ttk widgets that will be disabled during FIND
        # trvwResults is not included because disabling it does not work
        # ttk widgets that are always visible
        self.clickablesA = (self.ntbkResults, self.ntbkFilters,
                            self.cmbbDir, self.btnDirChooser, self.ckbRecurse)
        # ttk widgets in tabs of notebook Filters
        self.clickablesB = {0: (self.cmbbSkipDir, self.btnSkipDirChooser,
                                self.cmbbSkipName, self.opmSkipNameMode, self.ckbSkipNameIC),
                            1: (self.opmName1, self.cmbbName1, self.opmName1Mode, self.ckbName1IC,
                                self.opmName2, self.cmbbName2, self.opmName2Mode, self.ckbName2IC),
                            2: (self.opmPath1, self.cmbbPath1, self.opmPath1Mode, self.ckbPath1IC,
                                self.opmPath2, self.cmbbPath2, self.opmPath2Mode, self.ckbPath2IC),
                            3: (self.opmExts, self.cmbbExts,
                                self.ckbTypeF, self.ckbTypeD, self.ckbTypeL, self.ckbTypeO),
                            4: (self.entSize1, self.opmSize, self.entSize2),
                            5: (self.entTime1, self.opmTime, self.entTime2, self.btnTimeToClipboard),
                            6: (self.opmUID, self.entUID, self.opmGID, self.entGID,
                                self.opmMODE, self.cmbbMODE, self.opmMODEMode, self.entNLINK),
                            7: (self.entCont, self.opmContMode, self.ckbContIC,
                                self.cmbbContEnc, self.opmContErrors, self.opmContNewline), }

        # create menu bar
        # must be done after creating widgets: need Treeview columns
        self.init_menubar()

        # popup menu for text widget Log
        self.pmenuLog = self.make_pmenuLog()
        self.txtLog.bind('<Button-3>', self.c_log_rclick)

        # popup menus for Treeview
        self.pmenuHeading = self.make_pmenuHeading()
        self.pmenuResults = self.make_pmenuResults()
        self.trvwResults.bind('<Button-3>', self.c_trvw_rclick)

        # Treeview bindings
        # Open
        self.trvwResults.bind('<Return>', self.c_trvw_kb_open)
        if OPT.DOUBLECLICK_IS_ENABLED:
            self.trvwResults.bind('<Double-Button-1>', self.c_trvw_mb_open)
        # Properties
        self.trvwResults.bind('<Alt-Return>', self.c_trvw_properties)
        # select all items
        self.trvwResults.bind('<Control-a>', self.c_trvw_kb_selectall)
        # scrolling
        # keys Prior (PgUp) and Next (PgDn) do the right thing by default
        # binding key KP_* give exception on Windows
        for k in ('<Home>', '<End>', '<KP_Home>', '<KP_End>', '<KP_Prior>', '<KP_Next>'):
            try:
                self.trvwResults.bind(k, self.c_trvw_kb_scroll)
            except tk.TclError:
                pass

        # notebook Results: don't allow focus on tabs, move focus to Treeview or Log
        self.ntbkResults.bind('<FocusIn>', self.c_rslts_focusin)
        # shortcut for switching between Treeview and Log
        self.trvwResults.bind('<Control-Tab>', self.c_rslts_switchtab)
        self.txtLog.bind('<Control-Tab>', self.c_rslts_switchtab)

        # notebook Filters: toggle checkmark signs on tabs
        self.ntbkFilters.bind('<space>', self.c_toggle_filter)
        self.ntbkFilters.bind('<Double-Button-1>', self.c_toggle_filter)
        self.ntbkFilters.bind('<Button-3>', self.c_toggle_filter)

        # global bindings
        self.root.bind_all('<Control-l>', lambda event: self.cmbbDir.focus_set())

        # configure geometry
        wxh = False
        if OPT.GEOMETRY:
            try:
                root.geometry(OPT.GEOMETRY)
                wxh = True
            except tk.TclError as e:
                startupLog.append('**tkinter.TclError** while setting geometry (bad GEOMETRY option):\n    %s' %e)
        if not wxh:
            wi, hi = root.winfo_screenwidth(), root.winfo_screenheight()
            ge = '%sx%s+10+10' %(int(wi*0.95), int(hi*0.85))
            root.geometry(ge)

        self.cmbbDir.focus_set()

        # finish
        startupLog.append('Ready...')
        self.log_put('\n'.join(startupLog))
        x = '' if len(startupLog) == 5 else ' **SEE LOG FOR ERRORS**'
        self.lblStatus['text'] = 'Ready...%s' %x


    def do_configfile(self, configDir, configFile):
        """Get options from config file in directory configDir."""
        log = self.startupLog

        cf = os.path.join(configDir, configFile)
        # can be symbolic link to a file, allow it
        if _path.isfile(cf):
            log.append('config file:\n    %s' %(quoted(cf)))
        else:
            log.append('config file (NOT FOUND):\n    %s' %(quoted(cf)))
            return

        options, errors = config_file_parser.parse(cf, OPT.options_table)
        if errors:
            log.extend(errors)
        if not options:
            return

        # verify color options for Treeview style: there is no error when
        # configuring style, but resultant gui may be broken
        f_ = tk.Frame(self.root) # dummy widget to check if color is valid
        for o in ('RESULTS_FG', 'RESULTS_BG', 'RESULTS_FIELD_BG'):
            if not options.get(o): continue
            try:
                f_.configure(background=options[o])
            except tk.TclError as e:
                log.append('**tkinter.TclError** while verifying color option %s:\n    %s' %(o, e))
                del options[o]

        # replace default option values with user values
        # copy.deepcopy() ?
        for o in options:
            setattr(OPT, o, options[o])


    def configure_tkFonts(self):
        fontTreview = tkFont.Font(family=OPT.FONT_RESULTS[0], size=OPT.FONT_RESULTS[1])
        # width of one letter W (usually the widest letter if proportional font)
        self.width_char = int(fontTreview.measure('W'*10) / 10)

        # Combobox and Entry fonts (ttk style does not work)
        tkFont.nametofont('TkTextFont').configure(family=OPT.FONT_TEXT[0], size=OPT.FONT_TEXT[1])
        #self.root.option_add('*TCombobox*font', OPT.FONT_TEXT)
        #self.root.option_add('*TEntry*font', OPT.FONT_TEXT)
        #self.root.option_add('*Listbox*font', OPT.FONT_TEXT)

        # Log font
        self.root.option_add('*Text*font', OPT.FONT_TEXT)

        # Menu font
        self.root.option_add('*Menu*font', OPT.FONT_LABEL)
        #tkFont.nametofont("TkMenuFont").configure(family=OPT.FONT_LABEL[0], size=OPT.FONT_LABEL[1])

        # almost all other fonts
        tkFont.nametofont('TkDefaultFont').configure(family=OPT.FONT_LABEL[0], size=OPT.FONT_LABEL[1])

        # fix bold heading font on Linux
        #tkFont.nametofont('TkHeadingFont').configure(weight='normal')

        # effective, but clobbers all fonts
        #self.root.option_add('*font', OPT.FONT_LABEL)

        # check if fonts are available
        sysfonts = tkFont.families()
        seen = {'Courier':0, 'Times':0, 'Helvetica':0}
        for fnt in (OPT.FONT_TEXT, OPT.FONT_RESULTS, OPT.FONT_HEADING, OPT.FONT_LABEL):
            f = fnt[0]
            if (f not in seen) and (f not in sysfonts):
                self.startupLog.append('**WARNING**: font family is not available:\n    %s' %repr(f))
            seen[f] = 0


    def configure_ttkStyle(self):
        # NOTE: When configuring ttk style, there is no error if font or color
        # is invalid, but resultant UI will likely be broken.
        # Thus, invalid font and color options must be thrown out while
        # processing config file.

        self.ttkStyle.configure('.', font=OPT.FONT_LABEL)
        self.ttkStyle.configure('Treeview', font=OPT.FONT_RESULTS)
        self.ttkStyle.configure('Heading', font=OPT.FONT_HEADING)

        # does not work, configure TkTextFont instead
        #self.ttkStyle.configure('TCombobox', font=OPT.FONT_TEXT)
        #self.ttkStyle.configure('TEntry', font=OPT.FONT_TEXT)

        # Treeview colors
        d = {}
        for (i, o) in (('foreground', OPT.RESULTS_FG),
                       ('background', OPT.RESULTS_BG),
                       ('fieldbackground', OPT.RESULTS_FIELD_BG)):
            if o:
                d[i] = o
        if d:
            self.ttkStyle.configure('Treeview', **d)

        # Tk default is 2, ttk themes other than classic use 1
        self.ttkStyle.configure('TCombobox', insertwidth=2)
        self.ttkStyle.configure('TEntry', insertwidth=2)


    def init_widgets(self, startupDir):
        root = self.root
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        master = ttk.Frame(root)
        self.master = master
        # make Treeview stretchable
        master.columnconfigure(0, weight=1)
        master.rowconfigure(0, weight=1)
        master.grid(in_=root, row=0, column=0, sticky=tk.NSEW)

        #=== master, row 0 ===========================================

        #--- Notebook: Treeview 'Results', Text 'Log' ----------------
        self.ntbkResults = ttk.Notebook(master)
        self.ntbkResults.grid(in_=master, row=0, column=0, sticky=tk.NSEW)

        ### Tab 'Results': Treeview
        frmResults = ttk.Frame(master)
        self.ntbkResults.add(frmResults, text='Results', sticky=tk.NSEW)

        ### Treeview
        # first columns, always present in "columns" and have values
        self.trvwColumnsA = ('FileType', 'Directory', 'Name', 'Ext', 'SIZE', 'Size')
        # other columns, optional, may be added to and removed from "columns"
        self.trvwColumnsB = ('MTIME', 'CTIME', 'ATIME', 'LinkTo', 'MODE', 'UID', 'GID', 'NLINK', 'INO')
        # all available columns
        self.trvwColumnsAB = self.trvwColumnsA + self.trvwColumnsB

        # displaycolumns
        displayColumns = []
        for cn in OPT.DISPLAYCOLUMNS:
            if (cn in self.trvwColumnsAB) and (cn not in displayColumns):
                displayColumns.append(cn)

        # displayed columns that are optional; their order MUST match that in "columns"
        self.trvwColumns2 = []
        for c in self.trvwColumnsB:
            if c in displayColumns:
                self.trvwColumns2.append(c)

        trvwColumns = list(self.trvwColumnsA) + self.trvwColumns2

        # show=('tree', 'headings',) # show both icon column '#0' and other columns
        self.trvwResults = ttk.Treeview(master, columns=trvwColumns, displaycolumns=displayColumns,
                                        show=('headings',), selectmode=tk.EXTENDED)
        _trvw = self.trvwResults

        # configure Treeview headings and columns
        self.init_trvw_kw()
        self.trvw_configure_cols(trvwColumns)

        # configure Treeview tags (do stripe last so it has the lowest priority)
        for (t, fg, bg) in (('d', OPT.RESULTS_DIR_FG,   OPT.RESULTS_DIR_BG),
                            ('l', OPT.RESULTS_LINK_FG,  OPT.RESULTS_LINK_BG),
                            ('o', OPT.RESULTS_OTHER_FG, OPT.RESULTS_OTHER_BG),
                            ('s', '',                   OPT.RESULTS_STRIPE_BG)):
            d = {}
            if fg: d['foreground'] = fg
            if bg: d['background'] = bg
            if not d: continue
            try:
                _trvw.tag_configure(t, **d)
            except tk.TclError as e:
                self.startupLog.append('**tkinter.TclError** while configuring Treeview tag (bad color option):\n    %s' %e)

        # font style of Treeview tags (config file options have been verified)
        for (t, stl) in (('d', OPT.RESULTS_DIR_STYLE),
                         ('l', OPT.RESULTS_LINK_STYLE),
                         ('o', OPT.RESULTS_OTHER_STYLE)):
            if not stl: continue
            try:
                _trvw.tag_configure(t, font=list(OPT.FONT_RESULTS[:2]) + [stl])
            except tk.TclError as e:
                self.startupLog.append('**tkinter.TclError** while configuring Treeview tag (bad font style option):\n    %s' %e)


        # Scrollbars for Treeview
        scbyTreeview = ttk.Scrollbar(master, orient=tk.VERTICAL)
        scbxTreeview = ttk.Scrollbar(master, orient=tk.HORIZONTAL)
        scbyTreeview.configure(command=_trvw.yview)
        scbxTreeview.configure(command=_trvw.xview)
        _trvw.configure(yscrollcommand=scbyTreeview.set, xscrollcommand=scbxTreeview.set)

        # grid Treeview and its scrollbars
        frmResults.columnconfigure(0, weight=1)
        frmResults.rowconfigure(0, weight=1)
        _trvw.grid(in_=frmResults, row=0, column=0, sticky=tk.NSEW)
        scbyTreeview.grid(in_=frmResults, row=0, column=1, sticky=tk.NS)
        scbxTreeview.grid(in_=frmResults, row=1, column=0, sticky=tk.EW)


        ### Tab 'Log': Text
        frmLog = ttk.Frame(master)
        self.ntbkResults.add(frmLog, text='Log', sticky=tk.NSEW)

        # Text 'Log'
        self.txtLog = tk.Text(master, undo=True, maxundo=20, wrap=tk.NONE)

        # Scrollbars for 'Log'
        scbyLog = ttk.Scrollbar(master, orient=tk.VERTICAL)
        scbxLog = ttk.Scrollbar(master, orient=tk.HORIZONTAL)
        scbyLog.configure(command=self.txtLog.yview)
        scbxLog.configure(command=self.txtLog.xview)
        self.txtLog.configure(yscrollcommand=scbyLog.set, xscrollcommand=scbxLog.set)

        # grid Log and its scrollbars
        frmLog.columnconfigure(0, weight=1)
        frmLog.rowconfigure(0, weight=1)
        self.txtLog.grid(in_=frmLog, row=0, column=0, sticky=tk.NSEW)
        scbyLog.grid(in_=frmLog, row=0, column=1, sticky=tk.NS)
        scbxLog.grid(in_=frmLog, row=1, column=0, sticky=tk.EW)


        #=== master, row 1: frmPanel =================================
        frmPanel = ttk.Frame(master) # no padding
        frmPanel.grid(in_=master, row=1, column=0, sticky=tk.NSEW)
        if not OPT.PANEL_IS_FIXED: # make bottom panel stretchable
            frmPanel.columnconfigure(0, weight=1)

        #--- frmPanel, row 0, col 0 ----------------------------------

        ### Combobox 'Directories'
        frm = ttk.Frame(master)
        frm.columnconfigure(1, weight=1)
        frm.grid(in_=frmPanel, row=0, column=0, sticky=tk.NSEW, pady=4)

        # label
        lblDir = ttk.Label(master, text='Directories:')
        lblDir.grid(in_=frm, row=0, column=0, sticky=tk.E)

        # combobox
        self.cmbbDir = ttk.Combobox(master, width=OPT.WIDTH_DIRECTORIES,
                                    values=OPT.DROPDOWN_DIRECTORIES)
        if startupDir:
            self.cmbbDir.insert(0, startupDir)
        else:
            tk_cmbb_insert(self.cmbbDir, OPT.DROPDOWN_DIRECTORIES)
        self.cmbbDir.grid(in_=frm, row=0, column=1, sticky=tk.EW)

        # Button for directory chooser
        self.btnDirChooser = ttk.Button(master, width=3, text='...',
                                        command=lambda: self.c_dir_chooser(self.cmbbDir))
        self.btnDirChooser.grid(in_=frm, row=0, column=2, sticky=tk.W, padx=4)

        # Checkbutton 'Recurse'
        self.var_ckbRecurse = tk.IntVar()
        self.ckbRecurse = ttk.Checkbutton(master, text='Recurse', variable=self.var_ckbRecurse)
        self.var_ckbRecurse.set(1)
        self.ckbRecurse.grid(in_=frm, row=0, column=3, sticky=tk.W)

        #--- frmPanel, row 0, col 1 ----------------------------------
        #frm = ttk.Frame(master)
        #frm.grid(in_=frmPanel, row=0, column=1, sticky=tk.NSEW, pady=4, padx=4)

        #--- frmPanel, row 1, col 0 ----------------------------------

        ### Notebook 'Filters:'
        self.ntbkFilters = ttk.Notebook(master)
        #self.ntbkFilters.columnconfigure(0, weight=1) # not needed
        self.ntbkFilters.grid(in_=frmPanel, row=1, column=0, sticky=tk.N + tk.EW)

        opm_match_modes = ['off', 'Exact', 'Contains', 'StartsWith', 'EndsWith', 'WildCard', 'RegExp']

        #### Tab 'Skipped dirs'
        frmTab = ttk.Frame(master)
        frmTab.columnconfigure(0, weight=1)
        self.ntbkFilters.add(frmTab, text='%sSkipped dirs' %TAB_OFF, sticky=tk.NSEW)
        frm = ttk.Frame(master, padding=4)
        frm.columnconfigure(1, weight=1)
        frm.grid(in_=frmTab, row=0, column=0, sticky=tk.NSEW)

        # ---1st row---

        # Label
        lblSkipDir = ttk.Label(master, text='Skip directories:')
        lblSkipDir.grid(in_=frm, row=0, column=0, sticky=tk.E)

        # Combobox
        self.cmbbSkipDir = ttk.Combobox(master, values=OPT.DROPDOWN_SKIP_DIRECTORIES)
        tk_cmbb_insert(self.cmbbSkipDir, OPT.DROPDOWN_SKIP_DIRECTORIES)
        self.cmbbSkipDir.grid(in_=frm, row=0, column=1, sticky=tk.EW)

        # Button for directory chooser
        self.btnSkipDirChooser = ttk.Button(master, width=3, text='...',
                command=lambda: self.c_dir_chooser(self.cmbbSkipDir))
        self.btnSkipDirChooser.grid(in_=frm, row=0, column=2, sticky=tk.W, padx=4)

        # ---2nd row---

        # frame for 2nd row
        frm2 = ttk.Frame(master)
        frm2.columnconfigure(1, weight=1)
        frm2.grid(in_=frm, row=1, column=0, columnspan=3, sticky=tk.NSEW)

        # Label
        lblSkipName = ttk.Label(master, text='Skip dirs with name:')
        lblSkipName.grid(in_=frm2, row=0, column=0, sticky=tk.E)

        # Combobox
        self.cmbbSkipName = ttk.Combobox(master, values=OPT.DROPDOWN_SKIP_DIRS_WITH_NAME)
        tk_cmbb_insert(self.cmbbSkipName, OPT.DROPDOWN_SKIP_DIRS_WITH_NAME)
        self.cmbbSkipName.grid(in_=frm2, row=0, column=1, sticky=tk.EW)

        # OptionMenu for match modes
        self.var_opmSkipNameMode = tk.StringVar()
        self.opmSkipNameMode = tk_make_optionmenu(master, self.var_opmSkipNameMode, opm_match_modes,
                                                  default='off', width=10)
        self.opmSkipNameMode.grid(in_=frm2, row=0, column=2, sticky=tk.EW, padx=4)

        # Checkbutton 'IgnoreCase'
        self.var_ckbSkipNameIC = tk.IntVar()
        self.ckbSkipNameIC = ttk.Checkbutton(master, text='IgnoreCase', variable=self.var_ckbSkipNameIC)
        self.var_ckbSkipNameIC.set(1)
        self.ckbSkipNameIC.grid(in_=frm2, row=0, column=3, sticky=tk.W)


        #### Tab 'Name'
        frmTab = ttk.Frame(master)
        frmTab.columnconfigure(0, weight=1)
        self.ntbkFilters.add(frmTab, text='%sName' %TAB_ON, sticky=tk.NSEW)
        frm = ttk.Frame(master, padding=4)
        frm.columnconfigure(1, weight=1)
        frm.grid(in_=frmTab, row=0, column=0, sticky=tk.NSEW)

        # ---1st row--- Name1

        # OptionMenu 'Name:'
        self.var_opmName1 = tk.StringVar()
        self.opmName1 = tk_make_optionmenu(master, self.var_opmName1, ['Name:', 'Not Name:'], default='Name:')
        self.opmName1.grid(in_=frm, row=0, column=0, sticky=tk.E)

        # Combobox
        self.cmbbName1 = ttk.Combobox(master, values=OPT.DROPDOWN_NAME_1)
        tk_cmbb_insert(self.cmbbName1, OPT.DROPDOWN_NAME_1)
        self.cmbbName1.grid(in_=frm, row=0, column=1, sticky=tk.EW)

        # OptionMenu for match modes
        self.var_opmName1Mode = tk.StringVar()
        self.opmName1Mode = tk_make_optionmenu(master, self.var_opmName1Mode, opm_match_modes,
                                               default='Contains', width=10)
        self.opmName1Mode.grid(in_=frm, row=0, column=2, sticky=tk.EW, padx=4)

        # Checkbutton 'IgnoreCase'
        self.var_ckbName1IC = tk.IntVar()
        self.ckbName1IC = ttk.Checkbutton(master, text='IgnoreCase', variable=self.var_ckbName1IC)
        self.var_ckbName1IC.set(1)
        self.ckbName1IC.grid(in_=frm, row=0, column=3, sticky=tk.W)

        # ---2nd row--- Name2

        # OptionMenu 'Name:'
        self.var_opmName2 = tk.StringVar()
        self.opmName2 = tk_make_optionmenu(master, self.var_opmName2, ['Name:', 'Not Name:'], default='Name:')
        self.opmName2.grid(in_=frm, row=1, column=0, sticky=tk.E)

        # Combobox
        self.cmbbName2 = ttk.Combobox(master, values=OPT.DROPDOWN_NAME_2)
        tk_cmbb_insert(self.cmbbName2, OPT.DROPDOWN_NAME_2)
        self.cmbbName2.grid(in_=frm, row=1, column=1, sticky=tk.EW)

        # OptionMenu for match modes
        self.var_opmName2Mode = tk.StringVar()
        self.opmName2Mode = tk_make_optionmenu(master, self.var_opmName2Mode, opm_match_modes,
                                               default='off', width=10)
        self.opmName2Mode.grid(in_=frm, row=1, column=2, sticky=tk.EW, padx=4)

        # Checkbutton 'IgnoreCase'
        self.var_ckbName2IC = tk.IntVar()
        self.ckbName2IC = ttk.Checkbutton(master, text='IgnoreCase', variable=self.var_ckbName2IC)
        self.var_ckbName2IC.set(1)
        self.ckbName2IC.grid(in_=frm, row=1, column=3, sticky=tk.W)


        #### Tab 'Path'
        frmTab = ttk.Frame(master)
        frmTab.columnconfigure(0, weight=1)
        self.ntbkFilters.add(frmTab, text='%sPath' %TAB_OFF, sticky=tk.NSEW)
        frm = ttk.Frame(master, padding=4)
        frm.columnconfigure(1, weight=1)
        frm.grid(in_=frmTab, row=0, column=0, sticky=tk.NSEW)

        # ---1st row--- Path1

        # OptionMenu 'Path:'
        self.var_opmPath1 = tk.StringVar()
        self.opmPath1 = tk_make_optionmenu(master, self.var_opmPath1, ['Path:', 'Not Path:'], default='Path:')
        self.opmPath1.grid(in_=frm, row=0, column=0, sticky=tk.E)

        # Combobox
        self.cmbbPath1 = ttk.Combobox(master, values=OPT.DROPDOWN_PATH_1)
        tk_cmbb_insert(self.cmbbPath1, OPT.DROPDOWN_PATH_1)
        self.cmbbPath1.grid(in_=frm, row=0, column=1, sticky=tk.EW)

        # OptionMenu for match modes
        self.var_opmPath1Mode = tk.StringVar()
        self.opmPath1Mode = tk_make_optionmenu(master, self.var_opmPath1Mode, opm_match_modes,
                                               default='Contains', width=10)
        self.opmPath1Mode.grid(in_=frm, row=0, column=2, sticky=tk.EW, padx=4)

        # Checkbutton 'IgnoreCase'
        self.var_ckbPath1IC = tk.IntVar()
        self.ckbPath1IC = ttk.Checkbutton(master, text='IgnoreCase', variable=self.var_ckbPath1IC)
        self.var_ckbPath1IC.set(1)
        self.ckbPath1IC.grid(in_=frm, row=0, column=3, sticky=tk.W)

        # ---2nd row--- Path2

        # OptionMenu 'Path:'
        self.var_opmPath2 = tk.StringVar()
        self.opmPath2 = tk_make_optionmenu(master, self.var_opmPath2, ['Path:', 'Not Path:'], default='Path:')
        self.opmPath2.grid(in_=frm, row=1, column=0, sticky=tk.E)

        # Combobox
        self.cmbbPath2 = ttk.Combobox(master, values=OPT.DROPDOWN_PATH_2)
        tk_cmbb_insert(self.cmbbPath2, OPT.DROPDOWN_PATH_2)
        self.cmbbPath2.grid(in_=frm, row=1, column=1, sticky=tk.EW)

        # OptionMenu for match modes
        self.var_opmPath2Mode = tk.StringVar()
        self.opmPath2Mode = tk_make_optionmenu(master, self.var_opmPath2Mode, opm_match_modes,
                                               default='off', width=10)
        self.opmPath2Mode.grid(in_=frm, row=1, column=2, sticky=tk.EW, padx=4)

        # Checkbutton 'IgnoreCase'
        self.var_ckbPath2IC = tk.IntVar()
        self.ckbPath2IC = ttk.Checkbutton(master, text='IgnoreCase', variable=self.var_ckbPath2IC)
        self.var_ckbPath2IC.set(1)
        self.ckbPath2IC.grid(in_=frm, row=1, column=3, sticky=tk.W)


        #### Tab 'Type'
        frmTab = ttk.Frame(master)
        frmTab.columnconfigure(0, weight=1)
        self.ntbkFilters.add(frmTab, text='%sType' %TAB_OFF, sticky=tk.NSEW)
        frm = ttk.Frame(master, padding=4)
        frm.columnconfigure(1, weight=1)
        frm.grid(in_=frmTab, row=0, column=0, sticky=tk.NSEW)

        # 1st row: Extension
        # OptionMenu
        self.var_opmExts = tk.StringVar()
        self.opmExts = tk_make_optionmenu(master, self.var_opmExts, ['Extension:', 'Not Extension:'], default='Extension:')
        self.opmExts.grid(in_=frm, row=0, column=0, sticky=tk.E)
        # Combobox
        self.cmbbExts = ttk.Combobox(master, values=OPT.DROPDOWN_EXTENSION)
        tk_cmbb_insert(self.cmbbExts, OPT.DROPDOWN_EXTENSION)
        self.cmbbExts.grid(in_=frm, row=0, column=1, sticky=tk.EW)

        # 2nd row: File type Checkbuttons
        ttk.Label(master, text='File type:').grid(in_=frm, row=1, column=0, sticky=tk.E)
        frm2 = ttk.Frame(master)
        frm2.grid(in_=frm, row=1, column=1, sticky=tk.W)
        self.var_ckbTypeF = tk.IntVar()
        self.ckbTypeF = ttk.Checkbutton(master, text='Regular file', variable=self.var_ckbTypeF)
        self.var_ckbTypeF.set('1')
        self.ckbTypeF.grid(in_=frm2, row=0, column=0, sticky=tk.W, padx=16)
        self.var_ckbTypeD = tk.IntVar()
        self.ckbTypeD = ttk.Checkbutton(master, text='Directory', variable=self.var_ckbTypeD)
        self.var_ckbTypeD.set('1')
        self.ckbTypeD.grid(in_=frm2, row=0, column=1, sticky=tk.W)
        self.var_ckbTypeL = tk.IntVar()
        self.ckbTypeL = ttk.Checkbutton(master, text='Symbolic link', variable=self.var_ckbTypeL)
        self.var_ckbTypeL.set('1')
        self.ckbTypeL.grid(in_=frm2, row=0, column=2, sticky=tk.W, padx=16)
        self.var_ckbTypeO = tk.IntVar()
        self.ckbTypeO = ttk.Checkbutton(master, text='Other', variable=self.var_ckbTypeO)
        self.var_ckbTypeO.set('1')
        self.ckbTypeO.grid(in_=frm2, row=0, column=3, sticky=tk.W)


        #### Tab 'Size'
        frmTab = ttk.Frame(master)
        frmTab.columnconfigure(0, weight=1)
        self.ntbkFilters.add(frmTab, text='%sSize' %TAB_OFF, sticky=tk.NSEW)
        frm = ttk.Frame(master, padding=4)
        frm.grid(in_=frmTab, row=0, column=0, sticky=tk.NSEW)

        self.entSize1 = ttk.Entry(master, width=20)
        self.entSize1.grid(in_=frm, row=0, column=0, sticky=tk.W)
        lbl = ttk.Label(master, text='<')
        lbl.grid(in_=frm, row=0, column=1, sticky=tk.EW, padx=8)
        self.var_opmSize = tk.StringVar()
        self.opmSize = tk_make_optionmenu(master, self.var_opmSize,
                            ['Size, bytes',
                            'Size, K', 'Size, M', 'Size, G', 'Size, T',
                            'Size, k', 'Size, m', 'Size, g', 'Size, t',],
                            default='Size, K', width=11)
        self.opmSize.grid(in_=frm, row=0, column=2, sticky=tk.W)
        lbl = ttk.Label(master, text='<')
        lbl.grid(in_=frm, row=0, column=3, sticky=tk.EW, padx=8)
        self.entSize2 = ttk.Entry(master, width=20)
        self.entSize2.grid(in_=frm, row=0, column=4, sticky=tk.W)


        #### Tab 'Time'
        frmTab = ttk.Frame(master)
        frmTab.columnconfigure(0, weight=1)
        self.ntbkFilters.add(frmTab, text='%sTime' %TAB_OFF, sticky=tk.NSEW)
        frm = ttk.Frame(master, padding=4)
        frm.grid(in_=frmTab, row=0, column=0, sticky=tk.NSEW)

        self.entTime1 = ttk.Entry(master, width=20)
        self.entTime1.grid(in_=frm, row=0, column=0, sticky=tk.W)
        lbl = ttk.Label(master, text='<')
        lbl.grid(in_=frm, row=0, column=1, sticky=tk.EW, padx=8)
        self.var_opmTime = tk.StringVar()
        self.opmTime = tk_make_optionmenu(master, self.var_opmTime,
                ['MTIME', 'CTIME', 'ATIME'], default='MTIME', width=5)
        self.opmTime.grid(in_=frm, row=0, column=2, sticky=tk.W)
        lbl = ttk.Label(master, text='<')
        lbl.grid(in_=frm, row=0, column=3, sticky=tk.EW, padx=8)
        self.entTime2 = ttk.Entry(master, width=20)
        self.entTime2.grid(in_=frm, row=0, column=4, sticky=tk.W)

        frm2 = ttk.Frame(master)
        frm2.grid(in_=frm, row=1, column=0, sticky=tk.W, columnspan=5)
        lbl = ttk.Label(master, text='Enter time as "YYYY-MM-DD HH:MM:SS". Copy time to clipboard:')
        lbl.pack(in_=frm2, side=tk.LEFT)
        self.btnTimeToClipboard = ttk.Button(master, text='Now', width=4, command=self.c_now_to_clipboard)
        self.btnTimeToClipboard.pack(in_=frm2, side=tk.LEFT)


        #### Tab 'Misc'
        frmTab = ttk.Frame(master)
        frmTab.columnconfigure(0, weight=1)
        self.ntbkFilters.add(frmTab, text='%sMisc' %TAB_OFF, sticky=tk.NSEW)
        frm = ttk.Frame(master, padding=4)
        frm.columnconfigure(1, weight=1)
        frm.grid(in_=frmTab, row=0, column=0, sticky=tk.NSEW)

        # 1st row
        frm1 = ttk.Frame(master)
        frm1.grid(in_=frm, row=0, column=0, columnspan=3, sticky=tk.W)
        # OptionMenu UID
        self.var_opmUID = tk.StringVar()
        self.opmUID = tk_make_optionmenu(master, self.var_opmUID, ['UID:', 'Not UID:'], default='UID:')
        self.opmUID.pack(in_=frm1, side=tk.LEFT)
        # Entry
        self.entUID = ttk.Entry(master, width=25)
        self.entUID.pack(in_=frm1, side=tk.LEFT)
        # OptionMenu GID
        self.var_opmGID = tk.StringVar()
        self.opmGID = tk_make_optionmenu(master, self.var_opmGID, ['GID:', 'Not GID:'], default='GID:')
        self.opmGID.pack(in_=frm1, side=tk.LEFT)
        # Entry
        self.entGID = ttk.Entry(master, width=25)
        self.entGID.pack(in_=frm1, side=tk.LEFT)
        # Label NLINK
        self.lblNLINK = ttk.Label(master, text='    NLINK >')
        self.lblNLINK.pack(in_=frm1, side=tk.LEFT)
        # Entry
        self.entNLINK = ttk.Entry(master, width=6)
        self.entNLINK.pack(in_=frm1, side=tk.LEFT)

        # 2nd row
        # OptionMenu MODE
        self.var_opmMODE = tk.StringVar()
        self.opmMODE = tk_make_optionmenu(master, self.var_opmMODE, ['MODE:', 'Not MODE:'], default='MODE:')
        self.opmMODE.grid(in_=frm, row=1, column=0, sticky=tk.E)
        # Combobox
        self.cmbbMODE = ttk.Combobox(master, values=OPT.DROPDOWN_MODE)
        tk_cmbb_insert(self.cmbbMODE, OPT.DROPDOWN_MODE)
        self.cmbbMODE.grid(in_=frm, row=1, column=1, sticky=tk.EW)
        # OptionMenu for match modes
        self.var_opmMODEMode = tk.StringVar()
        self.opmMODEMode = tk_make_optionmenu(master, self.var_opmMODEMode,
                                ['WildCard', 'RegExp'], default='RegExp', width=8)
        self.opmMODEMode.grid(in_=frm, row=1, column=2, sticky=tk.EW, padx=4)


        #### Tab 'Content'
        frmTab = ttk.Frame(master)
        frmTab.columnconfigure(0, weight=1)
        self.ntbkFilters.add(frmTab, text='%sContent' %TAB_OFF, sticky=tk.NSEW)
        frm = ttk.Frame(master, padding=4)
        frm.columnconfigure(1, weight=1)
        frm.grid(in_=frmTab, row=0, column=0, sticky=tk.NSEW)

        # ---1st row---
        # Label
        lblContLine = ttk.Label(master, text='Line:')
        lblContLine.grid(in_=frm, row=0, column=0, sticky=tk.E)
        # Entry
        self.entCont = ttk.Entry(master)
        self.entCont.grid(in_=frm, row=0, column=1, sticky=tk.EW)
        # OptionMenu for match modes
        self.var_opmContMode = tk.StringVar()
        self.opmContMode = tk_make_optionmenu(master, self.var_opmContMode,
                                ['Contains', 'StartsWith', 'WildCard', 'RegExp'],
                                default='Contains', width=8)
        self.opmContMode.grid(in_=frm, row=0, column=2, sticky=tk.EW, padx=4)
        # Checkbutton 'IgnoreCase'
        self.var_ckbContIC = tk.IntVar()
        self.ckbContIC = ttk.Checkbutton(master, text='IgnoreCase', variable=self.var_ckbContIC)
        self.var_ckbContIC.set(1)
        self.ckbContIC.grid(in_=frm, row=0, column=3, sticky=tk.W)

        # ---2nd row---
        # frame for 2nd row
        frm2 = ttk.Frame(master)
        frm2.grid(in_=frm, row=1, column=0, columnspan=4, sticky=tk.NSEW)

        # Label
        lblContEnc = ttk.Label(master, text='encoding=')
        lblContEnc.grid(in_=frm2, row=0, column=0, sticky=tk.E)
        # Combobox for encoding
        w0 = 16
        if OPT.DROPDOWN_ENCODING:
            w = max([len('%s' %i) for i in OPT.DROPDOWN_ENCODING])
            w0 = min(50, max(w0, w))
        self.cmbbContEnc = ttk.Combobox(master, width=w0, values=OPT.DROPDOWN_ENCODING)
        tk_cmbb_insert(self.cmbbContEnc, OPT.DROPDOWN_ENCODING)
        self.cmbbContEnc.grid(in_=frm2, row=0, column=1, sticky=tk.W)

        # Label
        lblContErrors = ttk.Label(master, text='    errors=')
        lblContErrors.grid(in_=frm2, row=0, column=2, sticky=tk.E)
        # OptionMenu
        self.var_opmContErrors = tk.StringVar()
        self.opmContErrors = tk_make_optionmenu(master, self.var_opmContErrors,
                                ['strict', 'ignore', 'replace', 'surrogateescape', 'backslashreplace'],
                                default='strict')
        self.opmContErrors.grid(in_=frm2, row=0, column=3, sticky=tk.W)

        # Label
        lblContNewline = ttk.Label(master, text='    newline=')
        lblContNewline.grid(in_=frm2, row=0, column=4, sticky=tk.E)
        # OptionMenu
        self.var_opmContNewline = tk.StringVar()
        self.opmContNewline = tk_make_optionmenu(master, self.var_opmContNewline,
                                ['None', "''", '\\n', '\\r', '\\r\\n'],
                                default='None')
        self.opmContNewline.grid(in_=frm2, row=0, column=5, sticky=tk.W)


        #--- frmPanel, row 1, col 1 ----------------------------------
        frm = ttk.Frame(master)
        frm.grid(in_=frmPanel, row=1, column=1, sticky=tk.NSEW)
        ### Buttons 'FIND', 'CANCEL'
        self.btnFIND = ttk.Button(master, text='FIND', width=7, command=self.c_btnFIND)
        self.btnFIND.grid(in_=frm, row=0, column=0, sticky=tk.W, padx=12)
        self.btnCANCEL = ttk.Button(master, text='CANCEL', width=7, command=self.c_btnCANCEL, state=tk.DISABLED)
        self.btnCANCEL.grid(in_=frm, row=1, column=0, sticky=tk.W, padx=12, pady=8)


        #=== master, row 2: Statusbar + Sizegrip =====================
        frmStatus = ttk.Frame(master)
        frmStatus.grid(in_=master, row=2, column=0, sticky=tk.EW)
        self.lblStatus = ttk.Label(master, borderwidth=1, relief=tk.SUNKEN, anchor=tk.W)
        ttk.Sizegrip(frmStatus).pack(in_=frmStatus, side=tk.RIGHT) # pack it first so it stays when resizing over text
        self.lblStatus.pack(in_=frmStatus, side=tk.LEFT, fill=tk.BOTH, expand=1)


    def init_trvw_kw(self):
        """Create dicts that will be used to configure Treeview headings and columns."""
        wi = self.width_char # width of one letter

        # defaults: stretch=1, width=200, minwidth=20

        self.trvwHeadingKW, self.trvwColumnKW = {}, {}
        headingKW, columnKW = self.trvwHeadingKW, self.trvwColumnKW
        for c in self.trvwColumnsAB:
            headingKW[c] = {'text': c, 'anchor': tk.W,
                            'command': lambda c_=c: self.c_trvw_sort('', c_), }
            columnKW[c] = {'stretch': 0, 'anchor': tk.W, }

        headingKW['FileType']['text'] = ''
        columnKW['FileType']['width'] = 3*wi
        columnKW['FileType']['minwidth'] = 3*wi

        w = 40*wi
        for c in ('Directory', 'Name'):
            columnKW[c]['width'] = w
            columnKW[c]['stretch'] = 1

        columnKW['Ext']['width'] = 6*wi

        columnKW['SIZE']['width'] = 10*wi
        columnKW['Size']['width'] = 7*wi
        headingKW['SIZE']['anchor'] = tk.E
        columnKW['SIZE']['anchor'] = tk.E
        headingKW['Size']['anchor'] = tk.E
        columnKW['Size']['anchor'] = tk.E

        columnKW['LinkTo']['width'] = 10*wi

        w = 21*wi # YYYY-MM-DD HH:MM:SS + two spaces
        for c in ('MTIME', 'CTIME', 'ATIME'):
            columnKW[c]['width'] = w

        columnKW['MODE']['width'] = 13*wi
        headingKW['MODE']['anchor'] = tk.E
        columnKW['MODE']['anchor'] = tk.E

        w = 9*wi
        for c in ('UID', 'GID', 'NLINK', 'INO'):
            columnKW[c]['width'] = w
            headingKW[c]['anchor'] = tk.E
            columnKW[c]['anchor'] = tk.E


    def trvw_configure_cols(self, colNames):
        """Configure Treeview headings and columns."""
        for c in colNames:
            self.trvwResults.heading(c, **self.trvwHeadingKW[c])
            self.trvwResults.column(c, **self.trvwColumnKW[c])


    def init_menubar(self):
        mnBar = tk.Menu(self.root, tearoff=0)
        self.root.config(menu=mnBar)

        # Menu 'File'
        mnFile = tk.Menu(mnBar, tearoff=0)
        #mnFile.add_separator()
        mnFile.add_command(label='Exit', underline=1, accelerator='Alt+F4', command=self.c_quit_app)
        mnBar.add_cascade(label='File', underline=0, menu=mnFile)

        # Menu 'Edit'
        mnEdit = tk.Menu(mnBar, tearoff=0, postcommand=self.c_mnEdit)
        mnEdit.add_command(label='Delete', underline=0, command=self.c_trvw_delete)
        mnBar.add_cascade(label='Edit', underline=0, menu=mnEdit)

        # Menu 'View'
        mnView = tk.Menu(mnBar, tearoff=0)
        mnBar.add_cascade(label='View', underline=0, menu=mnView)

        mnToggleCols = tk.Menu(mnBar, tearoff=1)
        mnView.add_cascade(label='Columns', underline=0, menu=mnToggleCols)
        # checkbutton menu for each Treeview column to hide/show
        self.vars_ckbToggleCol = {} # to save vars, otherwise checkbuttons don't init properly
        dispCols = self.trvwResults['displaycolumns']
        for cn in self.trvwColumnsAB:
            var_ckbToggleCol = tk.IntVar()
            self.vars_ckbToggleCol[cn] = var_ckbToggleCol
            mnToggleCols.add_checkbutton(label=cn,
                    command=lambda cn_=cn: self.c_trvw_toggle_col(cn_),
                    variable=var_ckbToggleCol)
            var_ckbToggleCol.set(int((cn in dispCols)))

        mnTheme = tk.Menu(mnBar, tearoff=1)
        mnView.add_cascade(label='Ttk Theme', underline=0, menu=mnTheme)
        # radiobutton menu for each available ttk Themes
        self.var_rdbTtkTheme = tk.StringVar()
        for th in self.ttkThemes:
            mnTheme.add_radiobutton(label=th,
                    command=lambda th_=th: self.c_apply_ttkTheme(th_),
                    variable=self.var_rdbTtkTheme,
                    value=th)
        self.var_rdbTtkTheme.set(self.ttkStyle.theme_use())

        # Menu 'Help'
        mnHelp = tk.Menu(mnBar, tearoff=0)
        mnHelp.add_command(label='README.html', underline=0, command=self.c_readme)
        mnBar.add_cascade(label='Help', underline=0, menu=mnHelp)

        self.mnEdit = mnEdit # need it for postcommand

        # list of menus that need to be disabled during FIND
        self.visibleMenus = (mnBar, mnToggleCols, mnTheme, )


    def c_mnEdit(self):
        """postcommand for menu Edit: disable menu commands when Results tab is
        not visible or has no selection."""
        if self._isBusy: return

        if self.trvwResults.selection() and self.ntbkResults.index(self.ntbkResults.select()) == 0:
            st = tk.NORMAL
        else:
            st = tk.DISABLED
        self.mnEdit.entryconfigure(0, state=st)


    def make_pmenuLog(self):
        """Popup menu for r-click in Log text widget."""
        txtLog = self.txtLog
        mn = tk.Menu(txtLog, tearoff=0)
        # Note: indices are used to enable/disable Copy, Paste, Delete
        mn.add_command(label='Copy', command=lambda: txtLog.event_generate('<<Copy>>'))
        mn.add_command(label='Paste', command=lambda: txtLog.event_generate('<<Paste>>'))
        mn.add_command(label='Delete', command=lambda: txtLog.event_generate('<<Clear>>'))
        mn.add_separator()
        mn.add_command(label='Select All', command=lambda: txtLog.event_generate('<<SelectAll>>'))
        return mn


    def c_log_rclick(self, event):
        """Command for popping up r-click menu in Log text widget."""
        if self._isBusy: return

        pmenuLog = self.pmenuLog

        # disable Copy, Delete if no text is selected
        if self.txtLog.tag_ranges('sel'): st = tk.NORMAL
        else: st = tk.DISABLED
        pmenuLog.entryconfigure(0, state=st)
        pmenuLog.entryconfigure(2, state=st)

        # disable Paste if clipboard is empty
        if tk_clipboard_get(self.root): st = tk.NORMAL
        else: st = tk.DISABLED
        pmenuLog.entryconfigure(1, state=st)

        self.txtLog.focus_set()
        pmenuLog.tk_popup(event.x_root, event.y_root)


    def make_pmenuHeading(self):
        """Popup menu for r-click on heading row in Treeview."""
        mn = tk.Menu(self.trvwResults, tearoff=0)

        mn.add_command(label='Fit',              command=lambda: self.c_trvw_fit(False,False))
        mn.add_command(label='Fit with Max',     command=lambda: self.c_trvw_fit(True,False))
        mn.add_command(label='Fit All',          command=lambda: self.c_trvw_fit(False,True))
        mn.add_command(label='Fit All with Max', command=lambda: self.c_trvw_fit(True,True))

        mn.add_separator()

        mn.add_command(label='Sort Low-to-High%s' %SL2H, command=lambda: self.c_trvw_sort('lowtohigh'))
        mn.add_command(label='Sort High-to-Low%s' %SH2L, command=lambda: self.c_trvw_sort('hightolow'))

        return mn


    def make_pmenuResults(self):
        """Popup menu for r-click on an item row in Treeview."""
        mn = tk.Menu(self.trvwResults, tearoff=0)

        mn.add_command(label='Open',                 command=lambda: self.c_trvw_open('open'))
        mn.add_command(label='Open in File Manager', command=lambda: self.c_trvw_open('open_fm'))
        if OPT.OPEN_EXTRA:
            for lbl, c in OPT.OPEN_EXTRA:
                mn.add_command(label=lbl, command=lambda cmd=c: self.c_trvw_open('open_with', menucmd=cmd))
        if OPT.OPEN_WITH:
            mnOpenWith = tk.Menu(mn, tearoff=0)
            mn.add_cascade(label='Open With', menu=mnOpenWith)
            for lbl, c in OPT.OPEN_WITH:
                mnOpenWith.add_command(label=lbl, command=lambda cmd=c: self.c_trvw_open('open_with', menucmd=cmd))

        mn.add_separator()
        mn.add_command(label='Copy Path',      command=lambda: self.c_trvw_copy_value('Path',0,0))
        mn.add_command(label='Copy Directory', command=lambda: self.c_trvw_copy_value('Directory',0,0))
        mn.add_command(label='Copy Name',      command=lambda: self.c_trvw_copy_value('Name',0,0))

        mnAll = tk.Menu(mn, tearoff=0)
        mn.add_cascade(label='All Selected', menu=mnAll)
        mnAll.add_command(label='Copy Paths',       command=lambda: self.c_trvw_copy_value('Path',1,0))
        mnAll.add_command(label='Copy Directories', command=lambda: self.c_trvw_copy_value('Directory',1,0))
        mnAll.add_command(label='Copy Names',       command=lambda: self.c_trvw_copy_value('Name',1,0))

        #mnAll.add_separator()
        mnLinewise = tk.Menu(mnAll, tearoff=0)
        mnAll.add_cascade(label='Copy Linewise', menu=mnLinewise)
        mnLinewise.add_command(label='Copy Paths',       command=lambda: self.c_trvw_copy_value('Path',1,1))
        mnLinewise.add_command(label='Copy Directories', command=lambda: self.c_trvw_copy_value('Directory',1,1))
        mnLinewise.add_command(label='Copy Names',       command=lambda: self.c_trvw_copy_value('Name',1,1))
        mnLinewise.add_separator()
        mnLinewise.add_command(label='Copy Rows as Table', command=self.c_trvw_copy_rows)

        mnAll.add_separator()
        mnAll.add_command(label='Selection Stats', command=self.c_trvw_selstats)

        mn.add_separator()
        mn.add_command(label='Properties', command=self.c_trvw_properties)

        return mn


    def c_trvw_rclick(self, event):
        """Command for popping up r-click menus in Treeview"""
        if self._isBusy: return

        _trvw = self.trvwResults
        _trvw.focus_set()

        # find out what is under the mouse click in Treeview

        # region ID: nothing, heading, separator, tree, cell
        rID = _trvw.identify_region(event.x, event.y)

        # item ID; '' if header row or emtpy area
        iID = _trvw.identify_row(event.y)

        # column ID: '#0', '#1', '#2', etc; '' if field outside columns
        cID = _trvw.identify_column(event.x)
        # ignore clicks on background and tree column
        if not cID or cID == '#0':
            return

        # save IDs for popup menus; cID must be converted to column name
        self._popCID = _trvw.column(cID, option='id')
        self._popIID = iID

        #print('cID="%s", self._popCID="%s", rID="%s", iID="%s"' %(cID,  self._popCID, rID, iID))
        #print(_trvw.set(iID))

        if rID == 'heading':
            # pop up menu for headings
            self.pmenuHeading.tk_popup(event.x_root, event.y_root)
            return
        elif rID == 'cell': # tree column not included
            if not iID: # empty area
                return
            selectedItems = _trvw.selection() # tuple of iID's of selected items
            # if item under mouse is not selected: select it, deselect other
            if iID not in selectedItems:
                _trvw.focus(iID)
                _trvw.selection_set(iID)
                self._popIIDS = (iID,)
            else:
                _trvw.focus(iID)
                self._popIIDS = selectedItems
            # pop up menu for items
            self.pmenuResults.tk_popup(event.x_root, event.y_root)
            return
        else:
            return


    def c_apply_ttkTheme(self, th):
        """Change ttk theme to th."""
        if self._isBusy: return
        try:
            self.ttkStyle.theme_use(th)
            self.configure_ttkStyle()
        except tk.TclError as e:
            msgbox_error('%s' %e)


    def c_rslts_focusin(self, event):
        """Put focus on tab's content, that is on Treeview or Log widget."""
        if self._isBusy: return
        if self.ntbkResults.index(self.ntbkResults.select()) == 0:
            self.trvwResults.focus_set()
        else:
            self.txtLog.focus_set()


    def c_rslts_switchtab(self, event):
        """Switch to another tab in notebook Results."""
        if self._isBusy: return
        ntbk = self.ntbkResults
        tabNew = int(not ntbk.index(ntbk.select()))
        ntbk.select(tabNew)
        if tabNew == 0:
            self.trvwResults.focus_set()
        else:
            self.txtLog.focus_set()


    def c_toggle_filter(self, event):
        """Toggle sign on tab in notebook Filters on/off."""
        if self._isBusy: return

        ntbk = self.ntbkFilters
        if event.keysym == 'space':
            tabClicked = ntbk.index(ntbk.select())
        else:
            # "" when clicked on empty part of tab line
            tabClicked = ntbk.tk.call(ntbk._w, 'identify', 'tab', event.x, event.y)
        if not isinstance(tabClicked, int) or tabClicked < 0:
            return
        text = ntbk.tab(tabClicked, option='text')
        if text.startswith(TAB_OFF):
            txt = '%s%s' %(TAB_ON, text[len(TAB_OFF) : ])
        elif text.startswith(TAB_ON):
            txt = '%s%s' %(TAB_OFF, text[len(TAB_ON) : ])
        ntbk.tab(tabClicked, text=txt)


    def c_dir_chooser(self, w):
        if self._isBusy: return

        # choose initialdir: last dir in combobox, or home dir
        # dir chooser dosn't care if initialdir is "" or does not exist
        dirstringOld = w.get() # get text from combobox widget
        inputDirs = inpstr_to_items(dirstringOld, sep='|')
        if inputDirs:
            initialdir = inputDirs[-1]
            initialdir = full_path(initialdir)
        else:
            initialdir = _path.expandvars('$HOME')

        dirAsk = tkFileDialog.askdirectory(initialdir=initialdir)
        if not dirAsk:
            return

        if '|' in dirstringOld:
            dirstringNew = '%s|%s' %(dirstringOld.rsplit('|', 1)[0], dirAsk)
        else:
            dirstringNew = dirAsk
        w.set(dirstringNew) # set text in combobox widget


    def c_quit_app(self):
        if self._isBusy: return
        else: self.root.destroy()


    def c_readme(self):
        """Open README.html with associated program."""
        if self._isBusy: return
        startfile(_path.join(PROGRAMDIR, 'README.html'), self.log_put)


    def c_now_to_clipboard(self):
        if self._isBusy: return
        txt = time.strftime(TIME_FORMAT, time.localtime(time.time()))
        tk_clipboard_put(self.root, txt)


    def c_trvw_toggle_col(self, colName):
        """If column is displayed, remove it. If not, display it."""
        if self._isBusy: return

        _trvw = self.trvwResults
        dispcols = list(_trvw['displaycolumns'])

        # column always stays in "columns", only "displaycolumns" is changed
        if colName in self.trvwColumnsA:
            if colName in dispcols:
                dispcols.remove(colName)
            else:
                if colName == 'Size' and 'SIZE' in dispcols:
                    dispcols.insert(dispcols.index('SIZE') + 1, colName)
                elif colName == 'SIZE' and 'Size' in dispcols:
                    dispcols.insert(dispcols.index('Size'), colName)
                else:
                    dispcols.append(colName)
            _trvw['displaycolumns'] = dispcols
            return

        # column is also removed from or added to "columns"
        # this means Treeview must be cleared of data, columns reconfigured
        cols = list(_trvw['columns'])
        if colName in dispcols:
            dispcols.remove(colName)
            cols.remove(colName)
        else:
            dispcols.append(colName)
            cols.append(colName)

        _trvw.delete(*_trvw.get_children())
        self.RSLTS = []
        _trvw['displaycolumns'] = [] # needed when removing
        _trvw['columns'] = cols
        _trvw['displaycolumns'] = dispcols
        self.trvw_configure_cols(cols)

        # MUST match the order in cols
        self.trvwColumns2 = []
        for c in cols:
            if c in self.trvwColumnsB:
                self.trvwColumns2.append(c)


    def c_trvw_sort(self, how, c=None):
        """Sort Treeview column."""
        if self._isBusy: return

        _trvw = self.trvwResults

        # called from left-click on heading; toggle sort order
        if c:
            cID = c
            h = _trvw.heading(c, option='text')
            if h.endswith(SL2H):
                isReverse = True
            elif h.endswith(SH2L):
                isReverse = False
            else: # unsorted
                isReverse = False
        # called from right-click popup menu on heading
        else:
            cID = self._popCID # saved previously on r-click before popup menu
            if how == 'lowtohigh':
                isReverse = False
            elif how == 'hightolow':
                isReverse = True

        if isReverse:
            hSign = SH2L
        else:
            hSign = SL2H

        ### remove old sort sign
        self.trvw_remove_sort_sign(self._sortedCID)
        self._sortedCID = ''

        ### sort
        # sort data table and put it into Treeview (almost same as during FIND)

        # clear Treeview
        _trvw.delete(*_trvw.get_children())

        # sort items
        _cols = _trvw['columns']
        colName = cID
        if colName == 'Size': # when sorting by size, always sort by actual size in bytes
            colName = 'SIZE'
        idx = _cols.index(colName)
        self.RSLTS.sort(key=lambda j: j[idx], reverse=isReverse)

        # put sorted items into Treeview
        self.trvw_populate(self.RSLTS)

        ### put sort sign in the heading of sorted column
        h = '%s%s' %(_trvw.heading(cID, option='text'), hSign)
        _trvw.heading(cID, text=h)
        self._sortedCID = cID


    def c_trvw_fit(self, fitmax, doall):
        """Adjust width of Treeview column(s) to fit content.
        If `fitmax`, do not exceed max width.
        If `doall`, adjust all columns. If not, clicked column only.
        """
        if self._isBusy: return

        _trvw = self.trvwResults
        if doall:
            columns = _trvw['displaycolumns']
        else:
            columns = (self._popCID, )

        for cn in columns:
            if cn == 'FileType':
                wi = self.width_char * 3
                _trvw.column(cn, width=wi)
                continue
            cnx = _trvw['columns'].index(cn)
            maxlen = len(_trvw.heading(cn, option='text')) + 1
            for row in self.RSLTS:
                l = len('%s' % row[cnx])
                if l > maxlen:
                    maxlen = l
            # add extra space to compensate for lack of gridlines
            wi = self.width_char * (maxlen+2)
            if fitmax:
                wi = min(wi, OPT.FIT_MAX_WIDTH)
            _trvw.column(cn, width=wi)


    def c_trvw_copy_value(self, colName, allsel, linewise):
        """Called from popup menu on Treeview items.
        Copy to clipboard value in colName: Path, Directory, Name."""
        if self._isBusy: return

        _cols = self.trvwResults['columns']
        _RSLTS = self.RSLTS

        # copy for one item under the cursor
        if not allsel:
            itx = int(self._popIID) - 1
            if colName == 'Path':
                cnxD, cnxN = _cols.index('Directory'), _cols.index('Name')
                v = _join(_RSLTS[itx][cnxD], _RSLTS[itx][cnxN])
            else:
                cnxX = _cols.index(colName)
                v = _RSLTS[itx][cnxX]
            tk_clipboard_put(self.root, v)
            return

        # copy for all selected items
        vals = []
        itxs = [(int(i) - 1) for i in self._popIIDS]
        #itxs.sort() # not needed

        if colName == 'Path':
            cnxD, cnxN = _cols.index('Directory'), _cols.index('Name')
            for itx in itxs:
                v = _join(_RSLTS[itx][cnxD], _RSLTS[itx][cnxN])
                vals.append(v)
        else:
            cnxX = _cols.index(colName)
            for itx in itxs:
                v = _RSLTS[itx][cnxX]
                vals.append(v)

        # copy line-wise: put each value on a separate line
        if linewise:
            txt = '\n'.join(vals)
        # copy as one line: put each value in quotes and join into one line
        else:
            vals = [quoted(v) for v in vals]
            txt = ' '.join(vals)

        tk_clipboard_put(self.root, txt)


    def c_trvw_copy_rows(self):
        """Copy to clipboard rows of selected items as formatted table."""
        if self._isBusy: return

        _trvw = self.trvwResults
        _cols = _trvw['columns']
        dispcols = _trvw['displaycolumns']
        _RSLTS = self.RSLTS

        cnxs = []
        maxlens, anchors = {}, {}
        firstrow = []
        for cn in dispcols:
            cnx = _cols.index(cn)
            cnxs.append(cnx)
            maxlens[cnx] = len(_trvw.heading(cn, option='text'))
            anchors[cnx] = str(_trvw.column(cn, option='anchor')) == str(tk.W)
            firstrow.append(_trvw.heading(cn, option='text'))

        itxs = [(int(i) - 1) for i in self._popIIDS]
        #itxs.sort() # not needed

        # iterate over selected items to get maximum width of each column
        for itx in itxs:
            items = _RSLTS[itx]
            for cnx in cnxs:
                val = items[cnx]
                wi = len('%s' % val)
                if wi > maxlens[cnx]:
                    maxlens[cnx] = wi

        table = []

        # first row of table: headings
        row = ''
        for i, cnx in enumerate(cnxs):
            val = firstrow[i]
            if anchors[cnx]:
                row += '%-*s|' %(maxlens[cnx], val)
            else:
                row +=  '%*s|' %(maxlens[cnx], val)
        table.append(row)

        # iterate over selected items again and construct the table
        for itx in itxs:
            row = ''
            items = _RSLTS[itx]
            for cnx in cnxs:
                val = items[cnx]
                if anchors[cnx]:
                    row += '%-*s|' %(maxlens[cnx], val)
                else:
                    row +=  '%*s|' %(maxlens[cnx], val)
            table.append(row)

        #table.append('')
        txt = '\n'.join(table)
        tk_clipboard_put(self.root, txt)


    def c_trvw_kb_selectall(self, event):
        """Select all items in Treeview."""
        if self._isBusy: return
        self.trvwResults.selection_set(self.trvwResults.get_children())


    def c_trvw_kb_scroll(self, event):
        """Treeview scrolling actions."""
        if self._isBusy: return
        l = len(self.trvwResults.get_children())
        if not l: return
        keysym = event.keysym
        #print(keysym)
        if keysym in ('KP_Home', 'Home'):
            self.trvwResults.see('1')
        elif keysym in ('KP_End', 'End'):
            self.trvwResults.see(str(l))
        elif keysym == 'KP_Prior': # PageUp
            self.trvwResults.event_generate('<Prior>')
        elif keysym == 'KP_Next': # PageDown
            self.trvwResults.event_generate('<Next>')


    def c_trvw_mb_open(self, event):
        """Treeview mouse click binding to Open item."""
        if self._isBusy: return
        iID = self.trvwResults.identify_row(event.y)
        cID = self.trvwResults.identify_column(event.x)
        if not iID or not cID or cID == '#0':
            return
        self.c_trvw_open('open', iID=iID)


    def c_trvw_kb_open(self, event):
        """Treeview key binding to Open item."""
        if self._isBusy: return
        iID = self.trvwResults.focus()
        if not iID: return
        self.c_trvw_open('open', iID=iID)


    def c_trvw_open(self, how, iID=None, menucmd=None):
        """Open Treeview item with external program."""
        if self._isBusy: return

        if not iID: # called from popup menu
            iID = self._popIID
        itx = int(iID) - 1
        _cols = self.trvwResults['columns']
        di = self.RSLTS[itx][_cols.index('Directory')]
        na = self.RSLTS[itx][_cols.index('Name')]
        pa = _join(di, na)

        if how == 'open':
            cmd = OPT.OPEN.strip()
            if not cmd:
                startfile(pa, self.log_put)
                return
        elif how == 'open_fm':
            cmd = OPT.OPEN_FM.strip()
            if not cmd:
                startfile(di, self.log_put)
                return
        elif how == 'open_with':
            cmd = menucmd

        try:
            args1 = shlex.split(cmd) # can raise exception (unmatched ' or ")
        except Exception as e:
            emsg = e_info(e)
            msgbox_error('**Exception** (see Log for details):%s' %emsg)
            self.log_put(LHR)
            self.log_put('**Exception**:%s' %emsg)
            self.log_put('caused by: shlex.split(cmd)\ncmd = %s' %repr(cmd), True)
            return

        args2 = expand_placeholders(args1, {'%P':pa, '%D':di, '%N':na})

        try:
            pid = subprocess.Popen(args2).pid
        except Exception as e:
            emsg = e_info(e)
            msgbox_error('**Exception** (see Log for details):%s' %emsg)
            self.log_put(LHR)
            self.log_put('**Exception**:%s' %emsg)
            self.log_put('caused by: subprocess.Popen(args2)')
            self.log_put('args2 (after expanding placeholders in args1) =\n    %s' %args2)
            self.log_put('args1 (after shlex.split(cmd)) =\n    %s' %args1)
            self.log_put('cmd =\n    %s' %repr(cmd), True)


    def c_trvw_properties(self, event=None):
        """Print to Log properties of the current Treeview item."""
        if self._isBusy: return

        if event: # called from key press
            iID = self.trvwResults.focus()
            if not iID: return
        else: # called from popup menu
            iID = self._popIID
        itx = int(iID) - 1

        _cols = self.trvwResults['columns']
        di = self.RSLTS[itx][_cols.index('Directory')]
        na = self.RSLTS[itx][_cols.index('Name')]
        pa = _join(di, na)

        props = file_properties(pa)
        self.log_put(LHR)
        self.log_put('%sFILE PROPERTIES%s' %(LD1, LD2))
        self.log_put('\n'.join(props))
        self.log_show()


    def c_trvw_selstats(self):
        """Print to Log statistics for items selected in Treeview."""
        if self._isBusy: return

        _RSLTS = self.RSLTS
        _cols = self.trvwResults['columns']
        cnxFT, cnxSIZE = _cols.index('FileType'), _cols.index('SIZE')

        # count file types and their sizes: directory, regular file, symlink, other
        fileTypes = {'-':0, 'd':0, 'l':0, 'other':0}
        fileSizes = {'-':0, 'd':0, 'l':0, 'other':0}
        totalSize = 0
        for iid in self._popIIDS:
            itx = int(iid) - 1
            ft = _RSLTS[itx][cnxFT]
            if ft not in fileTypes:
                ft = 'other'
            fileTypes[ft] += 1
            b = _RSLTS[itx][cnxSIZE]
            fileSizes[ft] += b
            totalSize += b

        m = len('%s' % max(list(fileTypes.values()) + [len(self._popIIDS)]))
        res =   []
        for (txt, cnt, b) in [
                ('       all items: ', len(self._popIIDS), totalSize),
                ('   regular files: ', fileTypes['-'], fileSizes['-']),
                ('     directories: ', fileTypes['d'], fileSizes['d']),
                ('  symbolic links: ', fileTypes['l'], fileSizes['l']),
                ('           other: ', fileTypes['other'], fileSizes['other']),
                ]:
            s = '%s%*s' %(txt, m, cnt)
            if b >= 1024:
                x = ', %s, %s' % (bytes2size(b,'kibi'), bytes2size(b,'kilo'))
            else:
                x = ''
            s += ' (%s bytes%s)' % (b, x)
            res.append(s)

        self.log_put(LHR)
        self.log_put('%sSELECTION STATS%s' %(LD1, LD2))
        self.log_put('\n'.join(res))
        self.log_show()


    def c_trvw_delete(self):
        """Delete file items selected in Treeview."""
        if self._isBusy: return

        global shutil
        if shutil is None:
            import shutil
        _trvw = self.trvwResults
        _RSLTS = self.RSLTS
        _cols = _trvw['columns']
        cnxFT, cnxD, cnxN = _cols.index('FileType'), _cols.index('Directory'), _cols.index('Name')
        selectedItems = _trvw.selection()
        itxs = [(int(i) - 1) for i in selectedItems]

        # verify itxs
        ok, msg = self.verify_itxs(selectedItems, itxs, cnxFT, cnxD, cnxN)
        if not ok:
            msgbox_error('DELETE ABORTED.\nINTERNAL ERROR.\nSee Log for details.')
            self.log_put(LHR)
            self.log_put('****************** DELETE ABORTED. INTERNAL ERROR. *******************')
            self.log_put('verify_itxs() failed with the following message:\n%s' %msg, True)
            return

        # show confirmation dialog
        lenItems = len(itxs)
        if not lenItems: return
        if lenItems == 1:
            itx = itxs[0]
            ft, di, na = _RSLTS[itx][cnxFT], _RSLTS[itx][cnxD], _RSLTS[itx][cnxN]
            pa = _join(di, na)
            ft_desc = '%s (%s)' %(ft, FT_DESCRIP.get(ft, 'n/a'))
            msg = 'Are you sure you want to\nPERMANENTLY DELETE this file?\n\nPath: %s\n\nName: %s\n\nType: %s' % (quoted(pa), quoted(na), ft_desc)
            yesno = tkMessageBox.askyesno('%s -- Delete File' % TITLE,
                                          msg, default=tkMessageBox.NO, icon=tkMessageBox.WARNING)
        else:
            msg = 'Are you sure you want to\nPERMANENTLY DELETE these %s files?' % (lenItems)
            yesno = tkMessageBox.askyesno('%s -- Delete Multiple Files' % TITLE,
                                          msg, default=tkMessageBox.NO, icon=tkMessageBox.WARNING)
        if not yesno: return

        # do delete
        self.lblStatus['text'] = 'deleting files...'
        self.master.update_idletasks()
        pa_deleted, itx_deleted, pa_notdeleted = [], [], []
        for n, itx in enumerate(itxs):
            pa = _join(_RSLTS[itx][cnxD], _RSLTS[itx][cnxN])
            ft = _RSLTS[itx][cnxFT]
            itxs[n] = (pa, ft, itx)
        # reverse-sort by path to ensure that files in subdirs are deleted first
        itxs.sort(reverse=True)
        for pa, ft, itx in itxs:
            if OPT.DELETE_IS_ENABLED:
                # do the actual delete
                ok, msg = delete_one_file(pa, ft)
            else:
                ok, msg = False, 'DELETE_IS_ENABLED=False'
            if ok:
                pa_deleted.append(quoted(pa))
                itx_deleted.append(itx)
            else:
                pa_notdeleted.append('%s\n    %s' % (quoted(pa), msg))

        # remove delete items from RSLTS, update display
        if itx_deleted:
            self.lblStatus['text'] = 'displaying...'
            self.master.update_idletasks()
            itx_deleted.sort(reverse=True)
            for itx in itx_deleted:
                del _RSLTS[itx]
            _trvw.delete(*_trvw.get_children())
            self.trvw_populate(_RSLTS)

        statusmsg = 'Deleted %s files.' % len(pa_deleted)
        self.log_put(LHR)
        if pa_deleted:
            self.log_put('%sDELETED %s FILES%s' %(LD1, len(pa_deleted), LD2))
            self.log_put('\n'.join(pa_deleted), True)
        if pa_notdeleted:
            self.log_put('\n%sCOULD NOT DELETE %s FILES%s'  %(LD1, len(pa_notdeleted), LD2))
            self.log_put('\n'.join(pa_notdeleted), True)
            statusmsg += ' **COULD NOT DELETE %s FILES (see Log for details)**' % len(pa_notdeleted)
        self.lblStatus['text'] = statusmsg


    def verify_itxs(self, iids, itxs, cnxFT, cnxD, cnxN):
        """Verify list of itxs (indexes into RSLTS) vs list of Treeview iids."""
        # Get Directory/Name for the first and the last item using both RSLTS
        # and Treeview as source of data. Compare the two. This is intended to
        # detect one-off coding errors and blunders during critical operations
        # such as deleting selected files.

        _RSLTS = self.RSLTS
        _trvw = self.trvwResults

        lenItems = len(itxs)
        if lenItems != len(iids):
            return (False, 'lengths of two lists are not equal')
        if lenItems > 1:
            ii = [0, -1]
        elif lenItems == 1:
            ii = [0]
        else:
            return (True, '')
        for i in ii:
            itx, iid = itxs[i], iids[i]
            ft1, di1, na1 = _RSLTS[itx][cnxFT], _RSLTS[itx][cnxD], _RSLTS[itx][cnxN]
            try: # UnicodeDecodeError error if invalid byte
                ft2 = _trvw.set(iid, column='FileType')
                di2 = _trvw.set(iid, column='Directory')
                na2 = _trvw.set(iid, column='Name')
            except Exception as e:
                return (False, '**Exception** while retrieving values from Treeview:%s' % e_info(e))
            if ft1 != ft2 or di1 != di2 or na1 != na2:
                return (False, 'FileType, or Directory, or Name do not match')

        return (True, '')


    def c_btnFIND(self):
        """Command for button FIND. Run the FIND process."""
        if self._isBusy: return

        tT0 = _time() # start of total run time
        logLines = [LHR]

        ### directories to search ------------------------------------
        var_ckbRecurse = self.var_ckbRecurse.get()
        inputDirs_v1 = inpstr_to_items(self.cmbbDir.get(), sep='|')
        if not inputDirs_v1:
            msgbox_inperror('No Directories to search')
            return
        inputDirs_v1 = process_input_dirs(inputDirs_v1, mustexist=True, nosubdirs=var_ckbRecurse)
        if not inputDirs_v1:
            return
        logLines.append('Directories: %s\n    Recurse=%s' %(inputDirs_v1, var_ckbRecurse))

        ### filter "Skipped dirs" ------------------------------------
        # skip directories and all files under them
        if self.tab_is_on(0):
            # directory paths to skip (Combobox in row 1)
            skipDirs = inpstr_to_items(self.cmbbSkipDir.get(), sep='|')
            skipDirs = process_input_dirs(skipDirs, mustexist=False, nosubdirs=False)
            # directory names to skip (Combobox and OptionMenu in row 2)
            ok, pttnsSkipNames, fltfuncSkipNames, logstr = get_input_names(self.cmbbSkipName, self.var_opmSkipNameMode, self.var_ckbSkipNameIC)
            if not ok: return
            if not (skipDirs or pttnsSkipNames):
                msgbox_inperror('Filter "Skipped dirs": nothing to search')
                return
            if skipDirs:
                logLines.append('Skip directories: %s' %(skipDirs))
            if pttnsSkipNames:
                logLines.append('Skip dirs with name: %s' % logstr)
        else:
            skipDirs, pttnsSkipNames, fltfuncSkipNames = (), (), None

        # Prepare inputDirs_v2: pair each path in inputDirs_v1 with a list
        # of relevant path from skipDirs. Note that dirs in skipDirs were not verified.
        inputDirs_v2 = []
        for p in inputDirs_v1:
            p1 = _normcase(p)
            skipDirsNew, ok = [], True
            for p2 in skipDirs:
                p2 = _normcase(p2)
                if is_subdir(p1, [p2]): # input dir itself is skipped, drop it from result
                    ok = False
                    break
                else:
                    skipDirsNew.append(p2)
                    # p2 is saved normcase-ed
                    # p1 is not normcase-ed: result paths should be as typed by user
            if ok:
                inputDirs_v2.append((p, skipDirsNew))

        ### filter "Name" --------------------------------------------
        doName1, doName2 = False, False
        if self.tab_is_on(1):
            # combobox Name1
            ok, querName1, fltfuncName1, logstr = get_input_names(self.cmbbName1, self.var_opmName1Mode, self.var_ckbName1IC)
            if not ok: return
            if querName1:
                doName1 = True
                yesName1 = self.var_opmName1.get()
                logLines.append('%s %s' %(yesName1, logstr))
                yesName1 = not yesName1.startswith('Not')
            # combobox Name2
            ok, querName2, fltfuncName2, logstr = get_input_names(self.cmbbName2, self.var_opmName2Mode, self.var_ckbName2IC)
            if not ok: return
            if querName2:
                doName2 = True
                yesName2 = self.var_opmName2.get()
                logLines.append('%s %s' %(yesName2, logstr))
                yesName2 = not yesName2.startswith('Not')
            if not (doName1 or doName2):
                msgbox_inperror('Filter "Name": nothing to search')
                return

        ### filter "Path" --------------------------------------------
        doPath1, doPath2 = False, False
        if self.tab_is_on(2):
            # combobox Path1
            ok, querPath1, fltfuncPath1, logstr = get_input_names(self.cmbbPath1, self.var_opmPath1Mode, self.var_ckbPath1IC)
            if not ok: return
            if querPath1:
                doPath1 = True
                yesPath1 = self.var_opmPath1.get()
                logLines.append('%s %s' %(yesPath1, logstr))
                yesPath1 = not yesPath1.startswith('Not')
            # combobox Path2
            ok, querPath2, fltfuncPath2, logstr = get_input_names(self.cmbbPath2, self.var_opmPath2Mode, self.var_ckbPath2IC)
            if not ok: return
            if querPath2:
                doPath2 = True
                yesPath2 = self.var_opmPath2.get()
                logLines.append('%s %s' %(yesPath2, logstr))
                yesPath2 = not yesPath2.startswith('Not')
            if not (doPath1 or doPath2):
                msgbox_inperror('Filter "Path": nothing to search')
                return

        ### filter "Type" --------------------------------------------
        doFT, doExt = False, False
        if self.tab_is_on(3):
            # Extension
            querExt = inpstr_to_items(self.cmbbExts.get(), sep='|', noempty=False)
            if querExt:
                doExt = True
                querExt = [s.casefold() for s in querExt]
                yesExt = self.var_opmExts.get()
                logLines.append('%s %s' %(yesExt, repr(querExt)))
                querExt = {}.fromkeys(querExt)
                yesExt = not yesExt.startswith('Not')
            # FileType
            querFT = []
            if self.var_ckbTypeF.get(): querFT.append('-')
            if self.var_ckbTypeD.get(): querFT.append('d')
            if self.var_ckbTypeL.get(): querFT.append('l')
            if self.var_ckbTypeO.get(): querFT.append('o')
            if len(querFT) != 4:
                doFT = True
                logLines.append('File type: %s' %(repr(querFT)))
                querFT = {}.fromkeys(querFT)

            if not (doExt or doFT):
                msgbox_inperror('Filter "Type": nothing to search')
                return

        ### filter "Size" --------------------------------------------
        doSize = self.tab_is_on(4)
        if doSize:
            what = self.var_opmSize.get()
            units = what.split(',')[1].strip()
            units = {'bytes':1,
                    'K':1024, 'M':1024**2, 'G':1024**3, 'T':1024**4,
                    'k':1000, 'm':1000**2, 'g':1000**3, 't':1000**4,
                    }[units]
            ok, sz1, logstr1 = get_input_size(self.entSize1, units)
            if not ok: return
            ok, sz2, logstr2 = get_input_size(self.entSize2, units)
            if not ok: return
            if (sz1 is None) and (sz2 is None):
                msgbox_inperror('Filter "Size": nothing to search')
                return
            logstr1 = '%s < ' %logstr1 if sz1 else ''
            logstr2 = ' < %s' %logstr2 if sz2 else ''
            logLines.append('%s%s%s' %(logstr1, what, logstr2))
            fltfuncSize = make_comp_func(sz1, sz2, 'st_size')

        ### filter "Time" --------------------------------------------
        doTime = self.tab_is_on(5)
        if doTime:
            ok, tm1, logstr1 = get_input_time(self.entTime1)
            if not ok: return
            ok, tm2, logstr2 = get_input_time(self.entTime2)
            if not ok: return
            if (tm1 is None) and (tm2 is None):
                msgbox_inperror('Filter "Time": nothing to search')
                return
            what = self.var_opmTime.get()
            logstr1 = '%s < ' %logstr1 if tm1 else ''
            logstr2 = ' < %s' %logstr2 if tm2 else ''
            logLines.append('%s%s%s' %(logstr1, what, logstr2))
            if what == 'MTIME':   att = 'st_mtime'
            elif what == 'CTIME': att = 'st_ctime'
            elif what == 'ATIME': att = 'st_atime'
            fltfuncTime = make_comp_func(tm1, tm2, att)

        ### filter "Misc" --------------------------------------------
        doMisc = self.tab_is_on(6)
        if doMisc:
            ok, querUID, querGID, querNLINK, querMODE, fltfuncMODE, logstr = get_input_misc(self.entUID, self.entGID, self.entNLINK, self.cmbbMODE, self.var_opmMODEMode)
            if not ok: return
            if not (querUID or querGID or querNLINK or querMODE):
                msgbox_inperror('Filter "Misc": nothing to search')
                return
            if querUID:
                yesUID = self.var_opmUID.get()
                logLines.append('%s %s' %(yesUID, repr(list(querUID))))
                yesUID = not yesUID.startswith('Not')
            if querGID:
                yesGID = self.var_opmGID.get()
                logLines.append('%s %s' %(yesGID, repr(list(querGID))))
                yesGID = not yesGID.startswith('Not')
            if querNLINK:
                querNlink = querNLINK[0]
                logLines.append('NLINK > %s' %(repr(querNlink)))
            if querMODE:
                yesMODE = self.var_opmMODE.get()
                logLines.append('%s %s' %(yesMODE, logstr))
                yesMODE = not yesMODE.startswith('Not')

        ### filter "Content" -----------------------------------------
        doCont = self.tab_is_on(7)
        if doCont:
            ok, querCont, fltfuncCont, kwargsCont, logstr = get_input_content(self.entCont, self.var_opmContMode, self.var_ckbContIC, self.cmbbContEnc, self.var_opmContErrors, self.var_opmContNewline)
            if not ok: return
            logLines.append('Content: %s' %logstr)

        ### needEnstat
        if doTime or doSize or doMisc:
            needEnstat = True
        else:
            needEnstat = False


        ### prepare to scan ------------------------------------------
        _trvw = self.trvwResults
        resTable, resErrs1, resErrs2, resErrs3 = [], [], [], []
        Cnt.d, cntItems, cntFound = 0, 0, 0

        # handle column LinkTo separately because it does not need stat
        wantLinkTo = 'LinkTo' in self.trvwColumns2

        # prepare widgets
        self._isBusy = True
        self._isCancelled = False
        self.btnFIND['state'] = tk.DISABLED
        self.btnCANCEL['state'] = tk.NORMAL
        self.txtLog['state'] = tk.DISABLED
        _trvw.delete(*_trvw.get_children())
        self.RSLTS = []
        self.lblStatus['text'] = 'searching...'

        # index of currently selected (visible) tab in notebook Filters
        tabSelFlt = self.ntbkFilters.index(self.ntbkFilters.select())
        # list of ttk widgets to disable during FIND
        clickables = self.clickablesA + self.clickablesB[tabSelFlt]
        self.disable_gui_state(True, clickables)

        self.master.update_idletasks()

        ### start of scanning ----------------------------------------
        # Iterate over input dirs and find matching files.
        self._isTime = False
        self._timer = Timer(2, self.timer)
        self._timer.start()
        tT1 = _time() # start of scanning time
        ### try: -----------------------------------------------------
        try:
            ok, notok = False, False
            for (inputDir, skipDirs) in inputDirs_v2:
                for (endir, en, isDir, err) in scantree(inputDir, recurse=var_ckbRecurse, skipPaths=skipDirs, skipNames=pttnsSkipNames, fltName=fltfuncSkipNames):
                    # TESTING: reduce scan speed to 1 second per item
                    #time.sleep(1)
                    ### periodically update Statusbar and check if CANCEL button was pressed
                    if self._isTime:
                        self._isTime = False
                        tNow = _time()
                        self.status_put('searching...', cntFound, cntItems, Cnt.d,
                                        '%s+%s+%s' %(len(resErrs1), len(resErrs2), len(resErrs3)),
                                        tNow-tT1, tNow-tT0)
                        self.master.update()
                        if self._isCancelled:
                            self.status_put('CANCELLED.', cntFound, cntItems, Cnt.d,
                                            '%s+%s+%s' %(len(resErrs1), len(resErrs2), len(resErrs3)),
                                            _time()-tT1, _time()-tT0)
                            self._timer.cancel()
                            ok = True
                            return

                    ### what we got from scandir()
                    if err:
                        resErrs1.append('%s: %s' %(err.__class__.__name__, err))
                    if not en:
                        continue
                    cntItems += 1

                    ### apply filters to current DirEntry item en --------------
                    enname = en.name

                    if doName1:
                        if fltfuncName1(enname, querName1):
                            if not yesName1: continue
                        else:
                            if yesName1: continue

                    if doName2:
                        if fltfuncName2(enname, querName2):
                            if not yesName2: continue
                        else:
                            if yesName2: continue

                    if doPath1:
                        if fltfuncPath1(en.path, querPath1):
                            if not yesPath1: continue
                        else:
                            if yesPath1: continue

                    if doPath2:
                        if fltfuncPath2(en.path, querPath2):
                            if not yesPath2: continue
                        else:
                            if yesPath2: continue

                    resCache = {}
                    if doExt:
                        enext = get_ext(enname)
                        if enext.casefold() in querExt:
                            if not yesExt: continue
                        else:
                            if yesExt: continue
                        resCache['Ext'] = enext

                    enft = ''
                    if doFT:
                        if isDir: enft = 'd'
                        else:
                            try:
                                if en.is_file(follow_symlinks=False): enft = '-'
                                elif en.is_symlink(): enft = 'l'
                                else: enft = 'o'
                            except OSError as e:
                                resErrs2.append(str(e))
                                continue
                        if enft not in querFT: continue

                    # call en.stat() only once the first time enstat is needed
                    # do this now if enstat is needed for one of next filters
                    enstat = None
                    if needEnstat:
                        try:
                            enstat = en.stat(follow_symlinks=False)
                        except OSError as e:
                            resErrs2.append(str(e))
                            continue

                        if doSize:
                            if not fltfuncSize(enstat): continue

                        if doTime:
                            if not fltfuncTime(enstat): continue

                        if doMisc:
                            if querUID:
                                if enstat.st_uid in querUID:
                                    if not yesUID: continue
                                else:
                                    if yesUID: continue
                            if querGID:
                                if enstat.st_gid in querGID:
                                    if not yesGID: continue
                                else:
                                    if yesGID: continue
                            if querNLINK:
                                if enstat.st_nlink <= querNlink: continue
                            if querMODE:
                                enmode = _filemode(enstat.st_mode)
                                if fltfuncMODE(enmode, querMODE):
                                    if not yesMODE: continue
                                else:
                                    if yesMODE: continue
                                resCache['MODE'] = enmode

                    if doCont:
                        # reject items other than regular files
                        if enft == '':
                            if isDir: continue
                            try:
                                if en.is_file(follow_symlinks=False): enft = '-'
                                else: continue
                            except OSError as e:
                                resErrs2.append(str(e))
                                continue
                        elif enft != '-':
                            continue
                        try:
                            with open(en.path, **kwargsCont) as f:
                                if not fltfuncCont(f, querCont):
                                    continue
                        except Exception as e:
                            resErrs3.append('%s:\n    %s: %s' %(en.path, e.__class__.__name__, e))
                            continue

                    ### process found item ---------------------------
                    cntFound += 1
                    enpath = en.path
                    if not enstat:
                        try:
                            enstat = en.stat(follow_symlinks=False)
                        except OSError as e:
                            resErrs2.append(str(e))
                            continue
                    if enft == '':
                        if isDir: enft = 'd'
                        else:
                            try:
                                if en.is_file(follow_symlinks=False):
                                    enft = '-'
                                elif en.is_symlink():
                                    enft = 'l'
                                else:
                                    enft = _filemode(enstat.st_mode)[0]
                            except OSError as e:
                                resErrs2.append(str(e))
                                continue
                    elif enft == 'o':
                        enft = _filemode(enstat.st_mode)[0]

                    if 'Ext' in resCache:
                        enext = resCache['Ext']
                    else:
                        enext = get_ext(enname)

                    # handle columns SIZE and Size (always available together)
                    ensize = enstat.st_size
                    if isDir:
                        enSize = '<DIR>'
                    else:
                        enSize = bytes2kibi(ensize)

                    # row for insertion into results table
                    # items MUST be in same order as in self.trvwColumns
                    # append values for first 6 columns which are always present:
                    #   'FileType', 'Directory', 'Name', 'Ext', 'SIZE', 'Size'
                    res = [enft, endir, enname, enext, ensize, enSize]

                    # handle column LinkTo
                    if wantLinkTo:
                        if enft == 'l':
                            lp = os.readlink(enpath)
                            if _path.isabs(lp):
                                lap = lp
                            else:
                                lap = _path.normpath(_join(endir, lp))
                            lft = get_path_ft(lap)
                            resCache['LinkTo'] = '[%s] %s' %(lft, lp)
                        else:
                            resCache['LinkTo'] = ''

                    # append values for all other (optional) columns
                    # they are always derived from stat
                    for c in self.trvwColumns2:
                        if c in resCache:
                            res.append(resCache[c])
                        else:
                            res.append(enst_Functions[c](enstat))

                    # add this row to results
                    resTable.append(tuple(res))
                    # end of processing found item -------------------

            ### end of scanning --------------------------------------
            self._timer.cancel()
            tT1 = _time()-tT1 # scanning time
            lenErrs = '%s+%s+%s' %(len(resErrs1), len(resErrs2), len(resErrs3))

            # cannot cancel while tree is being populated
            self.status_put('displaying...', cntFound, cntItems, Cnt.d, lenErrs, tT1, _time()-tT0)
            self.btnCANCEL['state'] = tk.DISABLED
            self.master.update_idletasks()

            # warn if there are too many results to display
            #if cntFound > 10:
            if cntFound > 100000:
                tT00 = _time()
                yesno = tkMessageBox.askyesno('%s -- Confirm' % TITLE, 'Display %s results?' % cntFound)
                tT0 += _time() - tT00
                if not yesno:
                    self._isCancelled = True
                    self.status_put('CANCELLED.', cntFound, cntItems, Cnt.d, lenErrs, tT1, _time()-tT0)
                    ok = True
                    return

            ### populate Treeview with results -----------------------
            if resTable:
                resTable.sort(key=lambda j: j[2]) # sort by Name
                resTable.sort(key=lambda j: j[1]) # sort by Directory
                self.trvw_populate(resTable)

                self.RSLTS = resTable
                #_trvw.selection_set('1')
                #_trvw.focus('1')

                # remove old sort sign
                self.trvw_remove_sort_sign(self._sortedCID)
                # put new sort sign in Directory heading
                h = '%s%s' %(_trvw.heading('Directory', option='text'), SL2H)
                _trvw.heading('Directory', text=h)
                self._sortedCID = 'Directory'

            ### save errors ------------------------------------------
            if resErrs1:
                logLines.append('\n**OSError** (during file system traversal)')
                resErrs1.sort()
                logLines.extend(resErrs1)
            if resErrs2:
                logLines.append('\n**OSError** (during item processing)')
                resErrs2.sort()
                logLines.extend(resErrs2)
            if resErrs3:
                logLines.append('\n**Exception** (during file content search)')
                resErrs3.sort()
                logLines.extend(resErrs3)

            ok = True

        ### except: --------------------------------------------------
        except:
            notok = True
            logLines.append('\n********************* ERROR OCCURRED DURING FIND *********************')
            try:
                etype, evalue, etb = sys.exc_info()
                f_ex = traceback.format_exception(etype, evalue, etb)
                logLines.extend(f_ex)
                etype = evalue = etb = None
            except Exception as e:
                logLines.append('**Exception** while trying to format traceback:%s' % e_info(e))

        ### finally: -------------------------------------------------
        finally:
            self._timer.cancel()
            self.btnFIND['state'] = tk.NORMAL
            self.btnCANCEL['state'] = tk.DISABLED
            # print to log
            self.txtLog['state'] = tk.NORMAL
            self.log_put('\n'.join(logLines), True)
            self.master.update() # to discard clicks on UI, e.g., during prolonged displaying
            self._isBusy = False
            #self._isCancelled = False
            self.disable_gui_state(False, clickables)

            if not ok or notok:
                self.lblStatus['text'] = 'ERROR OCCURRED DURING FIND, SEE LOG FOR TRACEBACK'
                self.lblStatus.configure(background='yellow', foreground='red')
            elif not self._isCancelled:
                self.status_put('DONE.', cntFound, cntItems, Cnt.d, lenErrs, tT1, _time()-tT0, toLog=True)
            else:
                self.log_put('\nCANCELLED.', True)

        # end of FIND


    def c_btnCANCEL(self):
        """Command for button CANCEL."""
        if not self._isBusy: return
        self._isCancelled = True
        self.btnCANCEL['state'] = tk.DISABLED


    def trvw_populate(self, resTable):
        """Populate empty Treeview with data from resTable."""
        _trvw = self.trvwResults
        _tags = self.tags
        for n, i in enumerate(resTable, start=1):
            if i[0] == '-':
                t = []
            else:
                t = [_tags.get(i[0], 'o')]
            if n % 2:
                t.append('s')
            _trvw.insert('', 'end', iid='%s' %n, values=i, tags=t)


    def trvw_remove_sort_sign(self, col):
        """Remove sort sign from column heading."""
        _trvw = self.trvwResults
        if col not in _trvw['columns']:
            return
        h = _trvw.heading(col, option='text')
        if h.endswith(SL2H):
            _trvw.heading(col, text=h[: - len(SL2H)])
        elif h.endswith(SH2L):
            _trvw.heading(col, text=h[: - len(SH2L)])


    def tab_is_on(self, idx):
        return self.ntbkFilters.tab(idx, option='text').startswith(TAB_ON)


    def timer(self):
        if not self._isBusy: return
        self._isTime = True


    def disable_gui_state(self, disable, clickables):
        # Disable or un-disable clickable ttk widgets, toplevel menus,
        # detachable menus.
        #
        # FIXME On Windows disabling toplevel menus in menubar is not enough:
        # mouse click on them during FIND still pauses FIND. Then need to click
        # outside menus or press Esc to resume. postcommand= is executed when
        # menu is disabled.
        # This means detachable menus should not have submenus.
        # No such issue on Linux.
        #
        # Note: Treeview does not respond to statespec=['disabled']

        if disable:
            ttkState = ['disabled']
            tkState = tk.DISABLED
        else:
            ttkState = ['!disabled']
            tkState = tk.NORMAL

        for w in clickables:
            w.state(statespec=ttkState)

        for m in self.visibleMenus:
            for i in range(m.index(tk.END) + 1):
                m.entryconfigure(i, state=tkState)


    def status_put(self, status, found, scanned, dirs, errs, time2, time1, toLog=False):
        # Put message on statusbar during FIND.
        s = '%s Found %s items. %s errors. Scanned %s items in %s directories in %.2f sec. Run time %.2f sec.' %(status, found, errs, scanned, dirs, time2, time1)
        self.lblStatus['text'] = s
        if toLog:
            self.txtLog.insert(tk.END, '\n%s\n' %s)


    def log_put(self, s, scroll=False):
        """Print string s to Log: insert at the end and append newline."""
        self.txtLog.insert(tk.END, '%s\n' %s)
        if scroll:
            self.txtLog.see(tk.END)


    def log_show(self):
        """Show end of Log."""
        self.ntbkResults.select(1)
        self.txtLog.focus_set()
        self.txtLog.see(tk.END)


class Timer(threading.Thread):
    """Adapted from class Timer(Thread) in Lib/threading.py.
    Like threading.Timer(), but instead of running function once, repeat it
    indefinitely until cancel() is called.
    """

    def __init__(self, interval, function):
        threading.Thread.__init__(self)
        self.interval = interval
        self.function = function
        self.finished = threading.Event()

    def cancel(self):
        """Stop the timer if it hasn't finished yet."""
        self.finished.set()

    def run(self):
        while not self.finished.is_set():
            self.finished.wait(self.interval)
            if not self.finished.is_set():
                self.function()


class Cnt:
    d = 0


def scantree(dirpath, recurse=True, skipPaths=None, skipNames=None, fltName=None):
    """Scan directory dirpath with scandir().
    Yield (dirpath, DirEntry, isDirectory, error).
    recurse -- scan recursively or not.
    skipPaths -- list of directory paths to skip, must be abspath-ed and normcase-ed.
    skipNames -- list of directory names to skip.
    fltName -- filter function to use with names in skipNames.
    When directory is skipped, skip everything under it (do not descent into it).
    """
    Cnt.d += 1
    try:
        for en in _scandir(dirpath):
            try:
                isDir = en.is_dir(follow_symlinks=False)
            except OSError as err:
                yield (dirpath, en, None, err)
            else:
                if isDir:
                    if skipPaths and is_subdir(_normcase(en.path), skipPaths):
                        continue
                    if skipNames and fltName(en.name, skipNames):
                        continue
                    yield (dirpath, en, True, None)
                    if recurse:
                        for item in scantree(en.path, recurse=recurse, skipPaths=skipPaths, skipNames=skipNames, fltName=fltName):
                            yield item
                else:
                    yield (dirpath, en, False, None)
    except OSError as err:
        Cnt.d -= 1
        yield (dirpath, None, None, err)


def inpstr_to_items(s, sep='|', noempty=True):
    """Convert input string s to a list of strings, or one string item.
    Items are separated by `sep` and may be surrounded by `"`.
    Whitespace is stripped: leading, trailing, around `sep`.
    Then enclosing "" are removed. If resulting string is empty, skip it.
    if `sep` and not `noempty`: allow `""` as an item to denote empty string.
    If not `sep`, process `s` as one item and return as string.
    """
    if sep:
        res = []
        items = s.split(sep)
        for i in items:
            j = i.strip()
            if not j: continue
            if len(j) > 1 and j[0] == '"' and j[-1] == '"':
                j = j[1:-1]
                if not j and noempty: continue
            res.append(j)
    else:
        res = s.strip()
        if len(res) > 1 and res[0] == '"' and res[-1] == '"':
            res = res[1:-1]
    return res


def inpstr_to_ints(s, sep='|'):
    """Convert input string s to a list of integers, or list with one integer."""
    if sep:
        items = s.split(sep)
    else:
        items = [s.strip()]
    res = []
    for i in items:
        j = i.strip()
        if not j: continue
        try:
            j = int(j)
            res.append(j)
        except Exception as e:
            msg = 'Cannot convert to integer: %s\n**Exception**:%s' %(repr(j), e_info(e))
            return ([], msg)
    return (res, '')


def process_input_dirs(dirs, mustexist=True, nosubdirs=True):
    """Process list of input directories: expand user and vars, absolutize,
    normalize, remove duplicates. Optionally: check for existence, remove subdirs."""
    if not dirs:
        return []
    res, seen = [], {}
    for d in dirs:
        d = full_path(d)
        # always remove duplicates
        d_nc = _normcase(d)
        if d_nc in seen:
            continue
        # when each entry must be a valid dir
        if mustexist and (not _path.isdir(d) or _path.islink(d)):
            msgbox_inperror('Path is not accessible or not a directory:\n%s' %(quoted(d)))
            return None
        res.append(d)
        seen[d_nc] = 1
    # when searching recursively, subdirs must be removed
    if nosubdirs:
        res1 = []
        for d in res:
            d_nc = _normcase(d)
            ok = True
            for d2 in seen:
                if is_subdir(d_nc, [d2]) and d_nc != d2: # duplicates have been removed already
                    ok = False
                    break
            if ok:
                res1.append(d)
        return res1
    else:
        return res


def get_input_names(cmbbName, var_opmNameMode, var_ckbNameIC):
    """Process string entered in combobox Name or Path.
    Return (ok, list-of-patterns, filter-function, logstr)."""

    s = cmbbName.get()

    var_mode = var_opmNameMode.get() # which filter function to use
    if var_mode == 'off':
        return (1, None, None, '')

    if var_mode == 'RegExp': # treat 'Name:' input as one string item
        pttrns = inpstr_to_items(s, sep=None)
    else:
        pttrns = inpstr_to_items(s, sep='|')

    if not pttrns:
        return (1, None, None, '')

    var_ic = var_ckbNameIC.get() # ignore case, 0 or 1

    if var_mode == 'RegExp':
        logstr = '%s\n    %s, IgnoreCase=%s' %(repr(pttrns), var_mode, var_ic)
        flags = re.IGNORECASE if var_ic else 0
        pttrns, msg = compile_regexp(pttrns, flags=flags)
        if msg:
            msgbox_inperror(msg)
            return (0, None, None, '')
        qn = 1
    else:
        if var_ic:
            pttrns = [s.casefold() for s in pttrns]
        if len(pttrns) == 1:
            pttrns, qn = pttrns[0], 1
        else:
            qn = 2
        logstr = '%s\n    %s, IgnoreCase=%s' %(repr(pttrns), var_mode, var_ic)

    filterFunc = flt_NameMatchers[(var_mode, qn, var_ic)]

    return (1, pttrns, filterFunc, logstr)


def get_input_content(entCont, var_opmContMode, var_ckbContIC,
                      cmbbContEnc, var_opmContErrors, var_opmContNewline):
    """Process data entered in filter Content.
    Return (ok, pattern, filter-function, kwargs, logstr)."""

    pttrn = inpstr_to_items(entCont.get(), sep=None)
    if not pttrn:
        msgbox_inperror('Filter "Content": nothing to search')
        return (0, None, None, None, '')

    var_mode = var_opmContMode.get()
    var_ic = var_ckbContIC.get()

    if var_mode == 'RegExp':
        logstr = '%s\n    %s, IgnoreCase=%s' %(repr(pttrn), var_mode, var_ic)
        flags = re.IGNORECASE if var_ic else 0
        pttrn, msg = compile_regexp(pttrn, flags=flags)
        if msg:
            msgbox_inperror(msg)
            return (0, None, None, None, '')
    else:
        if var_ic:
            pttrn = pttrn.casefold()
        logstr = '%s\n    %s, IgnoreCase=%s' %(repr(pttrn), var_mode, var_ic)

    matcherFunc = flt_ContMatchers[(var_mode, var_ic)]

    kwargs = {}
    enc = cmbbContEnc.get()
    if '#' in enc:
        enc, x = enc.split('#',1)
    enc = enc.strip()
    if not enc:
            msgbox_inperror('Filter "Content": no encoding')
            return (0, None, None, None, '')
    kwargs['encoding'] = enc
    kwargs['errors'] = var_opmContErrors.get()
    newln = var_opmContNewline.get()
    if newln == 'None':
        kwargs['newline'] = None
    elif newln == "''":
        kwargs['newline'] = ''
    else:
        kwargs['newline'] = newln.replace('\\n', '\n').replace('\\r', '\r')
    logstr += '; encoding=%s, errors=%s, newline=%s' % (repr(kwargs['encoding']), repr(kwargs['errors']), repr(kwargs['newline']))

    return (1, pttrn, matcherFunc, kwargs, logstr)


def get_input_misc(entUID, entGID, entNLINK, cmbbMODE, var_opmMODEMode):
    """Process data entered in filter Misc.
    Return (ok, UIDs, GIDs, NLINK, MODEs, MODE func, MODE logstr)."""
    querUID, querGID, querNLINK, querMODE, fltfuncMODE, logstr = None, None, None, None, None, None
    error = ('', None, None, None, None, None, None)

    # UID
    querUID, msg = inpstr_to_ints(entUID.get(), sep='|')
    if msg:
        msgbox_inperror(msg)
        return error
    # GID
    querGID, msg = inpstr_to_ints(entGID.get(), sep='|')
    if msg:
        msgbox_inperror(msg)
        return error
    # NLINK
    querNLINK, msg = inpstr_to_ints(entNLINK.get(), sep=None)
    if msg:
        msgbox_inperror(msg)
        return error

    # MODE
    s = cmbbMODE.get()
    var_mode = var_opmMODEMode.get() # which filter function to use
    if var_mode == 'RegExp': # treat 'Name:' input as one string item
        pttrns = inpstr_to_items(s, sep=None)
    else:
        pttrns = inpstr_to_items(s, sep='|')
    if pttrns:
        if var_mode == 'RegExp':
            logstr = '%s\n    %s' %(repr(pttrns), var_mode)
            pttrns, msg = compile_regexp(pttrns, flags=0)
            if msg:
                msgbox_inperror(msg)
                return error
            qn = 1
        else:
            if len(pttrns) == 1:
                pttrns, qn = pttrns[0], 1
            else:
                qn = 2
            logstr = '%s\n    %s' %(repr(pttrns), var_mode)
        querMODE = pttrns
        fltfuncMODE = flt_NameMatchers[(var_mode, qn, 0)] # IgnoreCase=0

    return (1, set(querUID), set(querGID), querNLINK, querMODE, fltfuncMODE, logstr)


def get_input_time(entBox):
    """Get time string from Entry entBox and convert it to actual time.
    Return (ok, time, logstr)."""
    s = entBox.get().strip()
    if not s:
        return (1, None, '')
    logstr = s
    try:
        tm = time.strptime(s, TIME_FORMAT)
        tm = time.mktime(tm)
    except Exception as e:
        msgbox_inperror('Cannot convert string to time: %s\n**Exception**:%s' %(repr(s), e_info(e)))
        return (0, None, '')
    logstr = '%s (%s)' %(logstr, tm)
    return (1, tm, logstr)


def get_input_size(entBox, units):
    """Get size string from Entrybox entBox and convert it to file size.
    Return (ok, size, logstr)."""
    s = entBox.get().strip()
    if not s:
        return (1, None, '')
    logstr = s
    try:
        sz = float(s)
        sz = int('%.0f' %(sz * units))
    except Exception as e:
        msgbox_inperror('Cannot convert string to file size: %s\n**Exception**:%s' %(repr(s), e_info(e)))
        return (0, None, '')
    logstr = '%s (%s bytes)' %(logstr, sz)
    return (1, sz, logstr)


def is_subdir(subDir, parDirs):
    """subDir is a directroy. parDirs is a list of directories.
    Return True if subDir is sub-directory of, or same as, one of directories in parDirs.
    IMPORTANT: all directores MUST be abspath-ed and normcase-ed.
    """
    for parDir in parDirs:
        if not subDir.startswith(parDir):
            continue
        len_parDir = len(parDir)
        # identical dirs
        if len(subDir) == len_parDir:
            return True
        # parDir is a root dir such as / or C:\ -- otherwise abspath() removes end sep
        elif parDir[-1] == _sep:
            return True
        elif subDir[len_parDir] == _sep:
            return True
    return False


def full_path(p, basedir=None):
    """Convert string p to full path. Expand ~, $HOME, etc. Normalize.
    If basedir is given and p does not resolve to an absolute path, p is
    relative to basedir, which must be full path to a dir.
    """
    p = _path.expanduser(p)
    p = _path.expandvars(p)
    if basedir:
        if not _path.isabs(p):
            p = _path.join(basedir, p)
        p = _path.normpath(p)
    else:
        p = _path.abspath(p)
    return p


def expand_placeholders(args, d):
    """ `args` is a list of strings. Keys in `d` are %P, %D, %N. 
    Replace items '%P', '%D', '%N' with values from `d`.
    For other items replace the above strings with quoted values.
    Do not change the first item: it is the program to run.
    """
    if len(args) < 2:
        return args
    args_new = [args[0], ]
    for a in args[1:]:
        if a in d:
            a_new = d[a]
        elif '%' in a:
            a_new = ''
            i, j, l = 0, 0, len(a)
            while j > -1:
                j = a.find('%', i)
                if j < 0 or j >= l-1:
                    a_new = '%s%s' %(a_new, a[i:])
                    break
                if a[j: j+2] in d:
                    a_new = '%s%s%s' %(a_new, a[i:j], quoted(d[a[j: j+2]]))
                    i = j+2
                else:
                    a_new = '%s%s' %(a_new, a[i: j+1])
                    i = j+1
        else:
            a_new = a
        args_new.append(a_new)
    return args_new


def compile_regexp(pttrn, flags):
        try:
            regexp = re.compile(pttrn, flags=flags)
        except Exception as e:
            msg = 'Cannot compile RegExp: %s\n**Exception**:%s' %(repr(pttrn), e_info(e))
            return (None, msg)
        else:
            return (regexp, '')


def bytes2kibi(b):
    """Convert size in bytes to human-readable format using kibi-bytes.
    Round to whole number."""
    if b < 2**10:
        return '%d B'   % (b)
    elif b < 2**20-2**9:
        return '%.0f K' % (b / 2**10)
    elif b < 2**30-2**19:
        return '%.0f M' % (b / 2**20)
    elif b < 2**40-2**29:
        return '%.0f G' % (b / 2**30)
    elif b < 2**50-2**39:
        return '%.0f T' % (b / 2**40)
    else:
        return '>= 1 P'


def bytes2size(b, how):
    """Convert size in bytes to human-readable format.
    Show 4 decimal points unless it's exact multiple."""
    pr = 4 # default precision
    if how == 'kibi':
        if b < 2**10:
            return '%d bytes' % (b)
        elif b < 2**20:
            if not b % 2**10: pr = 0
            return '%.*f K' % (pr, b / 2**10)
        elif b < 2**30:
            if not b % 2**20: pr = 0
            return '%.*f M' % (pr, b / 2**20)
        elif b < 2**40:
            if not b % 2**30: pr = 0
            return '%.*f G' % (pr, b / 2**30)
        elif b < 2**50:
            if not b % 2**40: pr = 0
            return '%.*f T' % (pr, b / 2**40)
        else:
            return '>= 1 P'
    elif how == 'kilo':
        if b < 10**3:
            return '%d bytes' % (b)
        elif b < 10**6:
            if not b % 10**3: pr = 0
            return '%.*f k' % (pr, b / 10**3)
        elif b < 10**9:
            if not b % 10**6: pr = 0
            return '%.*f m' % (pr, b / 10**6)
        elif b < 10**12:
            if not b % 10**9: pr = 0
            return '%.*f g' % (pr, b / 10**9)
        elif b < 10**15:
            if not b % 10**12: pr = 0
            return '%.*f t' % (pr, b / 10**12)
        else:
            return '>= 1 p'
    else:
        return 'ERROR'


def file_properties(p):
    """Get properties for file item at path p."""
    res = []
    res.append('     Path: %s' % quoted(p))
    res.append('Directory: %s' % quoted(_path.dirname(p)))
    res.append('     Name: %s' % quoted(_path.basename(p)))
    try:
        statinfo = os.stat(p, follow_symlinks=False)
        # https://docs.python.org/3/library/os.html#os.stat_result
        mode = statinfo.st_mode
        uid, gid = statinfo.st_uid, statinfo.st_gid
        res.append('     MODE: %s, UID=%s (user: %s), GID=%s (group: %s)' % (_filemode(mode), uid, _getpwuid(uid)[0], gid, _getgrgid(gid)[0]))

        ft = _filemode(mode)[0]
        if ft == 'l':
            x = '' if _path.exists(p) else ' -- BROKEN'
            ft_desc = '%s (%s%s)' %(ft, FT_DESCRIP.get(ft, 'n/a'), x)
            res.append('     Type: %s' %(ft_desc))
            # get info about real path
            rp = _path.realpath(p)
            ft_rp = get_path_ft(rp)
            res.append('Real path (%s):\n       [%s] %s' %(FT_DESCRIP.get(ft_rp, 'n/a'), ft_rp, quoted(rp)))
            # get info about all symbolic links leading to the real path
            res.append('  Link to:')
            lap = p # link absolute path
            lft, j = 'l', 0
            while lft == 'l':
                lp = os.readlink(lap)
                if _path.isabs(lp):
                    lap = lp
                    x = ''
                else:
                    lap = _path.normpath(_path.join(_path.dirname(lap), lp))
                    x = '  -> %s' %(quoted(lap))
                lft = get_path_ft(lap)
                res.append('       [%s] %s%s' %(lft, quoted(lp), x))
                j += 1
                if j >= 20:
                    res.append('           MAXIMUM LINK DEPTH EXCEEDED')
                    break
        else:
            ft_desc = '%s (%s)' %(ft, FT_DESCRIP.get(ft, 'n/a'))
            res.append('     Type: %s' %ft_desc)

        b = statinfo.st_size
        if b >= 1024:
            x = ', %s, %s' % (bytes2size(b,'kibi'), bytes2size(b,'kilo'))
        else:
            x = ''
        res.append('     SIZE: %s bytes%s' % (b, x))

        st_mtime, st_ctime, st_atime = statinfo.st_mtime, statinfo.st_ctime, statinfo.st_atime
        mtime = _strftime(TIME_FORMAT, _localtime(st_mtime))
        ctime = _strftime(TIME_FORMAT, _localtime(st_ctime))
        atime = _strftime(TIME_FORMAT, _localtime(st_atime))
        res.append('    MTIME: %s (%s)' % (mtime, st_mtime))
        res.append('    CTIME: %s (%s)' % (ctime, st_ctime))
        res.append('    ATIME: %s (%s)' % (atime, st_atime))

        st_dev = statinfo.st_dev
        res.append('NLINK=%s, INO=%s, DEV=%s (major: %s, minor: %s)' % (statinfo.st_nlink, statinfo.st_ino, st_dev, os.major(st_dev), os.minor(st_dev)))

        extras = []
        for st in ('st_blocks', 'st_blksize', 'st_rdev', 'st_flags',
                   'st_gen', 'st_birthtime',
                   'st_rsize', 'st_creator', 'st_type'):
            at = getattr(statinfo, st, None)
            if at is None: continue
            extras.append('%s=%s' %(st[3:].upper(), at))
        if extras:
            res.append(', '.join(extras))

    except OSError as e:
        res.append('**OSError**:%s' % e_info(e))
    except Exception as e:
        res.append('**Exception** (this should not happen):%s' % e_info(e))

    return res


def get_path_ft(p):
    """Get filetype char for path p."""
    try:
        mode = os.stat(p, follow_symlinks=False).st_mode
    except OSError:
        return '!'
    return _filemode(mode)[0]


def get_ext(name):
    """Return extension of file name."""
    j = name.rfind('.')
    if j > 0:
        return name[j:]
    return ''


def delete_one_file(p, ft):
    """Delete one file. `p` is path. `ft` is file type."""
    try:
        if ft == 'd':
            shutil.rmtree(p)
        else:
            os.unlink(p)
        return (True, '')
    except Exception as e:
        return (False, '%s: %s' %(e.__class__.__name__, e))


def e_info(e):
    """Return info message string for Exception e."""
    return '\n    %s: %s' %(e.__class__.__name__, e)


#--- Tkinter helpers--------------------------------------------------

def tk_clipboard_get(root):
    # when clipboard is empty, root.clipboard_get() gives exception:
    #   _tkinter.TclError: CLIPBOARD selection doesn't exist or form "STRING" not defined
    try:
        #clip = root.selection_get(selection='CLIPBOARD')
        clip = root.clipboard_get()
    except tk.TclError:
        clip = ''
    return clip


def tk_clipboard_put(root, text):
    root.clipboard_clear()
    root.clipboard_append(text)


def tk_make_optionmenu(master, var, choices, default=None, width=0):
    opm = ttk.OptionMenu(master, var, None, *choices)
    var.set(default)
    opm.config(width=width) # in characters, for monospaced font

    # Patch for ttk.OptionMenu bug (Python 3.5):
    # https://stackoverflow.com/questions/33831289/ttk-optionmenu-displaying-check-mark-on-all-menus
    menu = opm['menu']
    last = menu.index('end')
    for i in range(0, last+1):
        menu.entryconfig(i, variable=var)
    return opm


def tk_cmbb_insert(cmbb, values):
    """Put first item from list values into empty combobox cmbb."""
    if values:
        val = values[0]
        if val:
            cmbb.insert(0, val)


def msgbox_error(message):
    tkMessageBox.showerror('%s -- Error' % TITLE, message)


def msgbox_inperror(message):
    tkMessageBox.showerror('%s -- Invalid Input' % TITLE, message)


### OS is Windows
if sys.platform == 'win32':

    def quoted(s):
        return '"%s"' % s

    def startfile(p, log_put):
        p = os.path.normpath(p)
        try:
            os.startfile(p)
        except Exception as e:
            emsg = e_info(e)
            msgbox_error('**Exception** (see Log for details):%s' %emsg)
            log_put(LHR)
            log_put('**Exception**:%s' %emsg)
            log_put('caused by: os.startfile(p)\np = %s' %repr(p), True)

### OS is non-Windows
else:

    def quoted(s):
        return "'%s'" % (s.replace("'", "'\\''"))

    def startfile(p, log_put):
        try:
            pid = subprocess.Popen(['xdg-open', p]).pid
        except Exception as e:
            emsg = e_info(e)
            msgbox_error('**Exception** (see Log for details):%s' %emsg)
            log_put(LHR)
            log_put('**Exception**:%s' %emsg)
            log_put("caused by: subprocess.Popen(['xdg-open', p])\np = %s" %repr(p), True)


#--- filter Name functions -------------------------------------------

def flt_NameExact1(name, s):
    if s == name:
        return 1

def flt_NameExact1_IC(name, s):
    if s == name.casefold():
        return 1

def flt_NameExact2(name, ss):
    for s in ss:
        if s == name:
            return 1

def flt_NameExact2_IC(name, ss):
    for s in ss:
        if s == name.casefold():
            return 1

#---
def flt_NameContains1(name, s):
    if s in name:
        return 1

def flt_NameContains1_IC(name, s):
    if s in name.casefold():
        return 1

def flt_NameContains2(name, ss):
    for s in ss:
        if s in name:
            return 1

def flt_NameContains2_IC(name, ss):
    for s in ss:
        if s in name.casefold():
            return 1

#---
def flt_NameStartswith1(name, s):
    if name.startswith(s):
        return 1

def flt_NameStartswith1_IC(name, s):
    if name.casefold().startswith(s):
        return 1

def flt_NameStartswith2(name, ss):
    for s in ss:
        if name.startswith(s):
            return 1

def flt_NameStartswith2_IC(name, ss):
    for s in ss:
        if name.casefold().startswith(s):
            return 1

#---
def flt_NameEndswith1(name, s):
    if name.endswith(s):
        return 1

def flt_NameEndswith1_IC(name, s):
    if name.casefold().endswith(s):
        return 1

def flt_NameEndswith2(name, ss):
    for s in ss:
        if name.endswith(s):
            return 1

def flt_NameEndswith2_IC(name, ss):
    for s in ss:
        if name.casefold().endswith(s):
            return 1

#---
def flt_NameWildcard1(name, w):
    if fnmatch.fnmatchcase(name, w):
        return 1

def flt_NameWildcard1_IC(name, w):
    if fnmatch.fnmatchcase(name.casefold(), w):
        return 1

def flt_NameWildcard2(name, ww):
    for w in ww:
        if fnmatch.fnmatchcase(name, w):
            return 1

def flt_NameWildcard2_IC(name, ww):
    for w in ww:
        if fnmatch.fnmatchcase(name.casefold(), w):
            return 1

#---
def flt_NameRegexp(name, regExp):
    if regExp.search(name):
        return 1

#--- filter Name func map ---
# keys are: name of match mode, 1 query or >=2 queries, IgnoreCase
flt_NameMatchers = {
            ('Exact',      1, 0): flt_NameExact1,
            ('Contains',   1, 0): flt_NameContains1,
            ('StartsWith', 1, 0): flt_NameStartswith1,
            ('EndsWith',   1, 0): flt_NameEndswith1,
            ('WildCard',   1, 0): flt_NameWildcard1,
            ('RegExp',     1, 0): flt_NameRegexp,

            ('Exact',      1, 1): flt_NameExact1_IC,
            ('Contains',   1, 1): flt_NameContains1_IC,
            ('StartsWith', 1, 1): flt_NameStartswith1_IC,
            ('EndsWith',   1, 1): flt_NameEndswith1_IC,
            ('WildCard',   1, 1): flt_NameWildcard1_IC,
            ('RegExp',     1, 1): flt_NameRegexp,

            ('Exact',      2, 0): flt_NameExact2,
            ('Contains',   2, 0): flt_NameContains2,
            ('StartsWith', 2, 0): flt_NameStartswith2,
            ('EndsWith',   2, 0): flt_NameEndswith2,
            ('WildCard',   2, 0): flt_NameWildcard2,

            ('Exact',      2, 1): flt_NameExact2_IC,
            ('Contains',   2, 1): flt_NameContains2_IC,
            ('StartsWith', 2, 1): flt_NameStartswith2_IC,
            ('EndsWith',   2, 1): flt_NameEndswith2_IC,
            ('WildCard',   2, 1): flt_NameWildcard2_IC,
            }


#--- filter Content functions ----------------------------------------
# fl is opened file

def flt_ContContains(fl, s):
    for line in fl:
        if s in line:
            return 1

def flt_ContContains_IC(fl, s):
    for line in fl:
        if s in line.casefold():
            return 1

#---
def flt_ContStartswith(fl, s):
    for line in fl:
        if line.startswith(s):
            return 1

def flt_ContStartswith_IC(fl, s):
    for line in fl:
        if line.casefold().startswith(s):
            return 1

#---
def flt_ContWildcard(fl, w):
    for line in fl:
        if fnmatch.fnmatchcase(line, w):
            return 1

def flt_ContWildcard_IC(fl, w):
    for line in fl:
        if fnmatch.fnmatchcase(line.casefold(), w):
            return 1

#---
def flt_ContRegexp(fl, regExp):
    for line in fl:
        if regExp.search(line):
            return 1

#--- filter Content func map ---
flt_ContMatchers = {
            ('Contains',   0): flt_ContContains,
            ('StartsWith', 0): flt_ContStartswith,
            ('WildCard',   0): flt_ContWildcard,
            ('RegExp',     0): flt_ContRegexp,

            ('Contains',   1): flt_ContContains_IC,
            ('StartsWith', 1): flt_ContStartswith_IC,
            ('WildCard',   1): flt_ContWildcard_IC,
            ('RegExp',     1): flt_ContRegexp,
            }


#--- filter Time, Size functions -------------------------------------
def make_comp_func(x, z, att):
    if (x is not None) and (z is not None):
        return lambda y: x < getattr(y, att) < z
    elif (x is not None) and (z is None):
        return lambda y: x < getattr(y, att)
    elif (x is None) and (z is not None):
        return lambda y: getattr(y, att) < z


#--- DirEntry.stat() functions ---------------------------------------
# function for getting values for DirEntry stat object

def enst_mtime(st):
    return _strftime(TIME_FORMAT, _localtime(st.st_mtime))

def enst_ctime(st):
    return _strftime(TIME_FORMAT, _localtime(st.st_ctime))

def enst_atime(st):
    return _strftime(TIME_FORMAT, _localtime(st.st_atime))

def enst_mode(st):
    return _filemode(st.st_mode)

def enst_uid(st):
    return st.st_uid

def enst_gid(st):
    return st.st_gid

def enst_nlink(st):
    return st.st_nlink

def enst_ino(st):
    return st.st_ino

#--- DirEntry stat func map ---
# (there is no enst_size, Size is handled specially)
enst_Functions = {
            'MTIME': enst_mtime,
            'CTIME': enst_ctime,
            'ATIME': enst_atime,
            'MODE':  enst_mode,
            'UID':   enst_uid,
            'GID':   enst_gid,
            'NLINK': enst_nlink,
            'INO':   enst_ino,
            }


#---------------------------------------------------------------------

def start_GUI(configDir, startupDir, startupLog):
    root = tk.Tk()
    Application(root, configDir, startupDir, startupLog)
    root.mainloop()

# The End
