# Copyright (c) 2014, The Flame Authors.
# All rights reserved.
# Author: Chao Xiong <fancysimon@gmail.com>

import argparse
import os
import parser
import subprocess
import sys
from target import *
from target_pool import *
from util import *

_option_args = None

def ParseOption():
    global _option_args
    parser = argparse.ArgumentParser()
    parser.add_argument("cmd", default='build',
                        help="Build command: build test run clean.")
    parser.add_argument("-j", "--jobs", type=int, dest='jobs',
                        default=0, help="Number of jobs to run simultaneously.")
    parser.add_argument("-s", "--generate-dynamic", type=int, dest='dynamic',
                        default=0, help="Generate dynamic library(so).")
    _option_args = parser.parse_args(sys.argv[1:])
    return parser

def Main():
    global _option_args
    parser = ParseOption()
    if _option_args.cmd not in ['build', 'test', 'run', 'clean']:
        parser.print_help()
        ErrorExit('cmd is invalid.')
    cmd_dict = {'build':Build, 'test':Test, 'run':Run, 'clean':Clean}
    cmd = cmd_dict[_option_args.cmd]
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
    GenerateSconsRules('build')
    RunScons()
    return True

def TestImpl():
    LoadBuildFile()
    GenerateSconsRules('test')
    RunScons()
    return True

def RunImpl():
    LoadBuildFile()
    GenerateSconsRules('run')
    RunScons()
    return True

def CleanImpl():
    Check()
    LoadBuildFile()
    GenerateSconsRules('build')
    RunScons(True)
    return True

def LoadBuildFile():
    global _option_args
    build_name = GetBuildName()
    if not os.path.isfile(build_name):
        ErrorExit('BUILD not find.')
    Info('Loading BUILDs...')
    # Clear targets to load send by sys.argv.
    sys.argv = []
    if _option_args.dynamic == 1:
        sys.argv.append('-dynamic')
    execfile(build_name)

def GenerateSconsRules(cmd):
    WriteRuleForAllTargets()
    scons_rules = GetSconsRules(cmd)
    if len(scons_rules) == 0:
        ErrorExit('No targets to build.')
    flame_root_dir = GetFlameRootDir()
    scons_file_name = GetSconsFileName(flame_root_dir)
    scons_file = open(scons_file_name, 'w')
    for rule in scons_rules:
        scons_file.write(rule)
    scons_file.close()

def RunScons(clean=False):
    global _option_args
    current_dir = GetCurrentDir()
    blame_root_dir = GetFlameRootDir()
    os.chdir(blame_root_dir)
    cmd_list = ['scons']
    if clean:
        cmd_list.append('-c')
    SelectJobs()
    if _option_args.jobs > 1:
        cmd_list.append('-j %d' % _option_args.jobs)
    ret_code = subprocess.call(cmd_list)
    os.chdir(current_dir)
    if ret_code != 0:
        ErrorExit('There are some errors!')

def Check():
    if GetFlameRootDir() == '':
        ErrorExit('FLAME_ROOT not find!')

def SelectJobs():
    global _option_args
    if _option_args.jobs <= 0:
        jobs = GetCpuCount()
        if jobs <= 4:
            jobs *= 2
        elif jobs > 8:
            jobs = 8
        _option_args.jobs = jobs

def GetSconsRules(cmd):
    target_types = []
    if cmd == 'build' or cmd == 'run':
        target_types += ['env', 'cc_library', 'cc_binary', 'cc_plugin']
    elif cmd == 'test':
        target_types += ['env', 'cc_library', 'cc_binary', 'cc_plugin', 'cc_test']
    targets = GetAllTargets()
    scons_rules = []
    scons_rules.append('env = Environment(CPPPATH=[\"%s\"])\n' % (GetFlameRootDir()))
    for target in targets:
        if target.type in target_types:
            scons_rules += target.scons_rules
    return scons_rules

if __name__ == '__main__':
    Main()
