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
    '''Base class of Target.
    '''
    def __init__(self, name, target_type, srcs, deps, scons_target_type,
            incs, defs, extra_include_paths, extra_lib_paths):
        self.name = name
        self.type = target_type
        self.incs = VarToList(incs)
        self.srcs = VarToList(srcs)
        self.SrcReplaceRegex()
        self.deps = VarToList(deps)
        self.defs = VarToList(defs)
        self.scons_target_type = scons_target_type

        self.current_dir = GetCurrentDir()
        self.build_root_dir = GetBuildRootDir()
        self.relative_dir = GetRelativeDir(self.current_dir, GetFlameRootDir())
        self.relative_build_dir = os.path.join(GetBuildDirName(), self.relative_dir)
        self.flame_root_dir = GetFlameRootDir()

        self.key = os.path.join(self.current_dir, self.name)
        self.relative_name = os.path.join(self.relative_dir, self.name)
        self.relative_name = RemoveSpecialChar(self.relative_name)
        self.target_name = self.relative_name
        self.full_name = os.path.join(self.build_root_dir,
            self.relative_dir, self.name)
        self.dl_suffix = ''

        self.system_library_list = []
        self.prebuilt_library_list = []
        self.prebuilt_static_library_list = []
        self.dep_library_list = []
        self.link_all_symbols_lib_list = []
        self.dep_paths = []
        self.dep_header_list = []
        self.recursive_library_list = []  # Save dep library's target keys.
        self.recursive_library_list_sort = []
        # Save dep library's target keys and dep sub target keys.
        self.recursive_library_list_with_sub = []
        self.scons_rules = []
        self.scons_rules_for_install = []
        self.objs = []
        self.sub_objs = []
        self.data = {}

        self.extra_include_paths = VarToList(extra_include_paths)
        self.extra_lib_paths = VarToList(extra_lib_paths)

        self.release_prefix = ParseReleasePrefix(sys.argv)

    def WriteRule(self):
        self.env = self.relative_name + self.dl_suffix + '_env'
        self.env = RemoveSpecialChar(self.env)
        rule = '%s = env.Clone()' % (self.env)
        self.AddRule(rule)
        macros = []
        # Warning.
        if self.data.get('warning') == 'no':
            macros += ['-w']
        # Macro.
        if self.defs:
            macros += [('-D' + macro) for macro in self.defs]
        if macros:
            rule = '%s.Append(CPPFLAGS=%s)' % (self.env, macros)
            self.AddRule(rule)
        # Include path.
        if self.dep_header_list:
            rule = '%s.Append(CPPPATH=%s)' % (self.env, self.dep_header_list)
            self.AddRule(rule)
        # Extra include path.
        if self.extra_include_paths:
            rule = '%s.Append(CPPPATH=%s)' % (self.env, self.extra_include_paths)
            self.AddRule(rule)

        # Extra lib path.
        if self.extra_lib_paths:
            rule = '%s.Append(LIBPATH=%s)' % (self.env, self.extra_lib_paths)
            self.AddRule(rule)

        # Link all symbols.
        if self.link_all_symbols_lib_list:
            link_all_symbols_str = ','.join(self.link_all_symbols_lib_list)
            whole_archive = "-Wl,--whole-archive"
            no_whole_archive = "-Wl,--no-whole-archive"
            if Platform() == "darwin":
                whole_archive = "-Wl,-all_load"
                no_whole_archive = "-Wl,-noall_load"
            rule = '%s.Append(LINKFLAGS=["%s", %s , "%s"])' % (
                    self.env, whole_archive, link_all_symbols_str, no_whole_archive)
            self.AddRule(rule)

    def FormatDepLibrary(self):
        res = '['
        if self.data.get('export_dynamic') == 1:
            for library in self.prebuilt_library_list:
                library = '\"%s\"' % library
                res += library + ','
        elif self.data.get('export_static') == 1:
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
        self.scons_rules.append(rule + '\n')

    def AddRuleForInstall(self, rule):
        self.scons_rules_for_install.append(rule + '\n')

    def AddToTargetPool(self):
        targets = target_pool.GetTargetPool()
        if self.key not in targets:
            targets[self.key] = self

    def ParseDepHeader(self):
        if self.incs:
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

    def RegisterTarget(self):
        # build targets are send by sys.argv
        build_target_list = \
                filter(lambda x:(len(x) > 0 and x[0] != '-'), sys.argv)
        if len(build_target_list) == 0 or self.name in build_target_list:
            self.ParseAndAddTarget()

    def ParseAndAddTarget(self):
        pass

