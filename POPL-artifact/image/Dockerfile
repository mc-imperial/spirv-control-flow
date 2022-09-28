
# Copyright 2021 The GraphicsFuzz Project Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

FROM ubuntu:18.04

ENV \
  LC_ALL=C.UTF-8 LANG=C.UTF-8

RUN \
  apt-get -qq update && \
  apt-get -y -qq install python3 python3-pip git unzip curl libvulkan1 nano emacs vim moreutils cmake ninja-build default-jre

RUN \
  mkdir -p /data/git /data/fuzzing && \
  touch /data/ROOT && \
  cd /data/git && \
  git clone https://github.com/google/graphicsfuzz.git && \
  cd graphicsfuzz && \
  git checkout 74c729b850f6e5f1663c27c46cea4a5758d05f0b && \
  cd gfauto && \
  ./dev_shell.sh.template

RUN \
  cd /data/git && \
  git clone https://github.com/KhronosGroup/SPIRV-Tools.git && \
  cd SPIRV-Tools && \
  git checkout 939bc02603933200da5e375cb33f3a381472861c && \
  git clone https://github.com/KhronosGroup/SPIRV-Headers external/spirv-headers && \
  cd external/spirv-headers && \
  git checkout faa570afbc91ac73d594d787486bcf8f2df1ace0 && \
  cd ../.. && \
  git clone https://github.com/protocolbuffers/protobuf external/protobuf --branch v3.13.0 --depth 1

RUN \
  mkdir /data/git/SPIRV-Tools/pre-built && \
  cd /data/git/SPIRV-Tools/pre-built && \
  cmake -G Ninja -DSPIRV_BUILD_FUZZER=ON -DSPIRV_SKIP_TESTS=ON -DCMAKE_BUILD_TYPE=Debug .. && \
  cmake --build . --config Debug

RUN \
  mkdir /data/glslang && \
  cd /data/glslang && \
  curl -sSLo glslang.zip https://github.com/google/gfbuild-glslang/releases/download/github%2Fgoogle%2Fgfbuild-glslang%2F159b05708055fdb7cb2f01005d7c35545be6852f/gfbuild-glslang-159b05708055fdb7cb2f01005d7c35545be6852f-Linux_x64_Debug.zip && \
  unzip glslang.zip

RUN \
  echo 'ulimit -S -c 0' >>/etc/profile

COPY fuzz_directory/. /data/fuzzing/

COPY example/. /data/example/

ENV PATH="/data/git/graphicsfuzz/gfauto/.venv/bin:/data/glslang/bin:${PATH}"

RUN \
  ulimit -S -c 0 && \
  cd /data/fuzzing/spirv-fuzz && \
  gfauto_fuzz --spirv_fuzz_iterations 1 --glsl_fuzz_iterations 0 --iteration_seed 0 && \
  rm -rf reports temp log*.txt

RUN \
  ulimit -S -c 0 && \
  cd /data/fuzzing/glsl-fuzz && \
  gfauto_fuzz --spirv_fuzz_iterations 0 --glsl_fuzz_iterations 1 --iteration_seed 0 && \
  rm -rf reports temp log*.txt

COPY full_experimental_data/. /data/full_experimental_data/

ADD ResultData.tgz /data/full_experimental_data/
