# Copyright 2021 The SPIRV-Control Flow Project Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http:#www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from __future__ import annotations

import sys
import random
import xml.etree.ElementTree as elementTree
import argparse
from collections import defaultdict, deque

from random import Random
from typing import Deque, DefaultDict, Dict, List, Set


MAX_PATH_LENGTH = 900 # Python has a limit on recursion depth of around 1000


class NoTerminalNodesInCFGError(Exception):

    def __init__(self, *args):
        super().__init__("Fleshing requires the CFG to have at least one terminal node.")


class AllTerminalNodesUnreachableError(Exception):

    def __init__(self, *args):
        super().__init__("Fleshing requires a CFG to have at least one terminal node that can be reached from the entry point.")


class TerminalNodesUnreachableFromCurrentNodeError(Exception):

    def __init__(self, node, terminal_nodes):
        super().__init__(f"No terminal node could be found starting at node {node}. The terminal nodes are:\n {terminal_nodes}") 


def get_field_from_instance(instance, label):
    for child in instance:
        if child.tag == 'field' and child.attrib['label'] == label:
            return child
    assert False


def get_sig_from_instance(instance, label):
    for child in instance:
        if child.tag == 'sig' and (child.attrib['label'].endswith('/' + label) or child.attrib['label'] == label):
            return child
    assert False


def get_jump_relation(instance) -> Dict[str, List[str]]:
    node_to_int_to_node: Dict[str, Dict[int, str]] = {}
    for child in get_field_from_instance(instance, 'branch'):
        if child.tag != 'tuple':
            continue
        assert len(child) == 3
        assert child[0].tag == 'atom'
        predecessor: str = child[0].attrib['label']
        if predecessor not in node_to_int_to_node:
            node_to_int_to_node[predecessor] = {}
        value: Dict[int, str] = node_to_int_to_node[predecessor]
        assert child[1].tag == 'atom'
        index: int = int(child[1].attrib['label'])
        assert index not in value
        assert child[2].tag == 'atom'
        value[index] = child[2].attrib['label']
    result: Dict[str, List[str]] = {}
    for key in node_to_int_to_node:
        seq: List[str] = []
        for index in range(0, len(node_to_int_to_node[key])):
            seq.append(node_to_int_to_node[key][index])
        result[key] = seq
    return result


def get_merge_relation(instance) -> Dict[str, str]:
    result: Dict[str, str] = {}
    for child in get_field_from_instance(instance, 'merge'):
        if child.tag != 'tuple':
            continue
        result[child[0].attrib['label']] = child[1].attrib['label']
    return result


def get_continue_relation(instance) -> Dict[str, str]:
    result: Dict[str, str] = {}
    for child in get_field_from_instance(instance, 'continue'):
        if child.tag != 'tuple':
            continue
        result[child[0].attrib['label']] = child[1].attrib['label']
    return result


def get_entry_block(instance) -> str:
    for child in get_sig_from_instance(instance, 'EntryBlock'):
        if child.tag == 'atom':
            return child.attrib['label']
    assert False


def get_regular_blocks(instance) -> Set[str]:
    result: Set[str] = set()
    for child in get_sig_from_instance(instance, 'Block'):
        result.add(child.attrib['label'])
    return result


def get_loop_header_blocks(instance) -> Set[str]:
    result: Set[str] = set()
    for child in get_sig_from_instance(instance, 'LoopHeader'):
        result.add(child.attrib['label'])
    return result


def get_selection_header_blocks(instance) -> Set[str]:
    result: Set[str] = set()
    for child in get_sig_from_instance(instance, 'SelectionHeader'):
        result.add(child.attrib['label'])
    return result


def get_switch_blocks(instance) -> Set[str]:
    result: Set[str] = set()
    for child in get_sig_from_instance(instance, 'SwitchBlock'):
        if child.tag != 'atom':
            continue
        result.add(child.attrib['label'])
    return result


def get_all_blocks(instance) -> Set[str]:
    result: Set[str] = set()
    result.add(get_entry_block(instance))
    result.update(get_regular_blocks(instance), get_loop_header_blocks(instance)
                  , get_selection_header_blocks(instance), get_switch_blocks(instance))
    return result


def get_all_headers(instance) -> Set[str]:
    result: Set[str] = set()
    result.update(get_loop_header_blocks(instance)
                  , get_selection_header_blocks(instance), get_switch_blocks(instance))
    return result


def get_structured_jump_relation(instance) -> Dict[str, List[str]]:
    result: Dict[str, List[str]] = get_jump_relation(instance).copy()
    # First, remove duplicate successors
    for block in result:
        duplicate_free: List[str] = []
        for successor in result[block]:
            if block not in duplicate_free:
                duplicate_free.append(successor)
        result[block] = duplicate_free
    # Now add any extra edges arising from merge and continue relations
    for structured_relation in [get_merge_relation(instance), get_continue_relation(instance)]:
        for block in structured_relation:
            if block not in result:
                result[block] = [structured_relation[block]]
            elif structured_relation[block] not in result[block]:
                result[block].append(structured_relation[block])
    return result


def get_back_edges(instance) -> Dict[str, Set[str]]:
    def dfs_(back_edges: Dict[str, Set[str]], stack: List[str], visited: Set[str], block: str):
        assert block not in visited
        assert block not in stack
        visited.add(block)
        stack.append(block)
        structured_jump_relation = get_structured_jump_relation(instance)
        if block in structured_jump_relation:
            for successor in structured_jump_relation[block]:
                if successor in stack:
                    assert successor in visited
                    if block not in back_edges:
                        back_edges[block] = set()
                    back_edges[block].add(successor)
                elif successor not in visited:
                    dfs_(back_edges, stack, visited, successor)
        stack.pop()

    result: Dict[str, Set[str]] = {}
    dfs_(result, [], set(), get_entry_block(instance))
    return result


def find_all_paths(graph, start, end, backedges, path=[]):
    path = path + [start]
    if start == end:
        return [path]
    if start not in graph:
        return []
    paths = []
    adj = graph[start]
    adj = list(dict.fromkeys(adj)) # remove any duplicates
    if start in backedges:
        adj = list(set(adj) - backedges[start])
    for node in adj:
        if node not in path:
            newpaths = find_all_paths(graph, node, end, backedges, path)
            for newpath in newpaths:
                paths.append(newpath)
    return paths


def get_exit_blocks(graph) -> Set[str]:
    result: Set[str] = set()
    all_blocks = set(graph.keys()).union(set(x for lst in graph.values() for x in lst))
    for key in all_blocks:
        if graph.get(key) is None:
            result.add(key)
    return result


# Function to perform BFS traversal from a given source vertex in a graph to
# determine if a destination vertex is reachable from the source or not
def isReachable(graph, s, d):
    all_blocks = set(graph.keys()).union(set(x for lst in graph.values() for x in lst))
    # Mark all the vertices as not visited
    visited = {}
    for block in all_blocks:
        visited[block] = False

    # Create a queue for BFS
    queue = []

    # Mark the source node as visited and enqueue it
    queue.append(s)
    visited[s] = True

    while queue:

        # Dequeue a vertex from queue
        n = queue.pop(0)
        # If this adjacent node is the destination node,
        # then return true
        if n == d:
            return True

        if n not in graph:
            # n could be an exit block or a doomed block without
            # neighbours (I think), so it won't appear in the graph which
            # is built from the jump relation.
            continue

        #  Else, continue to do BFS
        for i in graph[n]:
            if visited[i] == False:
                queue.append(i)
                visited[i] = True
        # If BFS is complete without visited d
    return False


