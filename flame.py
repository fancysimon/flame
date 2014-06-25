# Copyright (c) 2014, The Flame Authors.
# All rights reserved.
# Author: Chao Xiong <fancysimon@gmail.com>

'''
Flame.
'''

import os
import subprocess
import sys
from target import *
from target_pool import *
from util import *
from cmd_parser import *

def Main():
    cmd_parser = GetCmdParser()
    ChooseDebugOrRelease()
    cmd_dict = {'build':Build, 'test':Test, 'run':Run, 'clean':Clean, 'install':Install}
    cmd = cmd_dict[cmd_parser.options.command]
    cmd()

def ChooseDebugOrRelease():
    cmd_parser = GetCmdParser()
    if cmd_parser.options.profile == 'release':
        build_dir = GetBuildReleaseRootDir()
    else:
        build_dir = GetBuildDebugRootDir()
    MkdirIfNotExists(build_dir)
    print build_dir
    print GetBuildRootDir()
    Symlink(build_dir, GetBuildRootDir())

def Build():
    LoadBuildFiles()
    GenerateSconsRules('build')
    RunScons('build')
    Info('Build success!')

def Test():
    LoadBuildFiles()
    GenerateSconsRules('test')
    RunScons('test')
    RunTestCases()

def Run():
    LoadBuildFiles()
    GenerateSconsRules('run')
    RunScons('run')
    RunBinary()

def Clean():
    LoadBuildFiles()
    GenerateSconsRules('clean')
    RunScons('clean')
    Info('Clean success!')

def Install():
    LoadBuildFiles()
    GenerateSconsRules('install')
    RunScons('install')
    Info('Install success!')

def RunTestCases():
    cmd_parser = GetCmdParser()
    targets = GetAllTargets()
    test_case_num = 0
    success_test_case_num = 0
    current_dir = GetCurrentDir()
    for target in targets:
        if target.type == 'cc_test':
            MkdirIfNotExists(target.testcase_rundir)
            os.chdir(target.testcase_rundir)
            # Copy testdata symlink to run dir.
            for pair in target.testdata_copy_pair:
                target_dir = os.path.dirname(pair[1])
                MkdirIfNotExists(target_dir)
                Symlink(pair[0], pair[1])
            cmd_list = [target.test_case]
            if cmd_parser.options.args:
                cmd_list += cmd_parser.options.args.split(' ')
            ret = subprocess.call(cmd_list)
            if ret == 0:
                success_test_case_num += 1
            test_case_num += 1
    os.chdir(current_dir)
    if test_case_num == success_test_case_num:
        Info('All test cases passed!')
    else:
        Info('%d test cases passed!' % success_test_case_num)
        Error('%d test cases failed!' % (test_case_num - success_test_case_num))

def RunBinary():
    cmd_parser = GetCmdParser()
    # Only run the first target.
    run_target = cmd_parser.targets[0]
    fields = run_target.split(':')
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
            cmd_list = [binary_name]
            if cmd_parser.options.args:
                cmd_list += cmd_parser.options.args.split(' ')
            os.chdir(binary_dir)
            Info('Start to run %s ...' % fields[1])
            ret = subprocess.call(cmd_list)
            if ret == 0:
                Info('Run %s success.' % fields[1])
            else:
                Error("Run %s failed. The return code is %d." % (fields[1], ret))
            os.chdir(current_dir)
    else:
        ErrorExit('Target format is invalid.')

def LoadBuildFile(target=None):
    cmd_parser = GetCmdParser()
    build_name = GetBuildName()
    if not os.path.isfile(build_name):
        ErrorExit('BUILD not find.')
    # Clear targets to load send by sys.argv.
    sys.argv = []
    if target != None:
        sys.argv = [target]
    if cmd_parser.options.command == 'test':
        sys.argv.append('-test')
    if cmd_parser.options.command in ['install', 'clean'] :
        abs_prefix = os.path.abspath(cmd_parser.options.prefix)
        sys.argv.append('-prefix=%s' % abs_prefix)
    execfile(build_name)

def LoadBuildFiles():
    Check()
    cmd_parser = GetCmdParser()
    Info('Loading BUILDs...')
    if len(cmd_parser.targets) == 0:
        LoadBuildFile()
    else:
        current_dir = GetCurrentDir()
        for option_target in cmd_parser.targets:
            if option_target == '...':
                for target_dir, _, _ in os.walk(current_dir):
                    os.chdir(target_dir)
                    build_name = GetBuildName()
                    if not os.path.isfile(build_name):
                        continue
                    LoadBuildFile()
                os.chdir(current_dir)
                break
            else:
                fields = option_target.split(':')
                if len(fields) == 1:
                    target_dir = os.path.join(current_dir, option_target)
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

def RunScons(cmd):
    cmd_parser = GetCmdParser()
    current_dir = GetCurrentDir()
    blame_root_dir = GetFlameRootDir()
    os.chdir(blame_root_dir)
    cmd_list = ['scons']
    if cmd == 'clean':
        if os.path.isabs(cmd_parser.options.prefix):
            cmd_list.append('install')
        cmd_list.append('-c')
    SelectJobs()
    if cmd_parser.options.jobs > 1:
        cmd_list.append('-j %d' % cmd_parser.options.jobs)
    ret_code = subprocess.call(cmd_list)
    if ret_code != 0:
        ErrorExit('There are some errors!')
    if cmd == 'install' and NeedInstall():
        cmd_list.append('install')
        ret_code = subprocess.call(cmd_list)
        if ret_code != 0:
            ErrorExit('There are some errors when install!')

    scons_file_name = GetSconsFileName(GetFlameRootDir())
    os.remove(scons_file_name)
    os.chdir(current_dir)

def Check():
    if GetFlameRootDir() == '':
        ErrorExit('FLAME_ROOT not find!')

def SelectJobs():
    cmd_parser = GetCmdParser()
    if cmd_parser.options.jobs <= 0:
        jobs = GetCpuCount()
        if jobs <= 4:
            jobs *= 2
        elif jobs > 8:
            jobs = 8
        cmd_parser.options.jobs = jobs
    Info('Jobs number is %d.' % cmd_parser.options.jobs)

def GetSconsRules(cmd):
    cmd_parser = GetCmdParser()
    target_types = ['env', 'cc_library', 'cc_binary', 'proto_library', 'cc_test']
    if cmd == 'install':
        target_types += ['extra_export']
    #elif cmd in ['test', 'clean']:
    #    target_types += ['cc_test']

    scons_rules = []
    scons_rules.append('import SCons\n\n')
    scons_rules.append('env = Environment(CPPPATH=[\"%s\", \"%s\"])\n\n' % (GetFlameRootDir(), GetBuildRootDir()))

    # Add c++ flags.
    cpp_flags = ['-DNDEBUG', '-O2']
    if cmd_parser.options.profile == 'debug':
        cpp_flags = ['-g', '-DDEBUG']
    scons_rules.append('env.Append(CPPFLAGS=%s)\n\n' % (cpp_flags))

    # Add builder for protobuf.
    scons_rules += ProtoBuilderRules()

    targets = GetAllTargets()
    for target in targets:
        if target.type in target_types:
            scons_rules += target.scons_rules
            scons_rules.append('\n')
        if cmd in ['install', 'clean']:
            scons_rules += target.scons_rules_for_install
            scons_rules.append('\n')
    return scons_rules

def NeedInstall():
    targets = GetAllTargets()
    scons_rules = []
    for target in targets:
        scons_rules += target.scons_rules_for_install
    return len(scons_rules) > 0

if __name__ == '__main__':
    Main()
