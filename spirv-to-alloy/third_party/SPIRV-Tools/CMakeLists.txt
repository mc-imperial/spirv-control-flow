# Copyright 2020 The gf-layers Project Authors
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

##
## Project: SPIRV-Tools
##
## Provides target: SPIRV-Tools-opt.
##
if(NOT TARGET SPIRV-Tools-opt)
    if(NOT IS_DIRECTORY ${SPIRV_TO_ALLOY_SPIRV_TOOLS_REPO_DIR})
        message(
            FATAL_ERROR
            "Could not find SPIRV-Tools at ${SPIRV_TO_ALLOY_SPIRV_TOOLS_REPO_DIR}. "
            "Try fetching submodules or set SPIRV_TO_ALLOY_SPIRV_TOOLS_REPO_DIR.")
    endif()
    # Requires SPIRV-Headers.
    if(NOT IS_DIRECTORY ${SPIRV_TO_ALLOY_SPIRV_HEADERS_REPO_DIR})
        message(
            FATAL_ERROR
            "Could not find SPIRV-Headers at ${SPIRV_TO_ALLOY_SPIRV_HEADERS_REPO_DIR}. "
            "Try fetching submodules or set SPIRV_TO_ALLOY_SPIRV_HEADERS_REPO_DIR.")
    endif()

    # The presence of SPIRV-Headers_SOURCE_DIR would normally imply that
    # add_subdirectory(/path/to/SPIRV-Tools/) has been executed.
    # However, SPIRV-Tools does not actually use any targets from SPIRV-Headers;
    # it only uses SPIRV-Headers_SOURCE_DIR. Thus, we can avoid using
    # add_subdirectory(...) by setting this variable.
    set(SPIRV-Headers_SOURCE_DIR ${SPIRV_TO_ALLOY_SPIRV_HEADERS_REPO_DIR})
    add_subdirectory(${SPIRV_TO_ALLOY_SPIRV_TOOLS_REPO_DIR} EXCLUDE_FROM_ALL)
endif()

##
## Target: spirv_to_alloy_spirv_opt
##
## Provides the SPIRV-Tools-opt target with extra headers.
##
add_library(spirv_to_alloy_spirv_opt INTERFACE)

# Targets that link spirv_to_alloy_spirv_opt should get SPIRV-Tools-opt.
# The following command: target_link_libraries(spirv_to_alloy_spirv_opt PUBLIC SPIRV-Tools-opt)
# is not supported by CMake for INTERFACE libraries, but we can achieve it manually:
set_property(
    TARGET spirv_to_alloy_spirv_opt
    APPEND
    PROPERTY INTERFACE_LINK_LIBRARIES
    SPIRV-Tools-opt
)
# We need to add the SPIRV-Tools root (source and binary directories) as
# include paths, because we need to use internal headers from SPIRV-Tools.
# CMake adds variables <PROJECT-NAME>_SOURCE_DIR and <PROJECT-NAME>_BINARY_DIR
# when it sees the project(<PROJECT-NAME> ...) command, so we can use these.
if(NOT spirv-tools_SOURCE_DIR OR NOT spirv-tools_BINARY_DIR)
    message(
        FATAL_ERROR
        "Could not find CMake variables spirv-tools_SOURCE_DIR and/or spirv-tools_BINARY_DIR. "
        "We require access to internal SPIRV-Tools headers, so the full source is required "
        "(as opposed to an installed version of SPIRV-Tools).")
endif()
target_include_directories(
    spirv_to_alloy_spirv_opt
    INTERFACE
    ${spirv-tools_SOURCE_DIR}
    ${spirv-tools_BINARY_DIR})
