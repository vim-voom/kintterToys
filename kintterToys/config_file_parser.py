# -*- coding: utf-8 -*-

"""
kintterToys configuration file parser. Usage:
    import config_file_parser
    options, errors = config_file_parser.parse(configfile, validation_table)

The syntax of config file is that of a Python file that has only module-level
constants. Example:

    TITLE = 'Gadget'
    WIDTH = 638
    IS_RESIZABLE=False
    # some color schemes
    color_schemes = {
            'default':['white', 'black'],
            # bright colors
            'garish': ['yellow', 'pink'],
            }
    favorite_schemes = ('default',)

The general syntax is

    option1 = expression1 line 1
        expression1 line 2
        expression1 line 3
    ...
    option2 = expresssion2 line 1
    ...

Each string `option` must be at the start of line and be a valid identifier.

Everything after "option = " and until the next option line is treated as an
`expression`. It is converted into value with `ast.literal_eval(expression)`.
If no exception, the value is assigned to key `option` in dictionary "options".
If there is an exception, info about exception is appended to list "errors".

Lines at the start of file before the first "option = " line are ignored.
Blank lines and commented lines are ignored.

If validation_table is provided, check each options against it. Remove invalid
option from results and add error to errors.
"""

from ast import literal_eval

def parse(configfile, validation_table=None):
    """Parse configfile. Return (options, errors)."""

    options, errors = {}, []

    f = None
    try:
        f = open(configfile, 'rt', encoding='utf-8', newline='\n')
    except Exception as err:
        errors.append('    %s' %(err))
    except:
        errors.append('    %s' %('exception other than Exception'))
    if not f:
        errors.insert(0, '**CANNOT OPEN CONFIG FILE**:')
        return options, errors

    opt, expr, val = '', '', ''
    for ln in f:
        # skip blank lines and commented lines
        if not ln or ln.lstrip().startswith('#'):
            continue

        isOpt = False
        parts = ln.split('=', 1)
        if len(parts) == 2:
            p1, p2 = parts[0].rstrip(), parts[1]
            if p1.isidentifier():
                isOpt = True
        # current line is a new opt=expr line
        if isOpt:
            # save data from previous expr lines
            if expr:
                try:
                    val = literal_eval(expr)
                except Exception as err:
                    errors.append('    %s -- %s' %(opt, err))
                except:
                    errors.append('    %s -- %s' %(opt, 'exception other than Exception'))
                else:
                    options[opt] = val
                opt, expr, val = '', '', ''
            # start new data
            opt, expr, val = p1, p2.lstrip(), ''
        # current line is not a opt=expr line
        else:
            # append line to previous expr lines
            if expr:
                expr += ln

    f.close()

    # last opt=expr
    if expr:
        try:
            val = literal_eval(expr)
        except Exception as err:
            errors.append('    %s -- %s' %(opt, err))
        except:
            errors.append('    %s -- %s' %(opt, 'exception other than Exception'))
        else:
            options[opt] = val
        opt, expr, val = '', '', ''

    if errors:
        errors.insert(0, '**BAD OPTIONS IN CONFIG FILE** (invalid syntax):')

    if validation_table:
        unknownOpts, badtypeOpts = [], []
        for o in options:
            if o not in validation_table:
                unknownOpts.append(o)
                continue
            e = validation_table[o](options[o])
            if e:
                badtypeOpts.append((o, e))
                continue

        if unknownOpts:
            errors.append('**BAD OPTIONS IN CONFIG FILE** (option not known):')
            for o in unknownOpts:
                errors.append('    %s' %o)
                del options[o]

        if badtypeOpts:
            errors.append('**BAD OPTIONS IN CONFIG FILE** (option in wrong format):')
            for oe in badtypeOpts:
                errors.append('    %s -- %s' %(oe[0], oe[1]))
                del options[oe[0]]

    return options, errors


#--- type and format checkers ----------------------------------------

def isBool(o):
    if isinstance(o, bool):
        return 0
    return 'not boolean'


def isInt(o):
    if isinstance(o, int):
        return 0
    return 'not integer'


#def isNum(o):
#    if isinstance(o, int) and o > 0:
#        return 0
#    return 'not integer > 0'


def isStr(o):
    if isinstance(o, str):
        return 0
    return 'not string'


def isSeq(o):
    if isinstance(o, (list, tuple)):
        return 0
    return 'not list or tuple'


#def isDict(o):
#    if isinstance(o, dict):
#        return 0
#    return 'not dictionary'


def isFont(o):
    if not isinstance(o, (list, tuple)):
        return 'bad Font descriptor (not list or tuple)'
    l = len(o)
    if l < 2:
        return 'bad Font descriptor (len < 2)'
    if not isinstance(o[0], str):
        return 'bad Font descriptor (family is not string)'
    if not isinstance(o[1], int):
        return 'bad Font descriptor (size is not integer)'
    if l > 2:
        if not isinstance(o[2], str):
            return 'bad Font descriptor (style is not string)'
        for s in o[2].split():
            if s not in ('bold', 'italic', 'underline', 'overstrike'):
                return 'bad Font descriptor (style is ivalid)'
    if l > 3:
        return 'bad Font descriptor (len > 3)'
    return 0


def isFontStyle(o):
    if not isinstance(o, str):
        return 'bad FontStyle (not string)'
    if o:
        for s in o.split():
            if s not in ('bold', 'italic', 'underline', 'overstrike'):
                return 'bad FontStyle (style is ivalid)'
    return 0


#def isSeqStr(o):
#    if not isinstance(o, (list, tuple)):
#        return 'not list or tuple'
#    for s in o:
#        if not isinstance(s, str):
#            return 'item is not string'
#        if not s.strip():
#            return 'string is empty or blank'
#    return 0


def isMenuTable(o):
    if not isinstance(o, (list, tuple)):
        return 'not list or tuple'
    for r in o:
        if not isinstance(r, (list, tuple)):
            return 'table row is not list or tuple'
        if len(r) != 2:
            return 'table row length is not 2'
        for i in r:
            if not isinstance(i, str):
                return 'item is not string'
            if not i.strip():
                return 'string is empty or blank'
    return 0


def isSeqSeq(o):
    if not isinstance(o, (list, tuple)):
        return 'not list or tuple'
    for i in o:
        if not isinstance(i, (list, tuple)):
            return 'item is not list or tuple'
        if len(i) != 2:
            return 'item\'s length is not 2'
    return 0

# The End