# A doomed block is a block that no terminal block is reachable from.
# This code is doing a reachability check from each src to every exit block rather
# than working backwards. As a potential performance improvement, we could work backwards and
# determine the union of the set of reachable nodes from each exit block, and then the doomed
# nodes are the complement of this and all nodes.
def get_doomed_blocks(graph):
    result: Set[str] = set()
    all_blocks = set(graph.keys()).union(set(x for lst in graph.values() for x in lst))
    exit_blocks = get_exit_blocks(graph)
    for src in all_blocks:
        if not any(isReachable(graph, src, dest) for dest in exit_blocks):
            result.add(src)
    return result


# Find a paths of the desired length by doing a random walk that is
# not allowed to visit a doomed or an exit block proceeding the last block
def random_paths_of_desired_length_without_passing_through_doomed_(graph, start, length, path, prng):
    path = path + [start]
    if len(path) == length:
        return [path]
    paths = []
    no_doomed = graph[start]
    no_doomed = list(dict.fromkeys(no_doomed)) # remove any duplicates
    for doomed in set(get_doomed_blocks(graph)).union(get_exit_blocks(graph)):
        if doomed in no_doomed:
            no_doomed.remove(doomed)
    prng.shuffle(no_doomed)
    for block in no_doomed:
            newpaths = random_paths_of_desired_length_without_passing_through_doomed(graph, block, length, path)
            for newpath in newpaths:
                paths.append(newpath)
    return paths


def get_non_doomed_graph(graph, doomed_nodes):
    non_doomed_graph = {}
    for node in graph:
        if node in doomed_nodes:
            continue
        non_doomed_graph[node] = []
        for neighbour in graph[node]:
            if neighbour in doomed_nodes:
                continue
            non_doomed_graph[node].append(neighbour)
    return non_doomed_graph


def recover_bfs_path(src, dst, parents):
    if src == dst:
        return [dst]
    
    path = []
    while parents[dst] is not None:
        path.append(dst)
        dst = parents[dst]
    path.append(src)
    return path[::-1]


def dijkstra(graph, initial):
    shortest_path = None
    for end in get_exit_blocks(graph):

        # shortest paths is a dict of nodes
        # whose value is a tuple of (previous node, weight)
        shortest_paths = {initial: (None, 0)}
        current_node = initial
        visited = set()

        while current_node != end:
            visited.add(current_node)

            if current_node not in graph:
                destinations = []
            else:
                destinations = graph[current_node]
            weight_to_current_node = 1

            for next_node in destinations:
                weight = 1 + weight_to_current_node
                if next_node not in shortest_paths:
                    shortest_paths[next_node] = (current_node, weight)
                else:
                    current_shortest_weight = shortest_paths[next_node][1]
                    if current_shortest_weight > weight:
                        shortest_paths[next_node] = (current_node, weight)

            next_destinations = {node: shortest_paths[node] for node in shortest_paths if node not in visited}
            if not next_destinations:
                break
            # next node is the destination with the lowest weight
            current_node = min(next_destinations, key=lambda k: next_destinations[k][1])

        if current_node != end:
            continue # No path found

        # Work back through destinations in shortest path
        path = []
        while current_node is not None:
            path.append(current_node)
            next_node = shortest_paths[current_node][0]
            current_node = next_node
        # Reverse path
        path = path[::-1]
        if shortest_path is None or len(path) < len(shortest_path):
            shortest_path = path
    return shortest_path


def random_path_quasi_bounded_length(graph, start, length, path, prng):
    path = path + [start]
    all_blocks = set(graph.keys()).union(set(x for lst in graph.values() for x in lst))
    if len(path) > length and start not in graph:
        return [path]
    paths = []
    if len(path) < length + len(all_blocks) and start in graph:
        adj = graph[start]
        adj = list(dict.fromkeys(adj)) # remove any duplicates
        prng.shuffle(adj)
        for node in adj:
            newpaths = random_path_quasi_bounded_length(graph, node, length, path, prng)
            for newpath in newpaths:
                paths.append(newpath)
    return paths


def random_path_max_length(graph, start, maxlength, path, prng):
    path = path + [start]
    if len(path) == maxlength:
        return [path]
    if start not in graph: # exit block
        return path
    adj = graph[start]
    adj = list(dict.fromkeys(adj)) # remove any duplicates
    node = prng.choice(adj)
    newpath = random_path_max_length(graph, node, maxlength, path)
    return newpath


def find_all_paths_without_passing_through(graph, start, end, through, backedges, path=[]):
    path = path + [start]
    if start == end:
        return [path]
    if start not in graph:
        return []
    paths = []
    no_through = graph[start]
    no_through = list(dict.fromkeys(no_through)) # remove any duplicates
    if through in no_through:
        no_through.remove(through)
    if start in backedges:
        no_through = list(set(no_through) - backedges[start])
    for node in no_through:
        if node not in path:
            newpaths = find_all_paths_without_passing_through(graph, node, end, through, backedges, path)
            for newpath in newpaths:
                paths.append(newpath)
    return paths


def dominatorsOf(instance, a):
    dominants = set()
    jump = get_jump_relation(instance)
    entry = get_entry_block(instance)
    backedges = get_back_edges(instance)
    for block in get_all_blocks(instance):
        if all(block in path for path in find_all_paths(jump, entry, a, backedges)):
        #if not any(block in path for block in get_all_blocks(instance) for path in find_all_paths_without_passing_through(jump, entry, a, block, backedges)):
            # and block in some path entr->a
            dominants.add(block)
    return dominants


def dominated_by(instance, a):
    dominated = set()
    jump = get_jump_relation(instance)
    entry = get_entry_block(instance)
    backedges = get_back_edges(instance)
    for block in get_all_blocks(instance):
        if all(a in path for path in find_all_paths(jump, entry, block, backedges)):
        #if not any(block in path for block in get_all_blocks(instance) for path in find_all_paths_without_passing_through(jump, entry, a, block, backedges)):
            # and block in some path entr->a
            dominated.add(block)
    return dominated


def immediate_outter(instance, inner, flow) -> str:
    # find the immediate outer of 'inner' from the 'list'
    new_outer = 'flow[0]'
    for outer in flow:
        dominated_by_inner = dominated_by(instance, inner)
        dominated_by_outer = dominated_by(instance, outer.split('_')[2])
        if dominated_by_inner.issubset(dominated_by_outer):
            new_outer = outer
            dominated_by_new_outer = dominated_by(instance, new_outer.split('_')[2])
            if dominated_by_outer.issubset(dominated_by_new_outer):
                new_outer = outer
    return new_outer


def is_merge(instance, block):
    merge_rel = get_merge_relation(instance).copy()
    return block in merge_rel.values()


def is_selection_branch(instance, block):
    jump = get_jump_relation(instance).copy()
    sel_headers = get_selection_header_blocks(instance).copy()
    for sel_header in sel_headers:
        for b in jump[sel_header]:
            if block == b and not is_merge(instance, block) :
                return True
    return False


def is_break_block(instance, block):
    jump = get_jump_relation(instance).copy()
    if block in jump and block not in get_all_headers(instance) and not is_selection_branch(instance, block):
        return any(is_merge(instance, m) for m in jump[block])
    return False

def is_loop_branch_block(instance, block):
    jump = get_jump_relation(instance).copy()
    loop_headers = get_loop_header_blocks(instance).copy()
    return any(block in jump[loop_header] for loop_header in loop_headers)


def parallel_edges(instance, a, b):
    jump = get_jump_relation(instance).copy()
    if a in jump:
        for block in jump[a]:
            if block == b  and jump[a].count(b) > 1:
                return True
    return False


def compute_reverse_graph(graph):
    reverse = defaultdict(set)
    for node in graph:
        for neighbour in graph[node]:
            reverse[neighbour].add(node)
    return reverse


