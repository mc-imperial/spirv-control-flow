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

import sys
import xml.etree.ElementTree as elementTree

from typing import Dict, List, Set


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
                 entry_block: str, regular_blocks: Set[str],
                 loop_header_blocks: Set[str],
                 selection_header_blocks: Set[str],
                 switch_blocks: Set[str]):
        self.jump_relation = jump_relation
        self.merge_relation = merge_relation
        self.continue_relation = continue_relation
        self.entry_block = entry_block
        self.regular_blocks = regular_blocks
        self.loop_header_blocks = loop_header_blocks
        self.selection_header_blocks = selection_header_blocks
        self.switch_blocks = switch_blocks
        self.label_to_id: Dict[str, int] = {}
        self.next_id = self.ENTRY_BLOCK_ID
        assert len(self.loop_header_blocks.intersection(self.selection_header_blocks)) == 0
        assert len(self.loop_header_blocks.intersection(self.switch_blocks)) == 0
        assert self.switch_blocks.issubset(self.selection_header_blocks)
        self.structured_jump_relation: Dict[str, List[str]] = self.compute_structured_jump_relation()
        self.structured_back_edges: Dict[str, Set[str]] = self.compute_back_edges()
        self.topological_ordering: List[str] = self.compute_topological_ordering()

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
        queue: List[str] = []
        for block in in_degree:
            if in_degree[block] == 0:
                queue.append(block)

        # Pop blocks from the queue, adding them to the sorted order and decreasing the
        # in-degrees of their successors. A successor who's in-degree becomes zero
        # gets added to the queue.

        while len(queue) > 0:
            block: str = queue.pop(0)
            result.append(block)
            if block in self.structured_jump_relation:
                for successor in self.structured_jump_relation[block]:
                    if block in self.structured_back_edges and successor in self.structured_back_edges[block]:
                        continue
                    assert in_degree[successor] > 0
                    in_degree[successor] -= 1
                    if in_degree[successor] == 0:
                        queue.append(successor)

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

    def get_block_id(self, label: str) -> str:
        if label not in self.label_to_id:
            self.label_to_id[label] = self.next_id
            self.next_id += 1
        return str(self.label_to_id[label])

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


def main():
    if len(sys.argv) != 2:
        print("Usage: " + sys.argv[0] + " <xml file>")
        sys.exit(1)
    tree = elementTree.parse(sys.argv[1])

    alloy = tree.getroot()
    assert alloy.tag == "alloy"
    assert len(alloy) == 1
    instance = alloy[0]
    assert instance.tag == "instance"

    cfg = CFG(get_jump_relation(instance),
              get_merge_relation(instance),
              get_continue_relation(instance),
              get_entry_block(instance),
              get_regular_blocks(instance),
              get_loop_header_blocks(instance),
              get_selection_header_blocks(instance),
              get_switch_blocks(instance))
    print(cfg.to_string())


if __name__ == "__main__":
    main()
