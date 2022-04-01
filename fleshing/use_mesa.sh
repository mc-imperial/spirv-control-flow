#!/bin/bash
# This script sets the environment variables for the mesa version defined by MESA_VERSION
echo "Setting up environment for $MESA_VERSION"
export LD_LIBRARY_PATH=$MESA_WORK_DIR/$MESA_VERSION-all-libs:$LD_LIBRARY_PATH
export LIBGL_DRIVERS_PATH=$MESA_WORK_DIR/$MESA_VERSION-all-libs
export VK_ICD_FILENAMES=$MESA_WORK_DIR/$MESA_VERSION-install/share/vulkan/icd.d/intel_icd.x86_64.json
source $VULKAN_SDK/../setup-env.sh
