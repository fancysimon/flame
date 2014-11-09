# Copyright (c) 2014, The Flame Authors.
# All rights reserved.
# Author: Chao Xiong <fancysimon@gmail.com>

'''
Dependence analyser.
'''

import copy
import os
import sys
from util import *

_sorted_target_node_list = []

class TargetNode:
    def __init__(self, key, recursive_library_list):
        self.key = key
        self.recursive_library_list = copy.copy(recursive_library_list)

def ToString(target_node_list):
    ans = ''
    for target_node in target_node_list:
        ans += '[\n    key:' + target_node.key + '\n    lib:' + ',\n    '.join(target_node.recursive_library_list) + '\n]\n'
    return ans

def OutputRequiredErrorAndExit(target_node_list):
    target_key = target_node_list[0].key
    target_key_dict = {}
    for target in target_node_list:
        target_key_dict[target.key] = 1
    target_required_list = []
    for target in target_node_list:
        for required_library in target.recursive_library_list:
            if required_library not in target_key_dict:
                target_required_list.append([target.key, required_library])
    for target_key, required_library in target_required_list:
        flame_dir = GetFlameRootDir()
        relative_dir = GetRelativeDir(target_key, flame_dir)
        target_name = '//%s:%s' % (os.path.dirname(relative_dir), os.path.basename(target_key))
        relative_dir = GetRelativeDir(required_library, flame_dir)
        required_library_name = '//%s:%s' % (os.path.dirname(relative_dir), os.path.basename(required_library))
        Error('%s not find. required by %s' % (required_library_name, target_name))
    sys.exit(1)

def TopologySort(target_pool):
    target_node_list = []
    for key, target in target_pool.items():
        node = TargetNode(key, target.recursive_library_list_for_sort)
        target_node_list.append(node)
    result_list = []
    while True:
        if len(target_node_list) == 0:
            break
        zero_degree_list = filter(lambda x:len(x.recursive_library_list)==0, target_node_list)
        target_node_list = filter(lambda x:len(x.recursive_library_list)>0, target_node_list)

        if len(zero_degree_list) == 0:
            if CheckCircle(target_node_list):
                ErrorExit('Library dependency has circle!')
            OutputRequiredErrorAndExit(target_node_list)
        for node in zero_degree_list:
            for node2 in target_node_list:
                if node.key in node2.recursive_library_list:
                    node2.recursive_library_list = filter(lambda x:x!=node.key, node2.recursive_library_list)
        result_list += zero_degree_list

    return result_list

def GetSortedTargetNodes(target_pool):
    global _sorted_target_node_list
    if len(_sorted_target_node_list) > 0:
        return _sorted_target_node_list
    _sorted_target_node_list = TopologySort(target_pool)
    return _sorted_target_node_list

def CheckCircle(target_node_list):
    node_dict = {}
    #print ToString(target_node_list)
    for target_node in target_node_list:
        for library in target_node.recursive_library_list:
            key = (target_node.key, library)
            if key in node_dict:
                return True
            node_dict[key] = 1
            key = (library, target_node.key)
            if key in node_dict:
                return True
            node_dict[key] = 1
    return False