class CFG:
    VOID_TYPE_ID: int = 1
    MAIN_FUNCTION_TYPE_ID: int = 2
    BOOL_TYPE_ID: int = 3
    UINT_TYPE_ID: int = 4
    TRUE_CONSTANT_ID: int = 5
    ZERO_CONSTANT_ID: int = 6
    MAIN_FUNCTION_ID: int = 7
    ENTRY_BLOCK_ID: int = 8

    def __init__(self,
                 jump_relation: Dict[str, List[str]],
                 merge_relation: Dict[str, str],
                 continue_relation: Dict[str, str],
                 entry_block: str,
                 regular_blocks: Set[str],
                 loop_header_blocks: Set[str],
                 selection_header_blocks: Set[str],
                 switch_blocks: Set[str]):
        self.jump_relation: Dict[str, List[str]] = jump_relation
        self.reverse_graph = compute_reverse_graph(jump_relation)
        self.non_doomed_graph: Dict[str, List[str]] = self.create_non_doomed_graph()
        self.exit_blocks = get_exit_blocks(self.jump_relation)
        self.merge_relation = merge_relation
        self.merge_to_loop_header = dict([(self.merge_relation[block], block) for block in loop_header_blocks])
        self.continue_relation = continue_relation
        self.entry_block = entry_block
        self.regular_blocks = regular_blocks
        self.loop_header_blocks = loop_header_blocks
        self.selection_header_blocks = selection_header_blocks
        self.switch_blocks = switch_blocks
        self.all_blocks = {*self.regular_blocks, *self.loop_header_blocks, *self.selection_header_blocks}
        self.label_to_id: Dict[str, str] = {}
        self.next_id = self.ENTRY_BLOCK_ID
        assert len(self.loop_header_blocks.intersection(self.selection_header_blocks)) == 0
        assert len(self.loop_header_blocks.intersection(self.switch_blocks)) == 0
        assert self.switch_blocks.issubset(self.selection_header_blocks)
        self.structured_jump_relation: Dict[str, List[str]] = self.compute_structured_jump_relation()
        self.structured_back_edges: Dict[str, Set[str]] = self.compute_back_edges()
        self.topological_ordering: List[str] = self.compute_topological_ordering()


    def create_non_doomed_graph(self) -> Dict[str, List[str]]:
        graph = self.jump_relation.copy()
        doomed = get_doomed_blocks(graph)
        return get_non_doomed_graph(graph, doomed)


    def compute_structured_jump_relation(self) -> Dict[str, List[str]]:
        result: Dict[str, List[str]] = self.jump_relation.copy()
        # First, remove duplicate successors
        for block in result:
            duplicate_free: List[str] = []
            for successor in result[block]:
                if block not in duplicate_free:
                    duplicate_free.append(successor)
            result[block] = duplicate_free
        # Now add any extra edges arising from merge and continue relations
        for structured_relation in [self.merge_relation, self.continue_relation]:
            for block in structured_relation:
                if block not in result:
                    result[block] = [structured_relation[block]]
                elif structured_relation[block] not in result[block]:
                    result[block].append(structured_relation[block])
        return result


    def compute_topological_ordering(self) -> List[str]:
        # This is an implementation of Kahn’s algorithm for topological sorting.
        result: List[str] = []

        in_degree: Dict[str, int] = {}
        for blocks in [self.regular_blocks, self.loop_header_blocks, self.selection_header_blocks]:
            for block in blocks:
                in_degree[block] = 0

        for block in self.structured_jump_relation:
            for successor in self.structured_jump_relation[block]:
                if block in self.structured_back_edges and successor in self.structured_back_edges[block]:
                    continue
                in_degree[successor] += 1

        # Start with all nodes with zero in-degree
        queue: Deque[str] = Deque()

        # Entry block must apppear as the first block else variable definitions appear 
        # after other blocks which is not allowed
        queue.appendleft(self.entry_block)
        
        for block in in_degree:
            if in_degree[block] == 0 and block != self.entry_block:
                queue.appendleft(block)

        # Pop blocks from the queue, adding them to the sorted order and decreasing the
        # in-degrees of their successors. A successor who's in-degree becomes zero
        # gets added to the queue.

        while len(queue) > 0:
            block = queue.pop()
            result.append(block)
            if block in self.structured_jump_relation:
                for successor in self.structured_jump_relation[block]:
                    if block in self.structured_back_edges and successor in self.structured_back_edges[block]:
                        continue
                    assert in_degree[successor] > 0
                    in_degree[successor] -= 1
                    if in_degree[successor] == 0:
                        queue.appendleft(successor)

        assert len(result) == len(in_degree)
        return result


    def compute_back_edges(self) -> Dict[str, Set[str]]:
        def dfs(back_edges: Dict[str, Set[str]], stack: List[str], visited: Set[str], block: str):
            assert block not in visited
            assert block not in stack
            visited.add(block)
            stack.append(block)
            if block in self.structured_jump_relation:
                for successor in self.structured_jump_relation[block]:
                    if successor in stack:
                        assert successor in visited
                        if block not in back_edges:
                            back_edges[block] = set()
                        back_edges[block].add(successor)
                    elif successor not in visited:
                        dfs(back_edges, stack, visited, successor)
            stack.pop()

        result: Dict[str, Set[str]] = {}
        dfs(result, [], set(), self.entry_block)
        return result


    def parallel_edges(self, a, b):
        jump = self.jump_relation.copy()
        if a in jump:
            for block in jump[a]:
                if block == b:
                    return jump[a].count(b)
        return 0


    def is_conditional(self, label: str):
        num_successors: int = 0 if label not in self.jump_relation else len(self.jump_relation[label])
        return num_successors > 1 or label in self.switch_blocks


    # find the nodes which have OpBranchConditional or OpSwitch as their terminators
    def get_conditional_blocks_in_path(self, path: List[str]) -> List[str]:
        conditional_blocks = []
        for label in path:
            if self.is_conditional(label):
                conditional_blocks.append(label)
        return list(dict.fromkeys(conditional_blocks)) # duplicates removed


    def get_block_id(self, label: str) -> str:
        if label not in self.label_to_id:
            self.label_to_id[label] = str(self.next_id)
            self.next_id += 1
        return self.label_to_id[label]


    @staticmethod
    def indented_block_label(block_id: str) -> str:
        num_spaces: int = len("               ") - (len(block_id) + len("% = "))
        return "{0}%{1}".format(" " * num_spaces, block_id)


    def block_to_string(self, label: str) -> str:
        num_successors: int = 0 if label not in self.jump_relation else len(self.jump_relation[label])
        result = "{0} = OpLabel ; {1}\n".format(self.indented_block_label(self.get_block_id(label)), label)
        if label in self.loop_header_blocks:
            assert num_successors == 1 or num_successors == 2
            result += "               OpLoopMerge %{0} %{1} None\n".format(
                self.get_block_id(self.merge_relation[label]),
                self.get_block_id(self.continue_relation[label]))
        elif label in self.selection_header_blocks:
            assert (label not in self.switch_blocks and num_successors == 2) or num_successors >= 1
            result += "               OpSelectionMerge %{0} None\n".format(
                self.get_block_id(self.merge_relation[label]))
        else:
            assert num_successors <= 2
        if label not in self.jump_relation:
            assert num_successors == 0
            result += "               OpReturn"
        elif label not in self.switch_blocks:
            assert num_successors == 1 or num_successors == 2
            if num_successors == 1:
                result += "               OpBranch %{0}".format(self.get_block_id(self.jump_relation[label][0]))
            else:
                result += "               OpBranchConditional %{0} %{1} %{2}".format(
                    self.TRUE_CONSTANT_ID,
                    self.get_block_id(self.jump_relation[label][0]),
                    self.get_block_id(self.jump_relation[label][1]))
        else:
            assert num_successors > 0
            result += "               OpSwitch %{0} %{1}".format(self.ZERO_CONSTANT_ID,
                                                                 self.get_block_id(self.jump_relation[label][0]))
            for index in range(1, len(self.jump_relation[label])):
                result += " {0} %{1}".format(index, self.get_block_id(self.jump_relation[label][index]))
        return result + "\n"


    def to_string(self) -> str:

        result = """               OpCapability Shader
               OpMemoryModel Logical GLSL450
               OpEntryPoint GLCompute %{0} "main"
               OpExecutionMode %{0} LocalSize 1 1 1
          %{1} = OpTypeVoid
          %{2} = OpTypeFunction %{1}
          %{3} = OpTypeBool
          %{4} = OpTypeInt 32 0
          %{5} = OpConstantTrue %{3}
          %{6} = OpConstant %{4} 0

          %{0} = OpFunction %{1} None %{2}

""".format(self.MAIN_FUNCTION_ID,
           self.VOID_TYPE_ID,
           self.MAIN_FUNCTION_TYPE_ID,
           self.BOOL_TYPE_ID,
           self.UINT_TYPE_ID,
           self.TRUE_CONSTANT_ID,
           self.ZERO_CONSTANT_ID)
        result += "\n".join([self.block_to_string(block) for block in self.topological_ordering])
        result += "\n               OpFunctionEnd"

        return result


    @staticmethod
    def find_nth_occurrence(haystack: str, needle: str, occurrence: int) -> int:
        idx = haystack.find(needle)
        if idx < 0:
            return -1
        return idx if occurrence <= 1 else idx + 1 + CFG.find_nth_occurrence(haystack[idx+1:], needle, occurrence-1)


    @staticmethod
    def add_barrier(block_output: str, start_line: int, prng) -> str:
        barrier_line_offset = prng.randint(start_line, block_output.count("\n"))
        line_idx = CFG.find_nth_occurrence(block_output, "\n", barrier_line_offset)
        barrier_line = "               OpControlBarrier %constant_2 %constant_2 %constant_0 ; Barrier with Workgroup scope\n"
        return block_output[:line_idx+1] + barrier_line + block_output[line_idx+1:]
    

    def create_op_phi_instructions(self, label, predecessors, num_successors, path_ids, indent1):
        assert len(predecessors) > 0
        block_id = self.get_block_id(label)
        output_phi = indent1 + '%temp_' + block_id + '_0 = OpPhi %' + str(self.UINT_TYPE_ID)
        for predecessor in predecessors:
            pred_id = self.label_to_id[predecessor]
            if pred_id in path_ids:
                output_phi += ' %temp_' + str(pred_id) + '_2 %' + str(pred_id)
            else:
                output_phi += ' %dummy_val %' + str(pred_id)
        output_phi += '\n'

        input_phi = ''
        if num_successors > 1 or label in self.switch_blocks:
            input_phi += indent1 + '%temp_' + block_id + '_3 = OpPhi %' + str(self.UINT_TYPE_ID)
            for predecessor in predecessors:
                pred_id = self.label_to_id[predecessor]
                if pred_id in path_ids:
                    input_phi += ' %' + str(pred_id) + '_target_' + str(block_id) + ' %' + str(pred_id)
                else:
                    input_phi += ' %dummy_val %' + str(pred_id)
            input_phi += '\n'
        return output_phi + input_phi   


    def block_to_string_fleshing(self, 
                                 label: str, 
                                 paths: List[Path], 
                                 x_workgroups: int, 
                                 y_workgroups: int, 
                                 workgroup_size: int, 
                                 prng: Random, 
                                 include_op_phi: bool,
                                 path_ids: Set[str],
                                 conditional_block_ids: Set[str],
                                 exit_blocks: Set[str]) -> str:
        block_id: str = self.get_block_id(label)
        indent0 = self.indented_block_label(block_id)
        indent1 = ' '*(len("               ") - (len(block_id) + len("%temp___ = ")))
        num_successors: int = 0 if label not in self.jump_relation else len(self.jump_relation[label])
        result = "\n{0} = OpLabel ; {1}\n".format(indent0, label)
        condition = 'temp_' + block_id + '_6' if block_id in path_ids else self.TRUE_CONSTANT_ID
        selector = 'temp_' + block_id + '_5' if block_id in path_ids else self.ZERO_CONSTANT_ID
        if label == self.entry_block:
            result += '               %output_index = OpVariable %local_int_ptr Function %constant_0\n'
            for block in conditional_block_ids:
                result += '               %directions_' + str(block) + '_index = OpVariable %local_int_ptr Function %constant_0\n'

            result += '\n               %local_invocation_idx = OpLoad %' + str(self.UINT_TYPE_ID) + ' %local_invocation_idx_var\n'

            result += '               %x_wg_dim_ptr = OpAccessChain %input_int_ptr %workgroup_id_var %constant_0\n'
            result += '               %y_wg_dim_ptr = OpAccessChain %input_int_ptr %workgroup_id_var %constant_1\n'
            result += '               %z_wg_dim_ptr = OpAccessChain %input_int_ptr %workgroup_id_var %constant_2\n'
            result += '               %x_wg_dim = OpLoad %' + str(self.UINT_TYPE_ID) + ' %x_wg_dim_ptr\n'
            result += '               %y_wg_dim = OpLoad %' + str(self.UINT_TYPE_ID) + ' %y_wg_dim_ptr\n'
            result += '               %z_wg_dim = OpLoad %' + str(self.UINT_TYPE_ID) + ' %z_wg_dim_ptr\n'
            result += '               %z_idx_component = OpIMul %' + str(self.UINT_TYPE_ID) + ' %z_wg_dim %constant_' + str(x_workgroups * y_workgroups) + '\n'
            result += '               %y_idx_component = OpIMul %' + str(self.UINT_TYPE_ID) + ' %y_wg_dim %constant_' + str(x_workgroups) + '\n'
            result += '               %yz_idx_component = OpIAdd %' + str(self.UINT_TYPE_ID) + ' %y_idx_component %z_idx_component\n'
            result += '               %workgroup_idx = OpIAdd %' + str(self.UINT_TYPE_ID) + ' %yz_idx_component %x_wg_dim\n\n'

            result += '               %workgroup_offset = OpIMul %' + str(self.UINT_TYPE_ID) + ' %workgroup_idx %constant_' + str(workgroup_size) + '\n'
            result += '               %thread_index_offset = OpIAdd %' + str(self.UINT_TYPE_ID) + ' %workgroup_offset %local_invocation_idx\n\n'

            for block in conditional_block_ids:
                result += '               %directions_' + str(block) + '_start_idx_ptr = OpAccessChain %storage_buffer_int_ptr %directions_' + str(block) + '_index_variable %constant_0 %thread_index_offset\n'
                result += '               %directions_' + str(block) + '_offset = OpLoad %' + str(self.UINT_TYPE_ID) + ' %directions_' + str(block) + '_start_idx_ptr\n'

            result += '               %output_start_idx_ptr = OpAccessChain %storage_buffer_int_ptr %output_index_variable %constant_0 %thread_index_offset\n'
            result += '               %output_offset = OpLoad %' + str(self.UINT_TYPE_ID) + ' %output_start_idx_ptr\n'
            result += '\n'

            for block in conditional_block_ids:
                result += '               OpStore %directions_' + str(block) + '_index %directions_' + str(block) + '_offset\n' 
            result += '               OpStore %output_index %output_offset\n'

            result += '\n'

        predecessors = self.reverse_graph[label]
        num_op_phi = 0
        if block_id in path_ids:
            if include_op_phi and label != self.entry_block:
                result += self.create_op_phi_instructions(label, predecessors, num_successors, path_ids, indent1)        
                num_op_phi += 2
            else:
                result += indent1 + '%temp_' + block_id + '_0 = OpLoad %' + str(self.UINT_TYPE_ID) + ' %output_index\n'

            output_increment = 2 if block_id in exit_blocks else 1
            result += indent1 + '%temp_' + block_id + '_1 = OpAccessChain %storage_buffer_int_ptr %output_variable %constant_0 %temp_' + block_id + '_0\n' + \
                      '               OpStore %temp_' + block_id + '_1 %constant_' + block_id + '\n' + \
                      indent1 + '%temp_' + block_id + '_2 = OpIAdd %' + str(self.UINT_TYPE_ID) + ' %temp_' + block_id + '_0 %constant_' + str(output_increment) + '\n'

            if not include_op_phi:
                result += '               OpStore %output_index %temp_' + block_id + '_2\n'

            if block_id in conditional_block_ids:
                if not include_op_phi or label == self.entry_block:
                    result += indent1 + '%temp_' + block_id + '_3 = OpLoad %' + str(self.UINT_TYPE_ID) + ' %directions_' + block_id + '_index\n'

                result += indent1 + '%temp_' + block_id + '_4 = OpAccessChain %storage_buffer_int_ptr %directions_' + block_id + '_variable %constant_0 %temp_' + block_id + '_3\n' + \
                          indent1 + '%temp_' + block_id + '_5 = OpLoad %' + str(self.UINT_TYPE_ID) + ' %temp_' + block_id + '_4\n'

                if label not in self.switch_blocks:
                    result += indent1 + '%temp_' + block_id + '_6 = OpIEqual %' + str(self.BOOL_TYPE_ID) + ' %temp_' + block_id + '_5 %constant_1\n' + \
                              indent1 + '%temp_' + block_id + '_7 = OpIAdd %' + str(self.UINT_TYPE_ID) + ' %temp_' + block_id + '_3 %constant_1\n' + \
                              '               OpStore %directions_' + block_id + '_index %temp_' + block_id + '_7\n'

                else:
                    result += indent1 + '%temp_' + block_id + '_7 = OpIAdd %' + str(self.UINT_TYPE_ID) + ' %temp_' + block_id + '_3 %constant_1\n' + \
                              '               OpStore %directions_' + block_id + '_index %temp_' + block_id + '_7\n'


            if include_op_phi and num_successors > 0:
                successors = set(self.get_block_id(node) for node in self.jump_relation[label] if self.get_block_id(node) in path_ids and self.get_block_id(node) in conditional_block_ids)
                for successor in successors:
                    result += indent1 + '%' + block_id + '_target_' + str(successor) + ' = OpLoad %' + str(self.UINT_TYPE_ID) + ' %directions_' + str(successor) + '_index\n'

            # include barriers at any location before the final jump/return
            if label in paths[0].barrier_blocks:
                result = CFG.add_barrier(result, 2 + num_op_phi, prng)

        if label in self.loop_header_blocks:
            assert num_successors == 1 or num_successors == 2
            result += "               OpLoopMerge %{0} %{1} None\n".format(
                self.get_block_id(self.merge_relation[label]),
                self.get_block_id(self.continue_relation[label]))
        elif label in self.selection_header_blocks:
            assert (label not in self.switch_blocks and num_successors == 2) or num_successors >= 1
            result += "               OpSelectionMerge %{0} None\n".format(
                self.get_block_id(self.merge_relation[label]))
        else:
            assert num_successors <= 2 # Q: How can a non loop/selection header block have multiple successors? Aren't OpLoopMerge and OpSelectionMerge the only merge instructions?
        
        if label not in self.jump_relation:
            assert num_successors == 0
            result += "               OpReturn" # Exit nodes are defined as having no successors. Can we use an alternative to OpReturn in some cases to make fleshing more interesting?
        elif label not in self.switch_blocks:
            assert num_successors == 1 or num_successors == 2
            if num_successors == 1:
                result += "               OpBranch %{0}".format(self.get_block_id(self.jump_relation[label][0]))
            else:
                result += "               OpBranchConditional %{0} %{1} %{2}".format(
                    condition,
                    self.get_block_id(self.jump_relation[label][0]),
                    self.get_block_id(self.jump_relation[label][1]))
        else:
            assert num_successors > 0
            result += "               OpSwitch %{0} %{1}".format(selector,
                                                                 self.get_block_id(self.jump_relation[label][0]))
            for index in range(1, len(self.jump_relation[label])):
                result += " {0} %{1}".format(index, self.get_block_id(self.jump_relation[label][index]))
        return result + "\n"


    @staticmethod
    def compute_num_threads(x_threads: int, y_threads: int, z_threads: int) -> int:
        return (z_threads-1) * x_threads * y_threads + (y_threads-1) * x_threads + (x_threads-1) + 1


    @staticmethod
    def compute_num_workgroups(x_threads: int, y_threads: int, z_threads: int) -> int:
        return (z_threads-1) * x_threads * y_threads + (y_threads-1) * x_threads + (x_threads-1) + 1


    def fleshout(self, 
                 paths: List[Path], 
                 prng: Random, 
                 seed: int, 
                 x_threads: int, 
                 y_threads: int, 
                 z_threads: int, 
                 x_workgroups: int, 
                 y_workgroups: int, 
                 z_workgroups: int, 
                 include_op_phi: bool) -> str:
        """
███████ ██      ███████ ███████ ██   ██ ██ ███    ██  ██████       ██████  ██    ██ ████████ 
██      ██      ██      ██      ██   ██ ██ ████   ██ ██           ██    ██ ██    ██    ██    
█████   ██      █████   ███████ ███████ ██ ██ ██  ██ ██   ███     ██    ██ ██    ██    ██    
██      ██      ██           ██ ██   ██ ██ ██  ██ ██ ██    ██     ██    ██ ██    ██    ██    
██      ███████ ███████ ███████ ██   ██ ██ ██   ████  ██████       ██████   ██████     ██                                                                                                                                                                                
        """
        all_blocks_id: List[str] = [self.label_to_id[block] for block in self.all_blocks]
        all_blocks_id.sort()

        conditional_block_ids: List[str] = list(set([id for path in paths for id in path.conditional_block_ids]))
        conditional_block_ids.sort()
        # add constants: 0: to initialize counter variables to 0
        #                1: for incrementing counter variables
        #                2: for incrementing the last output index
        constants: Set[str] = {str(0), str(1), str(2)}.union(set(all_blocks_id))

        num_local_threads = self.compute_num_threads(x_threads, y_threads, z_threads)
        num_workgroups = self.compute_num_workgroups(x_workgroups, y_workgroups, z_workgroups)
        total_num_threads = num_local_threads * num_workgroups
        constants.update(str(x) for x in [x_threads, y_threads, z_threads, x_workgroups, y_workgroups, x_workgroups * y_workgroups, num_local_threads, total_num_threads])

        # find the sizes of the input and output arrays
        array_sizes: DefaultDict[str, int] = defaultdict(int)
        index_offsets: DefaultDict[str, List[int]] = defaultdict(list)
        for path in paths:
            unvisited = set(conditional_block_ids).union({'output'})
            for arr_name, size in path.array_sizes.items():
                unvisited.remove(arr_name)
                index_offsets[arr_name].append(array_sizes[arr_name])
                array_sizes[arr_name] += size
            
            for arr_name in unvisited:
                index_offsets[arr_name].append(0)

        # Set size of the arrays that will hold the starting indices for each thread
        array_sizes["index"] = total_num_threads

        unique_array_sizes: Set[int] = set(array_sizes.values())
        constants.update([constant for path in paths for constant in path.constants])
        constants.update([str(val) for val in unique_array_sizes])

        tab: str = '               '
        constants2string = '\n'
        constants2string += tab + f"%dummy_val = OpConstant %{str(self.UINT_TYPE_ID)} {str(666)}\n"
        for i in constants:
            constants2string += tab + '%constant_' + str(i) + ' = OpConstant %' + str(self.UINT_TYPE_ID) + ' ' + str(i) + '\n'

        # types_variables is used to declare various types and variables for storage buffers.
        types_variables = ''

        for b in set(unique_array_sizes):
            if b != array_sizes['output'] or array_sizes['index'] == array_sizes['output']:
                types_variables += '\n' + \
                    tab + 'OpDecorate %size_' + str(b) + '_struct_type BufferBlock\n' + \
                    tab + 'OpMemberDecorate %size_' + str(b) + '_struct_type 0 Offset 0\n' + \
                    tab + 'OpDecorate %size_' + str(b) + '_array_type ArrayStride 4\n'

        types_variables += '\n' + tab + 'OpDecorate %output_struct_type BufferBlock\n' + \
                                  tab + 'OpMemberDecorate %output_struct_type 0 Offset 0\n' + \
                                  tab + 'OpDecorate %output_array_type ArrayStride 4\n'
        
        bindings: Dict[str, int] = {}
        for i in conditional_block_ids:
            types_variables += '\n' + tab + 'OpDecorate %directions_' + str(i) + '_variable DescriptorSet 0\n' + \
                                      tab + 'OpDecorate %directions_' + str(i) + '_variable Binding ' + str(len(bindings)) + '\n'
            bindings[i] = len(bindings)
            types_variables += '\n' + tab + 'OpDecorate %directions_' + str(i) + '_index_variable DescriptorSet 0\n' + \
                                      tab + 'OpDecorate %directions_' + str(i) + '_index_variable Binding ' + str(len(bindings)) + '\n'
            bindings[f"{i}_index"] = len(bindings)

        types_variables += '\n' + tab + 'OpDecorate %output_variable DescriptorSet 0\n' + \
                                  tab + 'OpDecorate %output_variable Binding ' + str(len(bindings)) + '\n'
        bindings['output'] = len(bindings)
        types_variables += '\n' + tab + 'OpDecorate %output_index_variable DescriptorSet 0\n' + \
                                  tab + 'OpDecorate %output_index_variable Binding ' + str(len(bindings)) + '\n'
        bindings['output_index'] = len(bindings)

        storage_buffers = ''
        for s in set(unique_array_sizes):
            if array_sizes['output'] != s or array_sizes['index'] == array_sizes['output']:
                storage_buffers += '\n' + tab + '%size_' + str(s) + '_array_type = OpTypeArray %' + str(self.UINT_TYPE_ID) + ' %constant_' + str(s) + '\n' + \
                                          tab + '%size_' + str(s) + '_struct_type = OpTypeStruct %size_' + str(s) + '_array_type\n' + \
                                          tab + '%size_' + str(s) + '_pointer_type = OpTypePointer Uniform %size_' + str(s) + '_struct_type\n'

        storage_buffers += '\n'
        for id, size in array_sizes.items():
            if id == "output" or id == "index":
                continue
            storage_buffers += tab + f"%directions_{str(id)}_variable = OpVariable %size_{str(size)}_pointer_type Uniform\n"
            storage_buffers += tab + f"%directions_{str(id)}_index_variable = OpVariable %size_{str(array_sizes['index'])}_pointer_type Uniform\n"

        storage_buffers += '\n' + tab + '%output_array_type = OpTypeArray %' + str(self.UINT_TYPE_ID) + ' %constant_' + str(array_sizes['output']) + '\n' + \
                                  tab + '%output_struct_type = OpTypeStruct %output_array_type\n' + \
                                  tab + '%output_pointer_type = OpTypePointer Uniform %output_struct_type\n'+ \
                                  tab + '%output_variable = OpVariable %output_pointer_type Uniform\n'+ \
                                  tab + f"%output_index_variable = OpVariable %size_{str(array_sizes['index'])}_pointer_type Uniform\n\n"+ \
                                  tab + '%local_int_ptr = OpTypePointer Function %' + str(self.UINT_TYPE_ID) + '\n'+ \
                                  tab + '%storage_buffer_int_ptr = OpTypePointer Uniform %' + str(self.UINT_TYPE_ID) + '\n'

        end = '\n\n END\n\n'

        directions: DefaultDict[str, List[int]] = defaultdict(list)
        for path in paths:
            for block_id, choices in path.directions.items():
                directions[block_id] += choices

        for block_id, choices in directions.items():
            end += ' BUFFER directions_{0} DATA_TYPE uint32 STD430 DATA {1} END\n'\
                .format(block_id, ' '.join([str(direction) for direction in directions[block_id]]))
            end += ' BUFFER directions_{0}_index DATA_TYPE uint32 STD430 DATA {1} END\n'\
                .format(block_id, ' '.join([str(index) for index in index_offsets[block_id]]))
        

        end += """
 BUFFER output DATA_TYPE uint32 STD430 SIZE {0} FILL 0
 BUFFER output_index DATA_TYPE uint32 STD430 DATA {1} END

 PIPELINE compute pipeline
   ATTACH compute_shader
""".format(array_sizes['output'], ' '.join([str(index) for index in index_offsets['output']]))

        for id in conditional_block_ids:
            end += '   BIND BUFFER directions_{0} AS storage DESCRIPTOR_SET 0 BINDING {1}\n' \
                .format(id, bindings[id])
            end += '   BIND BUFFER directions_{0}_index AS storage DESCRIPTOR_SET 0 BINDING {1}\n' \
                .format(id, bindings[str(id) + "_index"])

        end += """
   BIND BUFFER output AS storage DESCRIPTOR_SET 0 BINDING {0}
   BIND BUFFER output_index AS storage DESCRIPTOR_SET 0 BINDING {1}

 END
 RUN pipeline {2} {3} {4}\n
""".format(bindings['output'], bindings['output_index'], x_workgroups, y_workgroups, z_workgroups)

        for id in conditional_block_ids:
            end += ' EXPECT directions_{0} IDX 0 EQ {1}\n' \
                .format(id, ' '.join([str(direction) for direction in directions[id]]))
            end += ' EXPECT directions_{0}_index IDX 0 EQ {1}\n' \
                .format(id, ' '.join([str(index) for index in index_offsets[id]]))

        expected_output = []
        for path in paths:
            expected_output += [id for id in path.id_path] + [str(0)]
        end += ' EXPECT output IDX 0 EQ {0}\n' \
            .format(' '.join(expected_output))
        end += ' EXPECT output_index IDX 0 EQ {0}\n' \
            .format(' '.join([str(index) for index in index_offsets['output']]))


        paths2string = ''
        for path_idx, path in enumerate(set(paths)):
            paths2string += f"; unique path #{path_idx}: {str(path)}\n"

        result_fleshed = """#!amber
SHADER compute compute_shader SPIRV-ASM
; Follow the path(s):
{7}
;
; {8} CFG nodes have OpBranchConditional or OpSwitch as their terminators (denoted <n>): {9}.
;
; To follow these paths, we need to make decisions each time we reach {10}.
; These paths were generated with the seed {14} and have lengths ranging from {15} to {16}.
;
; We equip the shader with {8}+1 storage buffers:
; - An input storage buffer with the directions for each node {10}
; - An output storage buffer that records the blocks that are executed

; SPIR-V
; Version: 1.3
; Generator: Khronos Glslang Reference Front End; 8
; Bound: 15
; Schema: 0
               OpCapability Shader
               OpMemoryModel Logical GLSL450
               OpEntryPoint GLCompute %{0} "main" %local_invocation_idx_var %workgroup_id_var
               OpExecutionMode %{0} LocalSize {17} {18} {19}
               
               ; Below, we declare various types and variables for storage buffers.
               ; These decorations tell SPIR-V that the types and variables relate to storage buffers
{11}
               OpDecorate %local_invocation_idx_var BuiltIn LocalInvocationIndex
               OpDecorate %workgroup_id_var BuiltIn WorkgroupId

          %{1} = OpTypeVoid
          %{2} = OpTypeFunction %{1}
          %{3} = OpTypeBool
          %{4} = OpTypeInt 32 0
          %{5} = OpConstantTrue %{3}
          %{6} = OpConstant %{4} 0
{12}
               ; Declaration of storage buffers for the {8} directions and the output
{13}
               %input_int_ptr = OpTypePointer Input %{4}
               %local_invocation_idx_var = OpVariable %input_int_ptr Input
               %vec_3_input = OpTypeVector %{4} 3
               %workgroup_ptr = OpTypePointer Input %vec_3_input 
               %workgroup_id_var = OpVariable %workgroup_ptr Input

          %{0} = OpFunction %{1} None %{2}
""".format(self.MAIN_FUNCTION_ID,
                   self.VOID_TYPE_ID,
                   self.MAIN_FUNCTION_TYPE_ID,
                   self.BOOL_TYPE_ID,
                   self.UINT_TYPE_ID,
                   self.TRUE_CONSTANT_ID,
                   self.ZERO_CONSTANT_ID,
                   paths2string, # {7}
                   len(conditional_block_ids), # {8}
                   ' and '.join(filter(None, [', '.join(conditional_block_ids[:-1])] + conditional_block_ids[-1:])), # {9}
                   ' or '.join(filter(None, [', '.join(conditional_block_ids[:-1])] + conditional_block_ids[-1:])),  # {10}
                   types_variables, # {11}
                   constants2string, # {12}
                   storage_buffers, # {13}
                   seed, # {14}
                   min([len(path) for path in paths]), # {15}
                   max([len(path) for path in paths]), # {16}
                   x_threads, # {17}
                   y_threads, # {18}
                   z_threads) # {19}
        
        path_ids: Set[str] = set(id for path in paths for id in path.id_path)
        exit_blocks: Set[str] = set(path.id_path[-1] for path in paths)
        result_fleshed += "\n".join([self.block_to_string_fleshing(block, paths, x_workgroups, y_workgroups, num_local_threads, prng, include_op_phi, path_ids, set(conditional_block_ids), exit_blocks) for block in self.topological_ordering])
        result_fleshed += "\n               OpFunctionEnd"
        result_fleshed += end

        return result_fleshed


    def random_path_of_desired_length_without_passing_through_doomed(self, start, length, current_iteration_vector, iteration_vectors, prng):
        if start not in self.non_doomed_graph:
            raise AllTerminalNodesUnreachableError()
        return self.find_random_path(start, length, [], current_iteration_vector, iteration_vectors, prng)


    def update_iteration_vectors(self, node, current_iteration_vector, iteration_vectors):
        if node in self.merge_to_loop_header:
            current_iteration_vector[self.merge_to_loop_header[node]] = 0

        if node in self.loop_header_blocks:
            current_iteration_vector[node] += 1

        iteration_vectors[node].append(current_iteration_vector.copy())


    def find_random_path(self, src, target_length, path, current_iteration_vector, iteration_vectors, prng):
        path.append(src)

        self.update_iteration_vectors(src, current_iteration_vector, iteration_vectors)

        if len(path) >= target_length:
            return path
        
        if src not in self.non_doomed_graph:
            assert src in self.exit_blocks
            return path
        
        next_node = prng.choice(self.non_doomed_graph[src])
        return self.find_random_path(next_node, target_length, path, current_iteration_vector, iteration_vectors, prng)


    def find_path_to_exit_node(self, graph, src, current_iteration_vector, iteration_vectors):
        # BFS where termination condition is reaching an exit node.
        # Since the graph is unweighted this will also give us the
        # shortest path to an exit node.
        parents = {}
        parents[src] = None
        queue = deque()
        queue.append(src)
        while queue:
            n = queue.popleft()

            if n != src:
                self.update_iteration_vectors(n, current_iteration_vector, iteration_vectors)

            if n in self.exit_blocks:
                return recover_bfs_path(src, n, parents) 

            if n not in graph:
                raise TerminalNodesUnreachableFromCurrentNodeError(n, self.exit_blocks)

            for neighbour in graph[n]:
                if neighbour not in parents:
                    queue.append(neighbour)
                    parents[neighbour] = n
        raise TerminalNodesUnreachableFromCurrentNodeError(src, self.exit_blocks)


    def generate_path(self, prng, max_path_length=MAX_PATH_LENGTH) -> Path:
        current_iteration_vector = dict((block, 0) for block in self.loop_header_blocks)
        iteration_vectors: DefaultDict[str, List[Dict[str, int]]] = defaultdict(list)
        rand_path_prefix = self.random_path_of_desired_length_without_passing_through_doomed(self.entry_block,
                                                                                             max_path_length,
                                                                                             current_iteration_vector,
                                                                                             iteration_vectors,
                                                                                             prng)
        if rand_path_prefix[-1] not in self.exit_blocks:
            rand_path_suffix = self.find_path_to_exit_node(self.jump_relation, rand_path_prefix[-1], current_iteration_vector, iteration_vectors)
            assert rand_path_suffix is not None
            rand_path_prefix += rand_path_suffix[1:]
        return Path(self, prng, rand_path_prefix, iteration_vectors)


