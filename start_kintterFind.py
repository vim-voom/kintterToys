#!/usr/bin/env python3

import sys
if sys.version_info < (3, 4):
    raise RuntimeError('kintterFind requires Python version >=3.4')
import kintterToys.kintterFind

configDir, startupDir, startupLog = '', '', []

if len(sys.argv) > 1:
    import getopt
    args = sys.argv[1:]
    try:
        opts, x = getopt.getopt(args, '', ['configdir=', 'directory='])
    except getopt.GetoptError as e:
        startupLog.append('**getopt.GetoptError** while parsing arguments for start_kintterFind.py:\n    %s' %e)
    else:
        for (o, v) in opts:
            if o == '--configdir':
                configDir = v
            elif o == '--directory':
                startupDir = v

if __name__ == '__main__':
    kintterToys.kintterFind.start_GUI(configDir, startupDir, startupLog)

# The End
