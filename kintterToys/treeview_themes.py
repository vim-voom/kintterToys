# This module handles treeview theme config files.

import os
from . import config_file_parser as cfp

# {theme-name : path-to-theme-file, }
THEMES = {}

# validation table for theme config files <theme-name>.config.py
options_table = {
        # ttk.Treeview style
        'BG_FIELD': cfp.isStr,
        'BG'      : cfp.isStr,
        'FG'      : cfp.isStr,
        'BG_SEL'  : cfp.isStr,
        'FG_SEL'  : cfp.isStr,
        # ttk.Treeview tags
        'STRIPE_BG': cfp.isStr,
        'DIR_BG'   : cfp.isStr,
        'DIR_FG'   : cfp.isStr,
        'LINK_BG'  : cfp.isStr,
        'LINK_FG'  : cfp.isStr,
        'OTHER_BG' : cfp.isStr,
        'OTHER_FG' : cfp.isStr,
        'DIR_FONT_STYLE'  : cfp.isFontStyle,
        'LINK_FONT_STYLE' : cfp.isFontStyle,
        'OTHER_FONT_STYLE': cfp.isFontStyle,
        }


def get_themes(dir1, dir2):
    """Parse directoris for theme config files
        <theme-name>.config.py
    Save paths. Return list of theme names.
    """
    themes = []
    for d in (dir1, dir2):
        if not os.path.isdir(d):
            continue
        for n in os.listdir(d):
            p = os.path.join(d, n)
            if not os.path.isfile(p) or not n.endswith('.config.py'):
                continue
            th = n[:-10].strip()
            if th:
                THEMES[th] = p
    themes = sorted(THEMES.keys())
    return themes


def parse_theme(theme, p=None):
    """Parse user theme config file corresponding to `theme`.
    If `p`, parse file with path `p`.
    Return (theme dict, error list)."""
    if p:
        opts, errs = cfp.parse(p, options_table)
    else:
        if theme in THEMES:
            p = THEMES[theme]
            opts, errs = cfp.parse(p, options_table)
            if errs:
                errs.insert(0, 'Errors parsing config file: %s' %p)
        else:
            opts, errs = {}, ['Results Theme not available: "%s"' %theme]
    # add missing options
    for o in options_table:
        if not o in opts:
            opts[o] = ''
    return opts, errs
