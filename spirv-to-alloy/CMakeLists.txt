# Copyright 2021 The SPIR-V Control Flow Project Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

cmake_minimum_required(VERSION 3.13)

project(spirv-to-alloy
    VERSION 1.0
    DESCRIPTION "SPIR-V to Alloy"
    LANGUAGES CXX)

set(
    SPIRV_TO_ALLOY_SPIRV_HEADERS_REPO_DIR
    ${CMAKE_CURRENT_SOURCE_DIR}/third_party/SPIRV-Headers
    CACHE
    PATH
    "Path to a https://github.com/KhronosGroup/SPIRV-Headers repo.")

set(
    SPIRV_TO_ALLOY_SPIRV_TOOLS_REPO_DIR
    ${CMAKE_CURRENT_SOURCE_DIR}/third_party/SPIRV-Tools/SPIRV-Tools
    CACHE
    PATH
    "Path to a https://github.com/KhronosGroup/SPIRV-Tools repo.")

# Set some global compiler flags.
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

add_subdirectory(third_party/SPIRV-Tools)

add_subdirectory(src/spirv_to_alloy)
