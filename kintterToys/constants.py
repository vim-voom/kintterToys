# -*- coding: utf-8 -*-

# Default path of config directory. Doesn't work in config file.
CONFIGDIR = '~/.config/kintterToys'

FT_DESCRIP = {'-': 'regular file', 'd': 'directory', 'l': 'symbolic link',
              'c': 'character device', 'b': 'block device', 'p': 'named pipe', 's': 'socket file',
              'D': 'door', 'P': 'event port', 'w': 'whiteout',
              '?': 'unknown', '!': 'does not exist', }

# Log pane: horizontal ruler
LHR = '=' * 70
# Log pane: headline decorators
LD1, LD2 = '--- ', ' ---'

# Time format string. Must be sortable.
# YYYY-MM-DD HH:MM:SS
TIME_FORMAT = '%Y-%m-%d %H:%M:%S'

# sort signs appended to headline text: Low-to-High, High-to-Low
#SL2H, SH2L = ' <', ' >'
SL2H, SH2L = ' ▲', ' ▼'

# on/off signs prepended to text on tabs in notebook Filters
#TAB_ON, TAB_OFF = '* ', '  '
#TAB_ON, TAB_OFF = '■ ', '□ ' # too big
TAB_ON, TAB_OFF = '◼ ', '◻ '

# The End
