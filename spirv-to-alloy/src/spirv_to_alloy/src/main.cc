// Copyright 2021 The SPIRV-Control Flow Project Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

#include <cerrno>
#include <cinttypes>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <memory>
#include <string>
#include <vector>

#include "source/opt/build_module.h"
#include "source/opt/ir_context.h"

namespace {

std::vector<char> ReadBinaryFile(const std::string &input_file) {
  std::ifstream file(input_file, std::ios::binary);
  std::vector<char> contents((std::istreambuf_iterator<char>(file)),
                             (std::istreambuf_iterator<char>()));
  return contents;
}

void CLIMessageConsumer(spv_message_level_t level, const char *,
                        const spv_position_t &position, const char *message) {
  switch (level) {
  case SPV_MSG_FATAL:
  case SPV_MSG_INTERNAL_ERROR:
  case SPV_MSG_ERROR:
    std::cerr << "error: line " << position.index << ": " << message
              << std::endl;
    break;
  case SPV_MSG_WARNING:
    std::cout << "warning: line " << position.index << ": " << message
              << std::endl;
    break;
  case SPV_MSG_INFO:
    std::cout << "info: line " << position.index << ": " << message
              << std::endl;
    break;
  default:
    break;
  }
}

uint32_t LogBase2(uint32_t arg) {
  assert(arg != 0 && "Undefined");
  uint32_t result = 0;
  arg >>= 1;
  while(arg != 0) {
    result++;
    arg >>= 1;
  }
  return result;
}

} // namespace

void print_usage_warning(const char **argv) {
  std::cerr << "Usage: " << argv[0] << " <spirv-binary> <function-id> <alloy-module-name> [skip-validation]" << std::endl;
}

