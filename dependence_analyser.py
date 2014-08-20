# Copyright (c) 2014, The Flame Authors.
# All rights reserved.
# Author: Chao Xiong <fancysimon@gmail.com>

'''
Dependence analyser.
'''

import os
import copy
from util import *

_sorted_target_node_list = []

class TargetNode:
    def __init__(self, key, recursive_library_list):
        self.key = key
        self.recursive_library_list = copy.copy(recursive_library_list)

def ToString(target_node_list):
    ans = ''
    for target_node in target_node_list:
        ans += '[key:' + target_node.key + ' lib:' + ','.join(target_node.recursive_library_list) + '] '
    return ans

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
            target_key = target_node_list[0].key
            not_find_library = target_node_list[0].recursive_library_list[0]
            flame_dir = GetFlameRootDir()
            relative_dir = GetRelativeDir(target_key, flame_dir)
            target_name = '//%s:%s' % (relative_dir, os.path.basename(target_key))
            relative_dir = GetRelativeDir(not_find_library, flame_dir)
            not_find_library_name = '//%s:%s' % (relative_dir, os.path.basename(not_find_library))
            ErrorExit('%s not find. required by %s' % (not_find_library_name, target_name))
        for node in zero_degree_list:
            for node2 in target_node_list:
                if node.key in node2.recursive_library_list:
                    node2.recursive_library_list.remove(node.key)
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

