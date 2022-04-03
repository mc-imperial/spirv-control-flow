#!/bin/bash

# Copyright 2022 The SPIRV-Control Flow Project Authors
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

# This script sets the environment variables for the mesa version defined by MESA_VERSION
echo "Setting up environment for $MESA_VERSION"
export LD_LIBRARY_PATH=$MESA_WORK_DIR/$MESA_VERSION-all-libs:$LD_LIBRARY_PATH
export LIBGL_DRIVERS_PATH=$MESA_WORK_DIR/$MESA_VERSION-all-libs
export VK_ICD_FILENAMES=$MESA_WORK_DIR/$MESA_VERSION-install/share/vulkan/icd.d/intel_icd.x86_64.json
source $VULKAN_SDK/../setup-env.sh
