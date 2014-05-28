# Copyright (c) 2014, The Flame Authors.
# All rights reserved.
# Author: Chao Xiong <fancysimon@gmail.com>

import os
import copy
from util import *

_target_pool = {}
_sorted_target_node_list = []

class Target(object):
    def __init__(self, name, target_type, srcs, deps, scons_target_type, prebuilt, incs):
        self.name = name
        self.type = target_type
        self.srcs = srcs
        if isinstance(self.srcs, str):
            self.srcs = [self.srcs]
        self.deps = deps
        if isinstance(self.deps, str):
            self.deps = [self.deps]
        self.incs = incs
        if isinstance(self.incs, str):
            self.incs = [self.incs]
        self.scons_target_type = scons_target_type
        self.current_dir = GetCurrentDir()
        self.build_root_dir = GetBuildRootDir()
        self.relative_dir = GetRelativeDir(self.current_dir, GetFlameRootDir())
        self.flame_root_dir = GetFlameRootDir()
        self.key = os.path.join(self.current_dir, self.name)
        self.system_library_list = []
        self.dep_library_list = []
        self.dep_paths = []
        self.dep_header_list = []
        self.recursive_library_list = []
        self.scons_rules = []
        self.relative_name = os.path.join(self.relative_dir, self.name)
        self.relative_name = self.RemoveSpecialChar(self.relative_name)
        self.prebuilt = prebuilt
        self.target_name = self.relative_name

    def WriteRule(self):
        env = self.relative_name + '_env'
        env = self.RemoveSpecialChar(env)
        rule = '%s = env.Clone()\n' % (env)
        self.AddRule(rule)
        # Include path.
        if len(self.dep_header_list) > 0:
            rule = '%s.Append(CPPPATH=%s)\n' % (env, self.dep_header_list)
            self.AddRule(rule)
        # Prebuild library
        if self.prebuilt == 1:
            rule = 'Command("build64_release/AliWS/libAliWS.a", "AliWS/lib64_release/libAliWS.a", Copy("$TARGET", "$SOURCE"))\n'
            prebuilt_name = 'lib%s.a' % (self.name)
            prebuilt_target = os.path.join(self.build_root_dir, self.relative_dir, prebuilt_name)
            prebuilt_source = os.path.join(self.flame_root_dir, self.relative_dir, 'lib', prebuilt_name)
            rule = 'Command(\"%s\", \"%s\", Copy(\"$TARGET\", \"$SOURCE\"))\n' % (prebuilt_target, prebuilt_source)
            self.AddRule(rule)
            rule = '%s = env.File(\"%s\")\n' % (self.relative_name, prebuilt_target)
            self.AddRule(rule)
            return
        # Not prebuilt.
        srcs = []
        for src in self.srcs:
            src_with_path = os.path.join(self.current_dir, src)
            srcs.append(src_with_path)
        full_name = os.path.join(self.build_root_dir, self.relative_dir, self.name)
        objs = []
        for src_with_path in srcs:
            src = os.path.basename(src_with_path)
            obj_target_name = os.path.join(self.build_root_dir, self.relative_dir,
                    self.name + '.objs', src + '.o')
            obj = self.relative_dir + "_" + src + '_obj'
            obj = self.RemoveSpecialChar(obj)
            rule = '%s = %s.SharedObject(target = \"%s\", source = \"%s\")\n' % (
                    obj, env, obj_target_name, src_with_path)
            objs.append(obj)
            self.AddRule(rule)
        objs_name = self.relative_dir + '_' + self.name + '_objs'
        objs_name = self.RemoveSpecialChar(objs_name)
        rule = '%s = [%s]\n' % (objs_name, ','.join(objs))
        self.AddRule(rule)
        #deps = self.dep_library_list
        deps = self.FormatDepLibrary()
        rule = '%s = %s.%s(\"%s\", %s, LIBS=%s)\n' % (
                self.target_name, env, self.scons_target_type,
                full_name, objs_name, deps)
        #rule = '%s = %s.%s(\"%s\", %s, LIBS=%s, LIBPATH=%s)\n' % (
        #        self.target_name, env, self.scons_target_type,
        #        full_name, objs_name, deps, self.dep_paths)
        #rule = '%s = %s.%s(\"%s\", %s, LIBS=%s, LIBPATH=%s)\n' % (
        #        self.name, env, self.scons_target_type,
        #        full_name, srcs, deps, self.dep_paths)
        self.AddRule(rule)

    def RemoveSpecialChar(self, name):
        name = name.replace('/', '_')
        name = name.replace('-', '_')
        name = name.replace('.', '_')
        name = name.replace(':', '_')
        return name

    def FormatDepLibrary(self):
        res = '['
        for library in self.dep_library_list:
            res += library + ','
        for library in self.system_library_list:
            res += '\"' + library + '\",'
        res += ']'
        return res

    def AddRule(self, rule):
        self.scons_rules.append(rule)

    def ParseAndAddTarget(self):
        self.ParseDeps()
        self.ParseDepsRecursive()
        self.AddToTargetPool()

    def AddPrebuiltTarget(self):
        self.AddToTargetPool()

    def AddToTargetPool(self):
        global _target_pool
        if self.key not in _target_pool:
            _target_pool[self.key] = self

    def ParseDeps(self):
        self.dep_library_list = []
        self.dep_paths = []
        self.dep_header_list = []
        for dep in self.deps:
            if len(dep) == 0:
                continue
            if dep[0] == '#':
                self.system_library_list.append(dep[1:])
            elif dep[0] == ':':
                dep_library = os.path.join(self.relative_dir, dep[1:])
                dep_library = self.RemoveSpecialChar(dep_library)
                self.dep_library_list.append(dep_library)
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
                dep_library = self.RemoveSpecialChar(dep[2:])
                self.dep_library_list.append(dep_library)
                target_key = os.path.join(self.flame_root_dir, library_path, library_name)
                self.recursive_library_list.append(target_key)
                dep_path = os.path.join(self.build_root_dir, library_path)
                self.dep_paths.append(dep_path)
            else:
                ErrorExit('The format of deps(%s) is invalid.' % (dep))
        # Include path.
        if len(self.incs) > 0:
            for inc in self.incs:
                inc_with_path = os.path.join(self.current_dir, inc)
                self.dep_header_list.append(inc_with_path)

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
            # Clear build targets.
            sys.argv = []
            os.chdir(current_dir)

