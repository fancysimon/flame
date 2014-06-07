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
    parser.add_argument('args', nargs=argparse.REMAINDER)
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
    TestImpl()

def Run():
    RunImpl()

def Clean():
    if CleanImpl():
        Info('Clean success!')
    else:
        Error('Clean failed!')

def BuildImpl():
    Check()
    LoadBuildFiles()
    GenerateSconsRules('build')
    RunScons()
    return True

def TestImpl():
    Check()
    LoadBuildFiles()
    GenerateSconsRules('test')
    RunScons()
    RunTestCases()
    return True

def RunImpl():
    Check()
    LoadBuildFiles()
    GenerateSconsRules('run')
    RunScons()
    RunBinary()
    return True

def CleanImpl():
    Check()
    LoadBuildFiles()
    GenerateSconsRules('build')
    RunScons(True)
    return True

def RunTestCases():
    targets = GetAllTargets()
    test_case_num = 0
    success_test_case_num = 0
    for target in targets:
        if target.type == 'cc_test':
            ret = subprocess.call(target.test_case)
            if ret == 0:
                success_test_case_num += 1
            test_case_num += 1
    if test_case_num == success_test_case_num:
        Info('All test cases passed!')
    else:
        Info('%d test cases passed!' % success_test_case_num)
        Error('%d test cases failed!' % (test_case_num - success_test_case_num))

def RunBinary():
    global _option_args
    if len(_option_args.args) == 0:
        ErrorExit('Must specify one target to run.')
    else:
        # Only run the first target.
        arg = _option_args.args[0]
        fields = arg.split(':')
        if len(fields) == 2:
            if fields[0] != '':
                ErrorExit('Target format is invalid.')
            binary_name = ''
            targets = GetAllTargets()
            for target in targets:
                if target.type == 'cc_binary':
                    if target.name == fields[1]:
                        binary_name = target.binary_name
            if binary_name != '':
                current_dir = GetCurrentDir()
                binary_dir = os.path.dirname(binary_name)
                os.chdir(binary_dir)
                Info('Start to run %s ...' % fields[1])
                ret = subprocess.call(binary_name)
                if ret == 0:
                    Info('Run %s success.' % fields[1])
                else:
                    Error("Run %s failed. The return code is %d." % (fields[1], ret))
                os.chdir(current_dir)
        else:
            ErrorExit('Target format is invalid.')

def LoadBuildFile(target=None):
    global _option_args
    build_name = GetBuildName()
    if not os.path.isfile(build_name):
        ErrorExit('BUILD not find.')
    # Clear targets to load send by sys.argv.
    sys.argv = []
    if target != None:
        sys.argv = [target]
    if _option_args.cmd == 'test':
        sys.argv.append('-test')
    execfile(build_name)

def LoadBuildFiles():
    global _option_args
    Info('Loading BUILDs...')
    if len(_option_args.args) == 0:
        LoadBuildFile()
    else:
        arg = _option_args.args[0]
        current_dir = GetCurrentDir()
        if arg == '...':
            for target_dir, _, _ in os.walk(current_dir):
                os.chdir(target_dir)
                build_name = GetBuildName()
                if not os.path.isfile(build_name):
                    continue
                LoadBuildFile()
            os.chdir(current_dir)
        else:
            fields = arg.split(':')
            if len(fields) == 1:
                target_dir = os.path.join(current_dir, arg)
                if not os.path.isdir(target_dir):
                    ErrorExit('Dir is not exists: %s' % target_dir)
                os.chdir(target_dir)
                LoadBuildFile()
                os.chdir(current_dir)
            elif len(fields) == 2:
                target_dir = os.path.join(current_dir, fields[0])
                if not os.path.isdir(target_dir):
                    ErrorExit('Dir is not exists: %s' % target_dir)
                os.chdir(target_dir)
                LoadBuildFile(fields[1])
                os.chdir(current_dir)
            else:
                ErrorExit('Target format is invalid.')

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
    Info('Jobs number is %d.' % _option_args.jobs)

def GetSconsRules(cmd):
    target_types = []
    if cmd == 'build' or cmd == 'run':
        target_types += ['env', 'cc_library', 'cc_binary']
    elif cmd == 'test':
        target_types += ['env', 'cc_library', 'cc_binary', 'cc_test']
    targets = GetAllTargets()
    scons_rules = []
    scons_rules.append('env = Environment(CPPPATH=[\"%s\"])\n' % (GetFlameRootDir()))
    for target in targets:
        if target.type in target_types:
            scons_rules += target.scons_rules
    return scons_rules

if __name__ == '__main__':
    Main()
