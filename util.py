import os
import sys
import multiprocessing

# Global color enabled or not
_color_enabled = (sys.stdout.isatty() and
        os.environ['TERM'] not in ('emacs', 'dumb'))

# _colors
_colors = {}
_colors['red']    = '\033[1;31m'
_colors['green']  = '\033[1;32m'
_colors['yellow'] = '\033[1;33m'
_colors['blue']   = '\033[1;34m'
_colors['purple'] = '\033[1;35m'
_colors['cyan']   = '\033[1;36m'
_colors['white']  = '\033[1;37m'
_colors['gray']   = '\033[1;38m'
_colors['end']    = '\033[0m'

def Colors(name):
    """Return ansi console control sequence from color name"""
    if _color_enabled:
        return _colors[name]
    return ''

def Error(msg):
    """dump error message. """
    msg = 'Flame(error): ' + msg
    if _color_enabled:
        msg = _colors['red'] + msg + _colors['end']
    print >>sys.stderr, msg


def ErrorExit(msg, code=1):
    """dump error message and exit. """
    Error(msg)
    sys.exit(code)


def Warning(msg):
    """dump warning message but continue. """
    msg = 'Flame(warning): ' + msg
    if _color_enabled:
        msg = _colors['yellow'] + msg + _colors['end']
    print >>sys.stderr, msg


def Info(msg, prefix=True):
    """dump info message. """
    if prefix:
        msg = 'Flame(info): ' + msg
    if _color_enabled:
        msg = _colors['cyan'] + msg + _colors['end']
    print >>sys.stderr, msg

def GetCurrentDir():
    return os.getcwd()

def GetRelativeDir(dir1, dir2):
    return os.path.relpath(dir1, dir2)

def GetFlameRootDir():
    flame_root = 'FLAME_ROOT'
    current_dir = GetCurrentDir()
    flame_root_dir = ''
    while not os.path.isfile(flame_root):
        if GetCurrentDir() == '/':
            break
        parent_dir = os.path.join(GetCurrentDir(), '..')
        os.chdir(parent_dir)

    if os.path.isfile(flame_root):
        flame_root_dir = GetCurrentDir()
    os.chdir(current_dir)
    return flame_root_dir

def GetSconsFileName(scons_dir):
    return os.path.join(scons_dir, 'SConstruct')

def GetBuildName():
    return os.path.join(GetCurrentDir(), 'BUILD')

def GetBuildRootDir():
    flame_root = GetFlameRootDir()
    return os.path.join(flame_root, 'flame-bin')

def GetCpuCount():
    return multiprocessing.cpu_count()

def RemoveDuplicate(item_list):
    result_list = []
    for item in item_list:
        if item not in result_list:
            result_list.append(item)
    return result_list

def VarToList(var):
    var_list = var
    if isinstance(var, str):
        var_list = [var]
    return var_list


