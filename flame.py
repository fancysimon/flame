# Copyright (c) 2014, The Flame Authors.
# All rights reserved.
# Author: Chao Xiong <fancysimon@gmail.com>

import argparse
import os
import parser
import subprocess
import sys
from target import *
from util import *

def ParseOption():
    parser = argparse.ArgumentParser()
    parser.add_argument("cmd", default='build', help="Build command: build test run clean")
    args = parser.parse_args(sys.argv[1:])
    return args

def Main():
    args = ParseOption()
    if args.cmd not in ['build', 'test', 'run', 'clean']:
        ErrorExit('cmd is invalid.')
    cmd_dict = {'build':Build, 'test':Test, 'run':Run, 'clean':Clean}
    cmd = cmd_dict[args.cmd]
    cmd()

def Build():
    if not BuildImpl():
        Error('Build failed!')
    else:
        Info('Build success!')

def Test():
    if BuildImpl():
        if not TestImpl():
            Error('Run test cases failed!')
        else:
            Info('Run test cases success!')
    else:
        Error('Build failed!')

def Run():
    if BuildImpl():
        if not RunImpl():
            Error('Run failed!')
        else:
            Info('Run success!')
    else:
        Error('Build failed!')

def Clean():
    if CleanImpl():
        Info('Clean success!')
    else:
        Error('Clean failed!')

def BuildImpl():
    Check()
    LoadBuildFile()
    GenerateSconsRule('build')
    RunScons()
    return True

def TestImpl():
    LoadBuildFile()
    GenerateSconsRule('test')
    RunScons()
    return True

def RunImpl():
    LoadBuildFile()
    GenerateSconsRule('run')
    RunScons()
    return True

def CleanImpl():
    Check()
    LoadBuildFile()
    GenerateSconsRule('build')
    RunScons(True)
    return True

def LoadBuildFile():
    InitSconsRule()
    build_name = GetBuildName()
    if not os.path.isfile(build_name):
        ErrorExit('BUILD not find.')
    Info('Loading BUILDs...')
    # Clear targets to load send by sys.argv.
    sys.argv = []
    execfile(build_name)

def GenerateSconsRule(cmd):
    WriteRuleForAllTargets()
    scons_rules = GetSconsRule(cmd)
    if len(scons_rules) == 0:
        ErrorExit('No targets to build.')
    flame_root_dir = GetFlameRootDir()
    scons_file_name = GetSconsFileName(flame_root_dir)
    scons_file = open(scons_file_name, 'w')
    for rule in scons_rules:
        scons_file.write(rule)
    scons_file.close()

def RunScons(clean=False):
    current_dir = GetCurrentDir()
    blame_root_dir = GetFlameRootDir()
    os.chdir(blame_root_dir)
    if not clean:
        ret_code = subprocess.call(['scons'])
    else:
        ret_code = subprocess.call(['scons', '-c'])
    os.chdir(current_dir)
    if ret_code != 0:
        ErrorExit('There are some errors!')

def Check():
    if GetFlameRootDir() == '':
        ErrorExit('FLAME_ROOT not find!')

if __name__ == '__main__':
    Main()
