# Copyright (c) 2014, The Flame Authors.
# All rights reserved.
# Author: Chao Xiong <fancysimon@gmail.com>

import os
import copy
from util import *
import glob
import string
import target_pool

class Target(object):
    def __init__(self, name, target_type, srcs, deps, scons_target_type,
                incs, export_dynamic, export_static):
        self.name = name
        self.type = target_type
        self.incs = VarToList(incs)
        self.srcs = VarToList(srcs)
        self.SrcReplaceRegex()
        self.deps = VarToList(deps)
        self.objs = []
        self.sub_objs = []
        self.scons_target_type = scons_target_type
        self.export_dynamic = export_dynamic
        self.export_static = export_static
        self.current_dir = GetCurrentDir()
        self.build_root_dir = GetBuildRootDir()
        self.relative_dir = GetRelativeDir(self.current_dir, GetFlameRootDir())
        self.flame_root_dir = GetFlameRootDir()
        self.key = os.path.join(self.current_dir, self.name)
        self.system_library_list = []
        self.prebuilt_library_list = []
        self.prebuilt_static_library_list = []
        self.dep_library_list = []
        self.dep_paths = []
        self.dep_header_list = []
        self.recursive_library_list = []
        self.recursive_library_list_sort = []
        self.scons_rules = []
        self.scons_rules_for_install = []
        self.relative_name = os.path.join(self.relative_dir, self.name)
        self.relative_name = self.RemoveSpecialChar(self.relative_name)
        self.target_name = self.relative_name
        self.dl_suffix = ''
        if self.export_dynamic == 1:
            self.dl_suffix = '_share'
            self.key += self.dl_suffix
            self.target_name += self.dl_suffix
        self.release_prefix = ParseReleasePrefix(sys.argv)
        self.full_name = os.path.join(self.build_root_dir, self.relative_dir, self.name)
        self.prebuilt = 0

    def WriteRule(self):
        self.env = self.relative_name + self.dl_suffix + '_env'
        self.env = self.RemoveSpecialChar(self.env)
        rule = '%s = env.Clone()\n' % (self.env)
        self.AddRule(rule)
        # Include path.
        if len(self.dep_header_list) > 0:
            rule = '%s.Append(CPPPATH=%s)\n' % (self.env, self.dep_header_list)
            self.AddRule(rule)

    def RemoveSpecialChar(self, name):
        name = name.replace('/', '_')
        name = name.replace('-', '_')
        name = name.replace('.', '_')
        name = name.replace(':', '_')
        return name

    def FormatDepLibrary(self):
        res = '['
        if self.export_dynamic == 1:
            for library in self.prebuilt_library_list:
                library = '\"%s\"' % library
                res += library + ','
        elif self.export_static == 1:
            for library in self.prebuilt_static_library_list:
                res += library + ','
        else:
            for library in self.dep_library_list:
                res += library + ','
        for library in self.system_library_list:
            res += '\"%s\",' % library
        res += ']'
        return res

    def AddRule(self, rule):
        self.scons_rules.append(rule)

    def AddRuleForInstall(self, rule):
        self.scons_rules_for_install.append(rule)

    def AddToTargetPool(self):
        targets = target_pool.GetTargetPool()
        if self.key not in targets:
            targets[self.key] = self

    def ParseDepHeader(self):
        # Include path.
        if len(self.incs) > 0:
            for inc in self.incs:
                inc_with_path = os.path.join(self.current_dir, inc)
                self.dep_header_list.append(inc_with_path)

    def SrcReplaceRegex(self):
        new_srcs = []
        for src in self.srcs:
            if '*' in src:
                src_list = glob.glob(src)
                new_srcs += src_list
            else:
                new_srcs.append(src)
        self.srcs = new_srcs

