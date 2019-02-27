# Filter functions.

from fnmatch import fnmatchcase
from time import strftime, localtime
from stat import filemode

from .constants import TIME_FORMAT

__all__ = ['flt_NameMatchers', 'flt_ContMatchers', "enst_Functions", 'make_comp_func']


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
    if fnmatchcase(name, w):
        return 1

def flt_NameWildcard1_IC(name, w):
    if fnmatchcase(name.casefold(), w):
        return 1

def flt_NameWildcard2(name, ww):
    for w in ww:
        if fnmatchcase(name, w):
            return 1

def flt_NameWildcard2_IC(name, ww):
    for w in ww:
        if fnmatchcase(name.casefold(), w):
            return 1

#---
def flt_NameRegexp(name, regExp):
    if regExp.search(name):
        return 1

#--- filter Name func map ---
# keys are: (name of match mode, 1 query or >=2 queries, IgnoreCase)
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
        if fnmatchcase(line, w):
            return 1

def flt_ContWildcard_IC(fl, w):
    for line in fl:
        if fnmatchcase(line.casefold(), w):
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


#--- DirEntry.stat() functions ---------------------------------------
# Functions for getting values for DirEntry stat object.
# There is no enst_size because Size is handled specially.

def enst_mtime(st):
    return strftime(TIME_FORMAT, localtime(st.st_mtime))

def enst_ctime(st):
    return strftime(TIME_FORMAT, localtime(st.st_ctime))

def enst_atime(st):
    return strftime(TIME_FORMAT, localtime(st.st_atime))

def enst_mode(st):
    return filemode(st.st_mode)

def enst_uid(st):
    return st.st_uid

def enst_gid(st):
    return st.st_gid

def enst_nlink(st):
    return st.st_nlink

def enst_ino(st):
    return st.st_ino

def enst_dev(st):
    return st.st_dev

#--- DirEntry stat func map ---
enst_Functions = {
            'MTIME': enst_mtime,
            'CTIME': enst_ctime,
            'ATIME': enst_atime,
            'MODE':  enst_mode,
            'UID':   enst_uid,
            'GID':   enst_gid,
            'NLINK': enst_nlink,
            'INO':   enst_ino,
            'DEV':   enst_dev,
            }


#--- filter Time, Size functions -------------------------------------
def make_comp_func(x, z, att):
    if (x is not None) and (z is not None):
        return lambda y: x < getattr(y, att) < z
    elif (x is not None) and (z is None):
        return lambda y: x < getattr(y, att)
    elif (x is None) and (z is not None):
        return lambda y: getattr(y, att) < z


# The End
