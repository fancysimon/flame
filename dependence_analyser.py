# Copyright (c) 2014, The Flame Authors.
# All rights reserved.
# Author: Chao Xiong <fancysimon@gmail.com>

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
        #print 'zero_degree_list:', ToString(zero_degree_list)
        #print 'target_node_list:', ToString(target_node_list)
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