class CcTarget(Target):
    def __init__(self, name, target_type, srcs, deps, scons_target_type,
                incs, export_dynamic, export_static):
        Target.__init__(self, name, target_type, srcs, deps, scons_target_type,
                incs, export_dynamic, export_static)
        # build targets are send by sys.argv
        build_target_list = filter(lambda x:(len(x) > 0 and x[0] != '-'), sys.argv)
        if len(build_target_list) == 0 or name in build_target_list:
            self.ParseAndAddTarget()

    def WriteRule(self):
        Target.WriteRule(self)
        for i in range(len(self.objs)):
            obj = self.objs[i]
            obj_target_name = self.obj_target_names[i]
            src_with_path = self.srcs_with_path[i]
            rule = '%s = %s.SharedObject(target = \"%s\", source = \"%s\")\n' % (
                    obj, self.env, obj_target_name, src_with_path)
            self.AddRule(rule)

        objs_name = self.relative_dir + '_' + self.name + '_objs' + self.dl_suffix
        objs_name = self.RemoveSpecialChar(objs_name)
        if self.export_dynamic == 1 or self.export_static == 1:
            rule = '%s = [%s]\n' % (objs_name, ','.join(self.objs + self.sub_objs))
        else:
            rule = '%s = [%s]\n' % (objs_name, ','.join(self.objs))
        self.AddRule(rule)
        deps = self.FormatDepLibrary()
        if self.export_dynamic == 1:
            # Dynamic dependence library can not link with absolutive path.
            rule = '%s = %s.%s(\"%s\", %s, LIBS=%s, LIBPATH=%s)\n' % (
                    self.target_name, self.env, self.scons_target_type,
                    self.full_name, objs_name, deps, self.dep_paths)
        else:
            rule = '%s = %s.%s(\"%s\", %s, LIBS=%s)\n' % (
                    self.target_name, self.env, self.scons_target_type,
                    self.full_name, objs_name, deps)
        self.AddRule(rule)

    def ParseAndAddTarget(self):
        self.AddObjs()
        self.ParseDeps()
        self.ParseDepHeader()
        self.ParseDepsRecursive()
        self.AddToTargetPool()

    def AddObjs(self):
        self.srcs_with_path = []
        for src in self.srcs:
            src_with_path = os.path.join(self.current_dir, src)
            self.srcs_with_path.append(src_with_path)
        self.objs = []
        self.obj_target_names = []
        for src_with_path in self.srcs_with_path:
            src = os.path.basename(src_with_path)
            obj_target_name = os.path.join(self.build_root_dir, self.relative_dir,
                    self.name + '.objs' + self.dl_suffix, src + '.o')
            self.obj_target_names.append(obj_target_name)
            obj = self.relative_dir + "_" + src + '_obj' + self.dl_suffix
            obj = self.RemoveSpecialChar(obj)
            self.objs.append(obj)

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
                if self.export_dynamic == 1:
                    self.dep_library_list.append(dep[1:])
                else:
                    self.dep_library_list.append(dep_library)
                target_key = os.path.join(self.current_dir, dep[1:])
                self.recursive_library_list.append(target_key)
                dep_path = os.path.join(self.build_root_dir, self.relative_dir)
                self.dep_paths.append(dep_path)
            elif dep[0:2] == '//':
                fields = dep[2:].split(':')
                if len(fields) != 2:
                    ErrorExit('The format of deps(%s) is invalid.' % (dep))
                library_path = fields[0]
                library_path = library_path.rstrip('/')
                library_name = fields[1]
                dep_library = self.RemoveSpecialChar(library_path + ':' + library_name)
                if self.export_dynamic == 1:
                    self.dep_library_list.append(library_name)
                else:
                    self.dep_library_list.append(dep_library)
                target_key = os.path.join(self.flame_root_dir, library_path, library_name)
                self.recursive_library_list.append(target_key)
                dep_path = os.path.join(self.build_root_dir, library_path)
                self.dep_paths.append(dep_path)
            else:
                ErrorExit('The format of deps(%s) is invalid.' % (dep))

    def ParseDepsRecursive(self):
        targets = target_pool.GetTargetPool()
        for target_key in self.recursive_library_list:
            if target_key in targets:
                continue
            library_path = os.path.dirname(target_key)
            library_name = os.path.basename(target_key)
            current_dir = GetCurrentDir()
            os.chdir(library_path)
            build_name = GetBuildName()
            if not os.path.isfile(build_name):
                ErrorExit('BUILD not find.')
            build_library_pool = target_pool.GetBuildLibraryPool()
            if (build_name, library_name) in build_library_pool:
                os.chdir(current_dir)
                continue
            build_library_pool[(build_name, library_name)] = 1
            # Only build |library_name|
            argv_backup = copy.copy(sys.argv)
            sys.argv = [library_name]
            if self.export_dynamic == 1:
                if library_name[-6:] == '_share':
                    library_name = library_name[:len(library_name)-6]
                    sys.argv = [library_name]
            execfile(build_name)
            # Clear build targets, restore old argv.
            sys.argv = argv_backup
            os.chdir(current_dir)

class CcLibraryTarget(CcTarget):
    def __init__(self, name, target_type, srcs, deps, scons_target_type,
                incs, export_dynamic, export_static):
        CcTarget.__init__(self, name, target_type, srcs, deps, scons_target_type,
                incs, export_dynamic, export_static)

    def WriteRule(self):
        CcTarget.WriteRule(self)
        if self.export_dynamic == 1 or self.export_static == 1:
            release_dir = os.path.join(self.release_prefix, 'lib')
            rule = '%s.Alias(\'install\', %s.Install(\'%s\', %s))\n' % (
                    self.env, self.env, release_dir, self.target_name)
            self.AddRuleForInstall(rule)

class CcBinaryTarget(CcTarget):
    def __init__(self, name, target_type, srcs, deps, scons_target_type,
                incs, export_dynamic, export_static):
        CcTarget.__init__(self, name, target_type, srcs, deps, scons_target_type,
                incs, export_dynamic, export_static)

    def WriteRule(self):
        CcTarget.WriteRule(self)
        self.binary_name = self.full_name
        release_dir = os.path.join(self.release_prefix, 'bin')
        rule = '%s.Alias(\'install\', %s.Install(\'%s\', %s))\n' % (self.env, self.env, release_dir, self.target_name)
        self.AddRuleForInstall(rule)