class CcTarget(Target):
    def __init__(self, name, target_type, srcs, deps, scons_target_type,
            incs, defs, extra_include_paths, extra_lib_paths):
        Target.__init__(self, name, target_type, srcs, deps, scons_target_type,
                incs, defs, extra_include_paths, extra_lib_paths)

    def WriteRule(self):
        Target.WriteRule(self)
        for i in range(len(self.objs)):
            obj = self.objs[i]
            obj_target_name = self.obj_target_names[i]
            src_with_path = self.srcs_with_path[i]
            rule = '%s = %s.SharedObject(target = \"%s\", source = \"%s\")' % (
                    obj, self.env, obj_target_name, src_with_path)
            self.AddRule(rule)

        objs_name = self.relative_dir + '_' + self.name + '_objs' + self.dl_suffix
        objs_name = RemoveSpecialChar(objs_name)
        if self.data.get('export_dynamic') == 1 or self.data.get('export_static') == 1:
            rule = '%s = [%s]' % (objs_name, ','.join(self.objs + self.sub_objs))
        else:
            rule = '%s = [%s]' % (objs_name, ','.join(self.objs))
        self.AddRule(rule)
        deps = self.FormatDepLibrary()
        if self.data.get('export_dynamic') == 1:
            # Dynamic dependence library can not link with absolutive path.
            rule = '%s = %s.%s(\"%s\", %s, LIBS=%s, LIBPATH=%s)' % (
                    self.target_name, self.env, self.scons_target_type,
                    self.full_name, objs_name, deps, self.dep_paths)
        else:
            rule = '%s = %s.%s(\"%s\", %s, LIBS=%s)' % (
                    self.target_name, self.env, self.scons_target_type,
                    self.full_name, objs_name, deps)
        self.AddRule(rule)

        # Depend relation.
        if self.link_all_symbols_lib_list:
            if self.type == 'cc_binary' or \
                    self.data.get('export_dynamic') == 1 or \
                    self.data.get('export_static') == 1:
                link_all_symbols_str = '[' + ','.join(self.link_all_symbols_lib_list) + ']'
                rule = '%s.Depends(%s, %s)' % (self.env, self.target_name, link_all_symbols_str)
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
            obj = RemoveSpecialChar(obj)
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
                dep_library = RemoveSpecialChar(dep_library)
                if self.data.get('export_dynamic') == 1:
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
                dep_library = RemoveSpecialChar(library_path + ':' + library_name)
                if self.data.get('export_dynamic') == 1:
                    self.dep_library_list.append(library_name)
                else:
                    self.dep_library_list.append(dep_library)

                target_key = os.path.join(self.flame_root_dir,
                        library_path, library_name)
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
                relative_dir = GetRelativeDir(library_path, GetFlameRootDir())
                ErrorExit('//%s/BUILD not find. required by //%s:%s.' % (
                        relative_dir, self.relative_dir, self.name))
            build_library_pool = target_pool.GetBuildLibraryPool()
            if (build_name, library_name) in build_library_pool:
                os.chdir(current_dir)
                continue
            build_library_pool[(build_name, library_name)] = 1
            # Only build |library_name|
            argv_backup = copy.copy(sys.argv)
            prefix_list = filter(lambda x:('-prefix=' in x), sys.argv)
            sys.argv = [library_name]
            if self.data.get('export_dynamic') == 1:
                if library_name[-6:] == '_share':
                    library_name = library_name[:len(library_name)-6]
                    sys.argv = [library_name]
            sys.argv += prefix_list
            execfile(build_name)
            # Clear build targets, restore old argv.
            sys.argv = argv_backup
            os.chdir(current_dir)

class CcLibraryTarget(CcTarget):
    def __init__(self, name, target_type, srcs, deps, scons_target_type,
            incs, defs, extra_include_paths, extra_lib_paths,
            export_dynamic, export_static, warning,
            link_all_symbols, allow_export):
        CcTarget.__init__(self, name, target_type, srcs, deps,
                scons_target_type, incs, defs, extra_include_paths,
                extra_lib_paths)
        self.data['export_dynamic'] = export_dynamic
        self.data['export_static'] = export_static
        self.data['warning'] = warning
        self.data['link_all_symbols'] = link_all_symbols
        self.data['allow_export'] = allow_export
        if self.data.get('export_dynamic') == 1:
            self.dl_suffix = '_share'
            self.key += self.dl_suffix
            self.target_name += self.dl_suffix

    def WriteRule(self):
        CcTarget.WriteRule(self)
        if self.data.get('export_dynamic') == 1 or self.data.get('export_static') == 1:
            release_dir = os.path.join(self.release_prefix, 'lib')
            rule = '%s.Alias(\'install\', %s.Install(\'%s\', %s))' % (
                    self.env, self.env, release_dir, self.target_name)
            self.AddRuleForInstall(rule)

