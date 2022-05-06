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

# This scripts copies all needed .so files into a MESA_VERSION specific lib directory
echo "Copying from $MESA_WORK_DIR/$MESA_VERSION-install and $MESA_WORK_DIR/drm-install into $MESA_VERSION-all-libs"
mkdir -p $MESA_WORK_DIR/$MESA_VERSION-all-libs
for f in `find $MESA_WORK_DIR/$MESA_VERSION-install $MESA_WORK_DIR/drm-install -name "*.so"`
do
  cp $f $MESA_WORK_DIR/$MESA_VERSION-all-libs
done