def WriteRuleForAllTargets():
    global _target_pool
    global _sorted_target_node_list
    _sorted_target_node_list = TopologySort()
    ComplementSubDeps(_sorted_target_node_list)
    for node in _sorted_target_node_list:
        target = _target_pool[node.key]
        target.WriteRule()

def GetAllTargets():
    global _target_pool
    global _sorted_target_node_list
    targets = []
    for node in _sorted_target_node_list:
        target = _target_pool[node.key]
        targets.append(target)
    return targets

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

def ComplementSubDeps(sorted_target_node_list):
    global _target_pool
    for node in sorted_target_node_list:
        target = _target_pool[node.key]
        for key in target.recursive_library_list:
            sub_target = _target_pool[key]
            # Dependant sub library must be put after this library,
            # or there will be link error(undefined reference to).
            target.dep_library_list += sub_target.dep_library_list
            target.system_library_list += sub_target.system_library_list
            target.dep_paths += sub_target.dep_paths
            target.dep_header_list += sub_target.dep_header_list
        target.dep_library_list = RemoveDuplicate(target.dep_library_list)
        target.system_library_list = RemoveDuplicate(target.system_library_list)
        target.dep_paths = RemoveDuplicate(target.dep_paths)
        target.dep_header_list = RemoveDuplicate(target.dep_header_list)

class CcTarget(Target):
    def __init__(self, name, target_type, srcs, deps, scons_target_type, prebuilt, incs):
        Target.__init__(self, name, target_type, srcs, deps, scons_target_type, prebuilt, incs)
        # build targets are send by sys.argv
        build_target_list = sys.argv
        if len(build_target_list) == 0 or name in build_target_list:
            if self.prebuilt == 0:
                self.ParseAndAddTarget()
            elif self.prebuilt == 1:
                self.AddPrebuiltTarget()

# TODO: warning
def cc_library(name, srcs=[], deps=[], prebuilt=0, incs=[], warning='yes'):
    target = CcTarget(name, 'cc_library', srcs, deps, 'Library', prebuilt, incs)

def cc_plugin(name, srcs=[], deps=[], prebuilt=0, incs=[], warning='yes'):
    target = CcTarget(name, 'cc_plugin', srcs, deps, 'SharedLibrary', prebuilt, incs)

def cc_binary(name, srcs, deps=[], prebuilt=0, incs=[], warning='yes'):
    target = CcTarget(name, 'cc_binary', srcs, deps, 'Program', prebuilt, incs)

def cc_test(name, srcs, deps=[], prebuilt=0, incs=[], warning='yes'):
    target = CcTarget(name, 'cc_test', srcs, deps, 'Program', prebuilt, incs)

