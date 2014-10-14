# Copyright (c) 2014, The Flame Authors.
# All rights reserved.
# Author: Chao Xiong <fancysimon@gmail.com>

import argparse
import parser
from util import *

_cmd_parser = None

class CmdParser(object):
    """CmdParser

    Parses user's input and provides hint.
    flame {command} [options] targets

    """
    def __init__(self):
        (self.options, self.targets) = self.CmdParse()

        for t in self.targets:
            if t.startswith('-'):
                ErrorExit('unregconized option %s, use flame [action] '
                                   '--help to get all the options' % t)

        command = self.options.command
        actions = {
            'build': self.CheckBuildCommand,
            'run': self.CheckRunCommand,
            'test': self.CheckTestCommand,
            'clean': self.CheckCleanCommand,
            'install': self.CheckInstallCommand
        }
        actions[command]()

    def CmdParse(self):
        cmd_help = 'flame <subcommand> [options...] [targets...]'
        arg_parser = argparse.ArgumentParser(prog='flame', description=cmd_help)

        sub_parser = arg_parser.add_subparsers(
                dest='command', help='Available subcommands')

        build_parser = sub_parser.add_parser(
                'build', help='Build specified targets')

        run_parser = sub_parser.add_parser(
                'run', help='Build and runs a single target')

        test_parser = sub_parser.add_parser(
                'test', help='Build the specified targets and runs tests')

        clean_parser = sub_parser.add_parser(
                'clean', help='Remove all Flame-created output')

        install_parser = sub_parser.add_parser(
                'install', help='Install package')

        self.AddBuildArgs(build_parser)
        self.AddBuildArgs(run_parser)
        self.AddBuildArgs(test_parser)
        self.AddBuildArgs(install_parser)
        self.AddBuildArgs(clean_parser)

        self.AddRunArgs(run_parser)
        self.AddRunArgs(test_parser)
        self.AddInstallArgs(install_parser)
        self.AddInstallArgs(clean_parser)

        return arg_parser.parse_known_args()

    def AddBuildArgs(self, parser):
        parser.add_argument("-j", "--jobs", type=int, dest='jobs',
                default=0, help="Number of jobs to run simultaneously.")
        parser.add_argument("-p", "--profile", type=str, dest='profile',
                default='release', help="Build profile: debug or release.")
        parser.add_argument("--generate-scons", dest='generate_scons',
                action="store_true", help="Generate scons file.")

    def AddRunArgs(self, parser):
        parser.add_argument("--args", type=str, dest='args',
                default='',
                help="Command line arguments to be passed run or test targets.")

    def AddInstallArgs(self, parser):
        parser.add_argument("--prefix", type=str, dest='prefix',
                default='release', help="Install prefix path.")

    def CheckBuildCommand(self):
        """check build options. """
        if (self.options.profile != 'debug' and
            self.options.profile != 'release'):
            ErrorExit('--profile must be "debug" or "release".')

    def CheckRunCommand(self):
        """check run options and the run targets. """
        self.CheckBuildCommand()
        if len(self.targets) == 0:
            ErrorExit('Must specify one target to run.')

    def CheckTestCommand(self):
        """check test optios. """
        self.CheckBuildCommand()

    def CheckCleanCommand(self):
        """check clean options. """
        self.CheckBuildCommand()

    def CheckInstallCommand(self):
        """check install options. """
        self.CheckBuildCommand()

def GetCmdParser():
    '''Get CmdParser singleton.'''
    global _cmd_parser
    if _cmd_parser == None:
        _cmd_parser = CmdParser()
    return _cmd_parser