class CcBinaryTarget(CcTarget):
    def __init__(self, name, target_type, srcs, deps, scons_target_type, defs,
            extra_include_paths, extra_lib_paths):
        CcTarget.__init__(self, name, target_type, srcs, deps, scons_target_type,
                [], defs, extra_include_paths, extra_lib_paths)

    def WriteRule(self):
        CcTarget.WriteRule(self)
        self.binary_name = self.full_name
        release_dir = os.path.join(self.release_prefix, 'bin')
        rule = '%s.Alias(\'install\', %s.Install(\'%s\', %s))' % (
                self.env, self.env, release_dir, self.target_name)
        self.AddRuleForInstall(rule)

class CcTestTarget(CcTarget):
    def __init__(self, name, target_type, srcs, deps, scons_target_type,
                defs, testdata):
        CcTarget.__init__(self, name, target_type, srcs, deps,
                scons_target_type, [], defs, [], [])
        self.testdata = VarToList(testdata)
        self.testcase_rundir = os.path.join(self.build_root_dir,
                self.relative_dir, self.name + '.runfiles')
        self.testdata_copy_pair = []

    def WriteRule(self):
        CcTarget.WriteRule(self)
        self.test_case = self.full_name
        self.WriteRuleForTestData()

    def WriteRuleForTestData(self):
        for test_file in self.testdata:
            test_file_list = VarToList(test_file)
            if test_file_list[0][0:2] == '//':
                source_file_name = os.path.join(
                        self.flame_root_dir, test_file_list[0][2:])
                source_relative_name = test_file_list[0][2:]
            else:
                source_file_name = os.path.join(
                        self.current_dir, test_file_list[0])
                source_relative_name = test_file_list[0]
            if len(test_file_list) == 2:
                link_file_name = os.path.join(
                        self.testcase_rundir, test_file_list[1])
            else:
                link_file_name = os.path.join(
                        self.testcase_rundir, source_relative_name)
            self.testdata_copy_pair.append((source_file_name, link_file_name))

class CcPrebuiltLibraryTarget(CcTarget):
    def __init__(self, name, target_type, srcs, deps, scons_target_type,
                incs, defs, export_dynamic, export_static, warning):
        CcTarget.__init__(self, name, target_type, srcs, deps, scons_target_type,
                incs, defs, [], [])
        self.data['export_dynamic'] = export_dynamic
        self.data['export_static'] = export_static
        self.data['warning'] = warning
        self.data['prebuilt'] = 1
        if self.data.get('export_dynamic') == 1:
            self.dl_suffix = '_share'
            self.key += self.dl_suffix
            self.target_name += self.dl_suffix

    def WriteRule(self):
        # Do not need to call CcTarget.WriteRule()
        Target.WriteRule(self)
        prebuilt_suffix = 'a'
        if self.data.get('export_dynamic') == 1:
            prebuilt_suffix = 'so'
        prebuilt_name = 'lib%s.%s' % (self.name, prebuilt_suffix)
        prebuilt_target = os.path.join(self.build_root_dir, self.relative_dir, prebuilt_name)
        prebuilt_source = os.path.join(self.flame_root_dir, self.relative_dir, 'lib', prebuilt_name)
        rule = 'Command(\"%s\", \"%s\", Copy(\"$TARGET\", \"$SOURCE\"))' % (prebuilt_target, prebuilt_source)
        self.AddRule(rule)
        rule = '%s = env.File(\"%s\")' % (self.target_name, prebuilt_target)
        self.AddRule(rule)

    def ParseAndAddTarget(self):
        self.ParseDepHeader()
        self.ParseDeps()
        self.ParseDepHeader()
        self.ParseDepsRecursive()
        self.AddToTargetPool()

class ExtraExportTarget(Target):
    def __init__(self, headers, confs, files):
        Target.__init__(self, 'extra_export', 'extra_export',
                [], [], '', [], [], [], [])
        self.export_headers = VarToList(headers)
        self.export_confs = VarToList(confs)
        self.export_files = VarToList(files)

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
            rule = 'env.Alias(\'install\', env.InstallAs(\'%s\', \'%s\'))' % (release_name, extra_file_name)
            self.AddRuleForInstall(rule)

    def ParseAndAddTarget(self):
        self.AddToTargetPool()