class Path:

    def __init__(self, cfg: CFG, rng: Random, path: List[str], iteration_vectors: DefaultDict[str, List[Dict[str, int]]]) -> None:
        self.cfg: CFG = cfg
        self.rng: Random = rng
        self.label_path: List[str] = path
        self.iteration_vectors: DefaultDict[str, List[Dict[str, int]]] = iteration_vectors
        self.id_path: List[str] = [cfg.get_block_id(label) for label in path]
        self.conditional_block_labels: List[str] = cfg.get_conditional_blocks_in_path(path)
        self.conditional_block_ids: List[str] = [cfg.get_block_id(label) for label in self.conditional_block_labels]
        self.array_sizes: Dict[str, int] = self.compute_array_sizes()
        self.switch2edges: Dict[str, List[int]] = self.compute_switch_edges()
        self.directions: Dict[str, List[int]] = self.compute_direction_arrays()
        self.constants: Set[str] = self.compute_constants()
        self.barrier_blocks: Set[str] = set()
    

    def compute_array_sizes(self) -> Dict[str, int]:
        array_sizes: Dict[str, int] = {}
        for id in self.conditional_block_ids:
            array_size = self.id_path.count(id) 
            array_sizes[str(id)] = array_size
        output_length = len(self.id_path) + 1
        array_sizes['output'] = output_length
        return array_sizes
    

    def compute_switch_edges(self) -> Dict[str, List[int]]:
        # for every switch find the edge number from the OpSwitch list: if there are parallel edges incident to a switch, then pick one edge randomly
        # compute successors of the block and the number of the edge which leads to the block in the path
        switch2edges: Dict[str, List[int]] = {k: [] for k in self.cfg.switch_blocks}
        for idx, sw in enumerate(self.label_path[:-1]):
            if sw in self.cfg.switch_blocks:
                successor_of_sw_index = idx + 1
                target = self.label_path[successor_of_sw_index]
                # find the position of target in self.jump_relation[sw]: if parallel edges,
                # find the random-th occurence in self.jump_relation[sw]
                parallel = self.cfg.jump_relation[sw].count(target)
                if parallel == 1:
                    literal_of_target = self.cfg.jump_relation[sw].index(target)
                    switch2edges[sw].append(literal_of_target)
                else:
                    parallel_indices = [i for i, x in enumerate(self.cfg.jump_relation[sw]) if x == target]
                    literal_of_target = self.rng.choice(parallel_indices)
                    switch2edges[sw].append(literal_of_target)
        return switch2edges


    def compute_constants(self) -> Set[str]:
        constants = set(self.id_path)
        for size in self.array_sizes.values():
            constants.add(str(size))
        
        for targets in self.switch2edges.values():
            constants.update([str(target) for target in targets])        
        return constants
    

    def compute_direction_arrays(self) -> Dict[str, List[int]]:
        directions: Dict[str, List[int]] = {k: [] for k in self.conditional_block_ids}
        for label in self.conditional_block_labels:
            label_id: str = self.cfg.get_block_id(label)
            for i in range(len(self.id_path[:-1])):
                if self.id_path[i] == label_id:
                    if label not in self.cfg.switch_blocks:
                        if self.id_path[i + 1] == self.cfg.get_block_id(self.cfg.jump_relation[label][0]):
                            directions[label_id].append(1)
                        elif self.id_path[i + 1] == self.cfg.get_block_id(self.cfg.jump_relation[label][1]):
                            directions[label_id].append(0)
                    else:
                        directions[label_id] = self.switch2edges[label]
        return directions
    

    def is_compatible(self, other: Path) -> bool:
        return all([self.iteration_vectors[block] == other.iteration_vectors[block] for block in self.barrier_blocks.union(other.barrier_blocks)])


    def __len__(self) -> int:
        return len(self.id_path)
    

    def __str__(self) -> str:
        path2string = ''
        occurrences = {}
        for block in self.cfg.switch_blocks:
            occurrences[block] = 0

        for block in self.label_path[:-1]:
            block_id = self.cfg.get_block_id(block)
            b = ''
            if block_id in self.conditional_block_ids:
                b = '<' + str(block_id) + '>'
            else:
                b = str(block_id)
            
            if block in self.barrier_blocks:
                b = 'b(' + b + ')'

            if block not in self.cfg.switch_blocks:
                path2string += b + ' -> '
            else:
                path2string += b + ' -> ' + 'edge_' + str(self.switch2edges[block][occurrences[block]]) + ' -> '
                occurrences[block] += 1
        path2string += str(self.cfg.get_block_id(self.label_path[-1]))
        return path2string


    def __key(self):
        return (tuple(self.id_path), frozenset(self.barrier_blocks), tuple(sorted(self.switch2edges))) 


    def __eq__(self, other: object) -> bool:
        if isinstance(other, Path):
            return self.__key() == other.__key()
        return NotImplemented
    

    def __hash__(self) -> int:
        return hash(self.__key())


