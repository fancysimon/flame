# Copyright (c) 2014, The Flame Authors.
# All rights reserved.
# Author: Chao Xiong <fancysimon@gmail.com>

import os
import copy
from util import *

_target_pool = {}
_scons_rules = {}

class Target(object):
    def __init__(self, name, target_type, srcs, deps, scons_target_type):
        self.name = name
        self.type = target_type
        self.srcs = srcs
        self.deps = deps
        self.scons_target_type = scons_target_type
        self.current_dir = GetCurrentDir()
        self.build_root_dir = GetBuildRootDir()
        self.relative_dir = GetRelativeDir(self.current_dir, GetFlameRootDir())
        self.flame_root_dir = GetFlameRootDir()
        self.key = os.path.join(self.current_dir, self.name)
        self.dep_library_list = []
        self.dep_paths = []
        self.recursive_library_list = []

    def WriteRule(self):
        srcs = []
        for src in self.srcs:
            src_with_path = os.path.join(self.current_dir, src)
            srcs.append(src_with_path)
        name = os.path.join(self.build_root_dir, self.relative_dir, self.name)
        deps = self.dep_library_list
        env = self.type + '_env'
        rule = '%s = env.Clone()\n' % (env)
        self.AddRule(rule)
        rule = '%s = %s.%s(\"%s\", %s, LIBS=%s, LIBPATH=%s)\n' % (
                self.name, env, self.scons_target_type,
                name, srcs, deps, self.dep_paths)
        self.AddRule(rule)

    def AddRule(self, rule):
        global _scons_rules
        if self.type not in _scons_rules:
            _scons_rules[self.type] = []
        if rule in _scons_rules[self.type]:
            return
        _scons_rules[self.type].append(rule)

    def ParseAndAddTarget(self):
        self.ParseDeps()
        self.ParseDepsRecursive()
        self.AddToTargetPool()

    def AddToTargetPool(self):
        global _target_pool
        if self.key not in _target_pool:
            _target_pool[self.key] = self

    def ParseDeps(self):
        self.dep_library_list = []
        self.dep_paths = []
        for dep in self.deps:
            if len(dep) == 0:
                continue
            if dep[0] == '#':
                self.dep_library_list.append(dep[1:])
            elif dep[0] == ':':
                self.dep_library_list.append(dep[1:])
                target_key = os.path.join(self.current_dir, dep[1:])
                self.recursive_library_list.append(target_key)
                dep_path = os.path.join(self.build_root_dir, self.relative_dir)
                self.dep_paths.append(dep_path)
            elif len(dep) >= 2 and dep[0:2] == '//':
                fields = dep[2:].split(':')
                if len(fields) != 2:
                    ErrorExit('The format of deps(%s) is invalid.' % (dep))
                library_path = fields[0]
                library_name = fields[1]
                self.dep_library_list.append(library_name)
                target_key = os.path.join(self.flame_root_dir, library_path, library_name)
                self.recursive_library_list.append(target_key)
                dep_path = os.path.join(self.build_root_dir, library_path)
                self.dep_paths.append(dep_path)
            else:
                ErrorExit('The format of deps(%s) is invalid.' % (dep))

    def ParseDepsRecursive(self):
        global _target_pool
        for target_key in self.recursive_library_list:
            if target_key in _target_pool:
                continue
            library_path = os.path.dirname(target_key)
            library_name = os.path.basename(target_key)
            current_dir = GetCurrentDir()
            os.chdir(library_path)
            build_name = GetBuildName()
            if not os.path.isfile(build_name):
                ErrorExit('BUILD not find.')
            # Only build |library_name|
            sys.argv = [library_name]
            execfile(build_name)
            os.chdir(current_dir)

def InitSconsRule():
    global _scons_rules
    _scons_rules = {}
    _scons_rules['env'] = ['env = Environment(CPPPATH=[\"%s\"])\n' % (GetFlameRootDir())]

def GetSconsRule(cmd):
    global _scons_rules
    target_types = []
    if cmd == 'build' or cmd == 'run':
        target_types += ['env', 'cc_library', 'cc_binary', 'cc_plugin']
    elif cmd == 'test':
        target_types += ['env', 'cc_library', 'cc_binary', 'cc_plugin', 'cc_test']
    rule_list = []
    for target_type in target_types:
        if target_type in _scons_rules:
            rule_list += _scons_rules[target_type]
    return rule_list

def WriteRuleForAllTargets():
    global _target_pool
    ComplementSubDeps()
    for key, target in _target_pool.items():
        target.WriteRule()

class TargetNode:
    def __init__(self, key, recursive_library_list):
        self.key = key
        self.recursive_library_list = copy.copy(recursive_library_list)

def TopologySort():
    global _target_pool
    target_node_list = []
    for key, target in _target_pool.items():
        node = TargetNode(key, target.recursive_library_list)
        target_node_list.append(node)
    result_list = []
    while True:
        if len(target_node_list) == 0:
            break
        zero_degree_list = filter(lambda x:len(x.recursive_library_list)==0, target_node_list)
        target_node_list = filter(lambda x:len(x.recursive_library_list)>0, target_node_list)
        for node in zero_degree_list:
            for node2 in target_node_list:
                if node.key in node2.recursive_library_list:
                    node2.recursive_library_list.remove(node.key)
        result_list += zero_degree_list
    return result_list

def ComplementSubDeps():
    global _target_pool
    target_node_list = TopologySort()
    for node in target_node_list:
        target = _target_pool[node.key]
        for key in target.recursive_library_list:
            sub_target = _target_pool[key]
            target.dep_library_list += sub_target.dep_library_list
            target.dep_paths += sub_target.dep_paths
        target.dep_library_list = list(set(target.dep_library_list))
        target.dep_paths = list(set(target.dep_paths))

class CcTarget(Target):
    def __init__(self, name, target_type, srcs, deps, scons_target_type):
        Target.__init__(self, name, target_type, srcs, deps, scons_target_type)
        # build targets are send by sys.argv
        build_target_list = sys.argv
        if len(build_target_list) == 0 or name in build_target_list:
            self.ParseAndAddTarget()

def cc_library(name, srcs, deps=[]):
    target = CcTarget(name, 'cc_library', srcs, deps, 'Library')

def cc_plugin(name, srcs, deps=[]):
    target = CcTarget(name, 'cc_plugin', srcs, deps, 'SharedLibrary')

def cc_binary(name, srcs, deps=[]):
    target = CcTarget(name, 'cc_binary', srcs, deps, 'Program')

