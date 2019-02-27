This folder contains kintterToys config files "*.config.py".
The syntax of config files is explained in "kintterFind.config.py".
Encoding is utf-8, line endings are \n.


File "kintterFind.config.py"
============================

This is a reference config file for kintterFind. It includes all kintterFind
startup options with their default values. It is not used from this location
and is provided for convenience.

If you want to change some options, copy  this file to your kintterToys config
directory, which by default is "~/.config/kintterToys/", and edit it. Options
that are not modified may be removed.


Folder "results_themes"
=======================

This folder contains Results Theme files which change the appearance of data
rows in kintterFind's tab Results (content of Treeview widget).

Theme files must be named "<some-theme-name>.config.py".
The format is the same as for "kintterFind.config.py", see comments there.
To apply a theme during startup, use option RESULTS_THEME.

kintterFind obtains the list of available Results Themes during startup from
the list of "*.config.py" files in this folder and from the namesake folder in
the kintterToys config directory. Files in the latter override the former.

If you want to add your own theme, copy some "*.config.py" file to directory
"results_themes" in the kintteToys config directory, rename the file (e.g.,
"my-theme.config.py") and edit it.

Themes present in this folder and in the namesake folder in the kintterToys
config directory will be listed in detachable menu

    View -> Results Theme

Each time a theme is clicked in that menu, the corresponding file is parsed and
the theme is re-applied. This means a theme file can be edited and tested
without restating the program.