def get_barrier_blocks(cfg: CFG, path: Path, likelihood_percentage: int, rng) -> set:
    return set(block for block in path.label_path if block != cfg.entry_block and rng.choices([True, False], [likelihood_percentage, 100-likelihood_percentage], k=1)[0])


def generate_paths(original_path, cfg, rng, path_length) -> List[Path]:
    MAX_PATH_GENERATION_ATTEMPTS = 100
    paths = [original_path]
    for _ in range(MAX_PATH_GENERATION_ATTEMPTS):
        new_path = cfg.generate_path(rng, path_length)
        new_path.barrier_blocks = original_path.barrier_blocks
        if original_path.is_compatible(new_path) and new_path != original_path:
            paths.append(new_path)
    return paths


def fleshout(xml_file, path_length=MAX_PATH_LENGTH, seed=None, x_threads=1, y_threads=1, z_threads=1, x_workgroups=1, y_workgroups=1, z_workgroups=1, include_barriers=True, include_op_phi=True, use_different_paths=True):
    rng = Random()
    if seed is None:
        seed = random.randrange(0, sys.maxsize)
    rng.seed(seed)

    tree = elementTree.parse(xml_file)

    alloy = tree.getroot()
    assert alloy.tag == "alloy"
    assert len(alloy) == 1
    instance = alloy[0]
    assert instance.tag == "instance"

    if not any(block in get_jump_relation(instance) for block in get_all_blocks(instance) ):
        raise NoTerminalNodesInCFGError()

    num_x_threads = rng.randint(1, x_threads) 
    num_y_threads = rng.randint(1, y_threads)
    num_z_threads = rng.randint(1, z_threads)
    num_x_workgroups = rng.randint(1, x_workgroups) 
    num_y_workgroups = rng.randint(1, y_workgroups) 
    num_z_workgroups = rng.randint(1, z_workgroups)  

    cfg = CFG(get_jump_relation(instance),
              get_merge_relation(instance),
              get_continue_relation(instance),
              get_entry_block(instance),
              get_regular_blocks(instance),
              get_loop_header_blocks(instance),
              get_selection_header_blocks(instance),
              get_switch_blocks(instance))

    path: Path = cfg.generate_path(rng, path_length)
    path.barrier_blocks = get_barrier_blocks(cfg, path, 40, rng) if include_barriers else set()
    paths: List[Path] = generate_paths(path, cfg, rng, path_length) if use_different_paths else [path]
    num_required_paths = CFG.compute_num_threads(num_x_threads, num_y_threads, num_z_threads) * CFG.compute_num_workgroups(num_x_workgroups, num_y_workgroups, num_z_workgroups)
    paths = [rng.choice(paths) for _ in range(num_required_paths)]

    return cfg.to_string(), cfg.fleshout(paths,
                                         rng, 
                                         seed, 
                                         num_x_threads,
                                         num_y_threads,
                                         num_z_threads,
                                         num_x_workgroups,
                                         num_y_workgroups,
                                         num_z_workgroups, 
                                         include_op_phi) 


