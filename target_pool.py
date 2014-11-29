# Copyright (c) 2014, The Flame Authors.
# All rights reserved.
# Author: Chao Xiong <fancysimon@gmail.com>

'''
Target pool.
'''

import os
import copy
from util import *
from dependence_analyser import *

_target_pool = {}
_build_library_pool = {}

def WriteRuleForAllTargets():
    global _target_pool
    GenerateRecursiveForSort()
    sorted_target_node_list = GetSortedTargetNodes(_target_pool)
    ComplementSubDeps(sorted_target_node_list)
    SortDepLibraryForAllTargets()
    GenerateLinkAllSymbolsList()
    for node in sorted_target_node_list:
        target = _target_pool[node.key]
        target.WriteRule()

def GetAllTargets():
    global _target_pool
    sorted_target_node_list = GetSortedTargetNodes(_target_pool)
    targets = []
    for node in sorted_target_node_list:
        target = _target_pool[node.key]
        targets.append(target)
    return targets

def ComplementSubDeps(sorted_target_node_list):
    global _target_pool
    for node in sorted_target_node_list:
        target = _target_pool[node.key]
        # First copy recursive_library_list to sub.
        target.recursive_library_list_with_sub = copy.copy(target.recursive_library_list)
        if target.type == 'extra_export':
            continue
        recursive_library_list_str = ''
        sub_recursive_library_list = []
        for key in target.recursive_library_list:
            sub_target = _target_pool[key]
            # Dependant sub library must be put after this library,
            # or there will be link error(undefined reference to).
            target.dep_library_list += sub_target.dep_library_list
            target.system_library_list += sub_target.system_library_list
            target.dep_paths += sub_target.dep_paths
            target.dep_header_list += sub_target.dep_header_list
            target.sub_objs += sub_target.sub_objs + sub_target.objs
            if sub_target.data.get('prebuilt') == 1:
                target.prebuilt_library_list.append(sub_target.name)
                target.prebuilt_static_library_list.append(sub_target.target_name)
            recursive_library_list_str += sub_target.name + ','
            sub_recursive_library_list += sub_target.recursive_library_list_with_sub
        target.recursive_library_list_with_sub = target.recursive_library_list_with_sub + sub_recursive_library_list
        target.recursive_library_list_with_sub = RemoveDuplicate(target.recursive_library_list_with_sub)
        target.dep_header_list = RemoveDuplicate(target.dep_header_list)
        target.dep_library_list = RemoveDuplicate(target.dep_library_list)
        target.system_library_list = RemoveDuplicate(target.system_library_list)
        target.dep_paths = RemoveDuplicate(target.dep_paths)
        target.sub_objs = RemoveDuplicate(target.sub_objs)
        target.prebuilt_library_list = RemoveDuplicate(target.prebuilt_library_list)
        target.prebuilt_static_library_list = RemoveDuplicate(target.prebuilt_static_library_list)

# Dynamic library only dependent prebuild and system library.
def GenerateRecursiveForSort():
    global _target_pool
    for target in _target_pool.values():
        target.recursive_library_list_for_sort = \
                copy.copy(target.recursive_library_list)

def GetTargetPool():
    global _target_pool
    return _target_pool

def GetBuildLibraryPool():
    global _build_library_pool
    return _build_library_pool

def SortDepLibraryForAllTargets():
    # There will be wrong if dep library list in disorder.
    global _target_pool
    sorted_target_node_list = GetSortedTargetNodes(_target_pool)
    dep_library_map = {}
    flame_root_dir = GetFlameRootDir()
    i = 0
    for node in sorted_target_node_list:
        relative_dir = GetRelativeDir(node.key, flame_root_dir)
        dep_library = RemoveSpecialChar(relative_dir)
        dep_library_map[dep_library] = i
        dep_library_for_share = os.path.basename(node.key)
        dep_library_map[dep_library_for_share] = i
        i += 1
    for target in _target_pool.values():
        target.dep_library_list.sort(key=lambda x:dep_library_map[x], reverse=True)
        target.prebuilt_library_list.sort(key=lambda x:dep_library_map[x], reverse=True)
        target.prebuilt_static_library_list.sort(key=lambda x:dep_library_map[x], reverse=True)

# Generate link all symbols by dep library list.
def GenerateLinkAllSymbolsList():
    global _target_pool
    flame_root_dir = GetFlameRootDir()
    for target_key in _target_pool:
        target = _target_pool[target_key]
        # Only binary and test need link all symbols.
        if target.type != 'cc_binary' and target.type != 'cc_test':
            continue

        link_all_symbols_list = []
        for sub_target_key in target.recursive_library_list_with_sub:
            relative_dir = GetRelativeDir(sub_target_key, flame_root_dir)
            dep_library = RemoveSpecialChar(relative_dir)
            sub_target = _target_pool[sub_target_key]
            if sub_target.data.get('link_all_symbols') == 1:
                link_all_symbols_list.append(dep_library)
        not_link_all_symbols_list = [i for i in target.dep_library_list if i not in link_all_symbols_list]
        target.dep_library_list = not_link_all_symbols_list
        target.link_all_symbols_lib_list = link_all_symbols_list