class CcTestTarget(CcTarget):
    def __init__(self, name, target_type, srcs, deps, scons_target_type,
                incs, export_dynamic, export_static):
        CcTarget.__init__(self, name, target_type, srcs, deps, scons_target_type,
                incs, export_dynamic, export_static)

    def WriteRule(self):
        CcTarget.WriteRule(self)
        self.test_case = self.full_name

class PrebuiltLibraryTarget(Target):
    def __init__(self, name, target_type, srcs, deps, scons_target_type,
                incs, export_dynamic, export_static):
        Target.__init__(self, name, target_type, srcs, deps, scons_target_type,
                incs, export_dynamic, export_static)
        self.prebuilt = 1
        build_target_list = filter(lambda x:(len(x) > 0 and x[0] != '-'), sys.argv)
        if len(build_target_list) == 0 or name in build_target_list:
            self.AddPrebuiltTarget()

    def WriteRule(self):
        Target.WriteRule(self)
        prebuilt_suffix = 'a'
        if self.export_dynamic == 1:
            prebuilt_suffix = 'so'
        prebuilt_name = 'lib%s.%s' % (self.name, prebuilt_suffix)
        prebuilt_target = os.path.join(self.build_root_dir, self.relative_dir, prebuilt_name)
        prebuilt_source = os.path.join(self.flame_root_dir, self.relative_dir, 'lib', prebuilt_name)
        rule = 'Command(\"%s\", \"%s\", Copy(\"$TARGET\", \"$SOURCE\"))\n' % (prebuilt_target, prebuilt_source)
        self.AddRule(rule)
        rule = '%s = env.File(\"%s\")\n' % (self.relative_name, prebuilt_target)
        self.AddRule(rule)

    def AddPrebuiltTarget(self):
        self.ParseDepHeader()
        self.AddToTargetPool()


class ExtraExportTarget(Target):
    def __init__(self, headers, confs, files):
        Target.__init__(self, 'extra_export', 'extra_export', [], [], '', [], 0, 0)
        self.export_headers = headers
        self.export_confs = confs
        self.export_files = files
        self.AddToTargetPool()

    def WriteRule(self):
        release_include_dir = os.path.join(self.release_prefix, 'include')
        release_conf_dir = os.path.join(self.release_prefix, 'conf')
        release_data_dir = os.path.join(self.release_prefix, 'data')
        self.WriteRuleForExtra(self.export_headers, release_include_dir)
        self.WriteRuleForExtra(self.export_confs, release_conf_dir)
        self.WriteRuleForExtra(self.export_files, release_data_dir)

    def WriteRuleForExtra(self, extra_files, release_dir):
        for extra_file in extra_files:
            extra_file_list = VarToList(extra_file)
            if extra_file_list[0][0:2] == '//':
                extra_file_name = os.path.join(self.flame_root_dir, extra_file_list[0][2:])
            else:
                extra_file_name = os.path.join(self.current_dir, extra_file_list[0])
            source_name = os.path.basename(extra_file_list[0])
            if len(extra_file_list) == 2:
                release_name = os.path.join(release_dir, extra_file_list[1])
            else:
                release_name = os.path.join(release_dir, source_name)
            rule = 'env.Alias(\'install\', env.InstallAs(\'%s\', \'%s\'))\n' % (release_name, extra_file_name)
            self.AddRuleForInstall(rule)

# TODO: warning
def cc_library(name, srcs=[], deps=[], prebuilt=0, incs=[], warning='yes', export_dynamic=0, export_static=0):
    if prebuilt == 1:
        export_dynamic = 1
        target = PrebuiltLibraryTarget(name, 'cc_library', srcs, deps, 'SharedLibrary', incs, 1, 0)
        target = PrebuiltLibraryTarget(name, 'cc_library', srcs, deps, 'Library', incs, 0, export_static)
        return
    if export_dynamic == 1:
        target = CcLibraryTarget(name, 'cc_library', srcs, deps, 'SharedLibrary', incs, 1, 0)
    target = CcLibraryTarget(name, 'cc_library', srcs, deps, 'Library', incs, 0, export_static)

def cc_binary(name, srcs, deps=[], incs=[], warning='yes'):
    target = CcBinaryTarget(name, 'cc_binary', srcs, deps, 'Program', incs, 0, 0)

def cc_test(name, srcs, deps=[], incs=[], warning='yes'):
    deps = VarToList(deps)
    deps += ['//thirdparty/gtest:gtest', '//thirdparty/gtest:gtest_main']
    target = CcTestTarget(name, 'cc_test', srcs, deps, 'Program', incs, 0, 0)

def extra_export(headers=[], confs=[], files=[]):
    target = ExtraExportTarget(headers, confs, files)