def parse_args():
    t = 'This tool fleshes out xml CFG skeletons generated by Alloy.'
    parser = argparse.ArgumentParser(description=t)

    # Required positional argument
    parser.add_argument('xml',
                        help='The xml CFG skeleton generated by Alloy')
    
    # Optional Arguments
    parser.add_argument('--l', type=int, default=MAX_PATH_LENGTH,
                    help='This is the suggested maximum length of the randomly chosen path: '
                            'the path may be extended minimally to make it terminating.'
                    )

    parser.add_argument("--seed", type=int, 
                        help='The seed to use for the PNG. This can be used to reproduce paths. '
                        'To guarantee reproducibility the seed should be paired with the exact same '
                        'path length argument.')
    
    parser.add_argument("--x-threads", type=int, default=1, 
                        help='The maximum number of threads in the x dimension')
    
    parser.add_argument("--y-threads", type=int, default=1, 
                        help='The maximum number of threads in the y dimension')
    
    parser.add_argument("--z-threads", type=int, default=1, 
                        help='The maximum number of threads in the z dimension')
    
    parser.add_argument("--x-workgroups", type=int, default=1, 
                        help='The maximum number of workgroups in the x dimension')
    
    parser.add_argument("--y-workgroups", type=int, default=1, 
                        help='The maximum number of workgroups in the y dimension')
    
    parser.add_argument("--z-workgroups", type=int, default=1, 
                        help='The maximum number of workgroups in the z dimension')
    
    parser.add_argument("--op-phi", action='store_true',
                        help='Use OpPhi instructions for output and directions index variables')
    
    parser.add_argument("--simple-barriers", action='store_true', 
                        help='Add barriers along a single path. If there are multiple threads, all threads follow that same path.')

    args = parser.parse_args()

    if not args.seed:
        args.seed = random.randrange(0, sys.maxsize)
    return args

def main():
    args = parse_args()
    print(f"Fleshing with seed {args.seed}")
    asm = fleshout(args.xml, path_length=args.l, seed=args.seed, x_threads=args.x_threads, y_threads=args.y_threads, z_threads=args.z_threads, x_workgroups=args.x_workgroups, y_workgroups=args.y_workgroups, z_workgroups=args.z_workgroups, include_barriers=args.simple_barriers, include_op_phi=args.op_phi)
    print('\n')
    print(asm[0])

    print('\n')
    print(asm[1])

    
if __name__ == "__main__":
    main()