int main(int argc, const char **argv) {

  if (argc < 4 || argc > 5) {
    print_usage_warning(argv);
    return 1;
  }

  bool skip_validation = false;
  if (argc == 5) {
    if (std::string(argv[4]).compare(std::string("skip-validation")) != 0) {
      print_usage_warning(argv);
      return 1;
    }
    skip_validation = true;
  }

  std::string input_filename(argv[1]);
  std::string alloy_module_name(argv[3]);

  char *endptr;
  errno = 0;
  int64_t function_id = std::strtol(argv[2], &endptr, 10);
  if (errno != 0 || endptr == argv[2] || function_id <= 0) {
    std::cerr << "'" << argv[2] << "' must be a positive integer" << std::endl;
    return 1;
  }

  std::vector<char> input_data = ReadBinaryFile(input_filename);

  // Assumes little endian
  uint32_t major = static_cast<uint32_t>(input_data[6]);
  uint32_t minor = static_cast<uint32_t>(input_data[5]);

  spv_target_env env;

  assert(major == 1);
  switch (minor) {
  case 0:
    env = SPV_ENV_UNIVERSAL_1_0;
    break;
  case 1:
    env = SPV_ENV_UNIVERSAL_1_1;
    break;
  case 2:
    env = SPV_ENV_UNIVERSAL_1_2;
    break;
  case 3:
    env = SPV_ENV_UNIVERSAL_1_3;
    break;
  case 4:
    env = SPV_ENV_UNIVERSAL_1_4;
    break;
  case 5:
    env = SPV_ENV_UNIVERSAL_1_5;
    break;
  case 6:
    env = SPV_ENV_UNIVERSAL_1_6;
    break;
  default:
    std::cerr << "Unknown SPIR-V minor version: " << minor << std::endl;
    assert(false);
    return 1;
  }

  std::unique_ptr<spvtools::opt::IRContext> ir_context =
      spvtools::BuildModule(env, CLIMessageConsumer,
                            reinterpret_cast<uint32_t *>(input_data.data()),
                            input_data.size() / sizeof(uint32_t));
  if (ir_context == nullptr) {
    std::cerr << "Error building module" << std::endl;
    return 1;
  }

  spvtools::opt::Function *target_function = nullptr;
  for (auto &function : *ir_context->module()) {
    if (function.result_id() == function_id) {
      target_function = &function;
      break;
    }
  }
  if (target_function == nullptr) {
    std::cerr << "Target function " << function_id << " was not found"
              << std::endl;
    return 1;
  }

  std::string blocks;
  std::string headers;
  std::string loop_headers;
  std::string switch_headers;
  std::string entry_point;
  std::string merge_edges;
  std::string continue_edges;
  std::string jump_edges;
  size_t num_blocks = 0;

  std::unordered_map<uint32_t, uint32_t> block_mapping;
  uint32_t count = 1;
  for (auto &block : *target_function) {
    block_mapping.emplace(block.id(), count);
    count++;
  }

  uint32_t max_switch_targets = 0;

  uint32_t num_exit_blocks = 0;
  uint32_t num_jump_edges = 0;

  for (auto &block : *target_function) {
    num_blocks++;
    if (!blocks.empty()) {
      blocks += ", ";
    }
    std::string block_string("b" + std::to_string(block_mapping.at(block.id())));
    blocks += block_string;
    if (entry_point.empty()) {
      // This is the first block; note that it is the entry point
      entry_point += block_string;
    }
    if (block.GetMergeInst() != nullptr) {
      // This is a loop or selection header
      if (!headers.empty()) {
        headers += " + ";
      }
      headers += block_string;
      if (!merge_edges.empty()) {
        merge_edges += "         + ";
      }
      merge_edges += "(" + block_string + " -> b" + std::to_string(block_mapping.at(block.MergeBlockId())) + ")\n";
      if (block.IsLoopHeader()) {
        if (!loop_headers.empty()) {
          loop_headers += " + ";
        }
        loop_headers += block_string;
        if (!continue_edges.empty()) {
          continue_edges += "         + ";
        }
        continue_edges += "(" + block_string + " -> b" + std::to_string(block_mapping.at(block.ContinueBlockId())) + ")\n";
      }
      if (block.terminator()->opcode() == SpvOpSwitch) {
        // This loop/selection header is also a switch header
        if (!switch_headers.empty()) {
          switch_headers += " + ";
        }
        switch_headers += block_string;
      }
    } else if (block.terminator()->opcode() == SpvOpSwitch) {
      std::cerr << "Found OpSwitch in non-header block" << std::endl;
      return 1;
    }
    switch (block.terminator()->opcode()) {
    case SpvOpBranch:
      num_jump_edges++;
      if (!jump_edges.empty()) {
        jump_edges += "         + ";
      }
      jump_edges += "(" + block_string + " -> (0" + " -> b" + std::to_string(block_mapping.at(block.terminator()->GetSingleWordInOperand(0))) + "))\n";
      break;
    case SpvOpBranchConditional:
      num_jump_edges += 2;
      if (!jump_edges.empty()) {
        jump_edges += "         + ";
      }
      jump_edges += "(" + block_string + " -> ((0" + " -> b" + std::to_string(block_mapping.at(block.terminator()->GetSingleWordInOperand(1))) + ")"
          + " + (1" + " -> b" + std::to_string(block_mapping.at(block.terminator()->GetSingleWordInOperand(2))) + ")))\n";
      break;
    case SpvOpSwitch: {
      if (!jump_edges.empty()) {
        jump_edges += "         + ";
      }
      jump_edges += "(" + block_string + " -> ((0" + " -> b" +
              std::to_string(block_mapping.at(
                  block.terminator()->GetSingleWordInOperand(1))) +
              ")";
      uint32_t num_targets = 1;
      for (uint32_t i = 3; i < block.terminator()->NumInOperands(); i += 2) {
        num_targets++;
        jump_edges += " + (" + std::to_string(i / 2) + " -> b" +
                std::to_string(block_mapping.at(
                    block.terminator()->GetSingleWordInOperand(i))) +
                ")";
      }
      jump_edges += "))\n";
      max_switch_targets = std::max(max_switch_targets, num_targets);
      num_jump_edges += num_targets;
      break;
    }
    case SpvOpReturn:
    case SpvOpReturnValue:
    case SpvOpKill:
    case SpvOpUnreachable:
    case SpvOpTerminateInvocation:
      // No edges
      num_exit_blocks++;
      break;
    default:
      std::cerr << "Unknown block terminator: " << block.terminator()->opcode() << std::endl;
      return 1;
    }
  }
  std::cout << "module " << alloy_module_name << std::endl;
  std::cout << "open AlloyModel/StructuredDominanceCFG as validCFG\n";
  std::cout << "pred sampleCFG {" << std::endl;
  std::cout << "  // #blocks:      " << num_blocks << std::endl;
  std::cout << "  // #exit blocks: " << num_exit_blocks << std::endl;
  std::cout << "  // #jumps:       " << num_jump_edges << std::endl;
  std::cout << "  some disj " + blocks + " : Block {" << std::endl;
  std::cout << "    EntryBlock = " << entry_point << std::endl;
  std::cout << "    HeaderBlock = " << (headers.empty() ? "none" : headers) << std::endl;
  std::cout << "    LoopHeader = " << (loop_headers.empty() ? "none" : loop_headers) << std::endl;
  std::cout << "    SwitchBlock = " << (switch_headers.empty() ? "none" : switch_headers) << std::endl;
  if (jump_edges.empty()) {
    std::cout << "    no branch" << std::endl;
  } else {
    std::cout << "    branch = " << jump_edges;
  }
  if (merge_edges.empty()) {
    std::cout << "    no merge" << std::endl;
  } else {
    std::cout << "    merge = " << merge_edges;
  }
  if (continue_edges.empty()) {
    std::cout << "    no continue" << std::endl;
  } else {
    std::cout << "    continue = " << continue_edges;
  }
  std::cout << "  }" << std::endl;
  std::cout << "}" << std::endl;

  std::string validation_check("&& validCFG/Valid ");
  if (skip_validation) {
      validation_check = "";
  }

  std::cout << "run { sampleCFG " << validation_check << "} for " << std::to_string(num_blocks) << " Block";
  if (max_switch_targets > 4) {
    std::cout << ", " << max_switch_targets << " seq";
  }
  std::cout << std::endl;
  if (max_switch_targets > 7) {
    std::cout << ", " << LogBase2(max_switch_targets) + 2 << " int";
  }
  return 0;
}