class ProtoLibraryTarget(CcTarget):
    def __init__(self, name, target_type, srcs, deps, scons_target_type):
        CcTarget.__init__(self, name, target_type, srcs, deps, scons_target_type,
                [], [], [], [])

    def WriteRule(self):
        Target.WriteRule(self)
        for i in range(len(self.objs)):
            obj = self.objs[i]
            obj_target_name = self.obj_target_names[i]
            src_with_path = self.srcs_with_path[i]
            proto_with_path = self.protos_with_path[i]
            inc_with_path = self.incs_with_path[i]
            proto_list = [inc_with_path, src_with_path]
            rule = '%s.%s(%s, \"%s\")' % (
                    self.env, self.scons_target_type, proto_list, proto_with_path)
            self.AddRule(rule)
            rule = '%s = %s.SharedObject(target = \"%s\", source = \"%s\")' % (
                    obj, self.env, obj_target_name, src_with_path)
            self.AddRule(rule)

        objs_name = self.relative_dir + '_' + self.name + '_objs'
        objs_name = RemoveSpecialChar(objs_name)
        rule = '%s = [%s]' % (objs_name, ','.join(self.objs))
        self.AddRule(rule)
        deps = self.FormatDepLibrary()
        rule = '%s = %s.Library(\"%s\", %s, LIBS=%s)' % (
                self.target_name, self.env, self.full_name, objs_name, deps)
        self.AddRule(rule)

    def AddObjs(self):
        self.srcs_with_path = []
        self.incs_with_path = []
        self.protos_with_path = []
        new_srcs = []
        for src in self.srcs:
            proto_prefix = src[:-5]
            src_with_path = os.path.join(self.relative_build_dir, proto_prefix + 'pb.cc')
            inc_with_path = os.path.join(self.relative_build_dir, proto_prefix + 'pb.h')
            proto_with_path = os.path.join(self.relative_dir, src)
            self.srcs_with_path.append(src_with_path)
            self.incs_with_path.append(inc_with_path)
            self.protos_with_path.append(proto_with_path)
            new_srcs.append(os.path.basename(src_with_path))
        self.srcs = new_srcs
        self.objs = []
        self.obj_target_names = []
        for src_with_path in self.srcs_with_path:
            src = os.path.basename(src_with_path)
            obj_target_name = os.path.join(self.build_root_dir, self.relative_dir,
                    self.name + '.objs', src + '.o')
            self.obj_target_names.append(obj_target_name)
            obj = self.relative_dir + "_" + src + '_obj'
            obj = RemoveSpecialChar(obj)
            self.objs.append(obj)

def cc_library(name, srcs=[], deps=[], prebuilt=0, incs=[], defs=[],
        extra_include_paths=[], extra_lib_paths=[], warning='yes',
        export_dynamic=0, export_static=0, link_all_symbols=0, allow_export=1):
    if prebuilt == 1:
        target = CcPrebuiltLibraryTarget(name, 'cc_library', srcs, deps, 'SharedLibrary', incs, defs, 1, 0, warning)
        target.RegisterTarget()
        target = CcPrebuiltLibraryTarget(name, 'cc_library', srcs, deps, 'Library', incs, defs, 0, export_static, warning)
        target.RegisterTarget()
        return
    if export_dynamic == 1:
        target = CcLibraryTarget(name, 'cc_library', srcs, deps,
                'SharedLibrary', incs, defs, extra_include_paths,
                extra_lib_paths, 1, 0, warning, 0, allow_export)
        target.RegisterTarget()
    target = CcLibraryTarget(name, 'cc_library', srcs, deps, 'Library',
            incs, defs, extra_include_paths, extra_lib_paths, 0,
            export_static, warning, link_all_symbols, allow_export)
    target.RegisterTarget()

def cc_binary(name, srcs, deps=[], defs=[], extra_include_paths=[],
        extra_lib_paths=[]):
    target = CcBinaryTarget(name, 'cc_binary', srcs, deps, 'Program', defs,
            extra_include_paths, extra_lib_paths)
    target.RegisterTarget()

def cc_test(name, srcs, deps=[], defs=[], testdata=[]):
    deps = VarToList(deps)
    deps += ['//thirdparty/gtest:gtest', '//thirdparty/gtest:gtest_main']
    target = CcTestTarget(name, 'cc_test', srcs, deps, 'Program', defs, testdata)
    target.RegisterTarget()

def extra_export(headers=[], confs=[], files=[]):
    target = ExtraExportTarget(headers, confs, files)
    target.RegisterTarget()

def proto_library(name, srcs=[], deps=[]):
    deps = VarToList(deps)
    deps += ['//thirdparty/protobuf:protobuf',]
    target = ProtoLibraryTarget(name, 'proto_library', srcs, deps, 'Proto')
    target.RegisterTarget()

