#!/usr/bin/env python

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

FROM ubuntu:20.04

ENV \
  LC_ALL=C.UTF-8 LANG=C.UTF-8

SHELL ["/bin/bash", "-c"]

RUN \
  apt-get -qq update && \
  apt-get -y -qq install wget python3 python3-pip git unzip curl moreutils ninja-build libssl-dev


RUN mkdir -p /data/git /data/fuzzing

# Install version of cmake > 3.13
RUN \
  cd /data/git && \
  wget https://github.com/Kitware/CMake/releases/download/v3.24.2/cmake-3.24.2.tar.gz && \
  tar -zxf cmake-3.24.2.tar.gz && \
  cd cmake-3.24.2 && \
  ./bootstrap && \
  make -j 8 && make install

# Install spirv-control-flow repo
RUN \
  cd /data/git && \
  git clone https://github.com/mc-imperial/spirv-control-flow.git && \
  cd spirv-control-flow && \
  git submodule update --init && \
  mkdir spirv-to-alloy/build && \
  cd spirv-to-alloy/build && \
  cmake -G Ninja .. -DCMAKE_BUILD_TYPE=Debug && \
  cmake --build . --config Debug

# Install SPIRV-Tools 
RUN \
  cd /data/git && \
  git clone https://github.com/KhronosGroup/SPIRV-Tools.git && \
  cd SPIRV-Tools && \
  git checkout cc5fca057ec61748e5fbde429adee155c7392510 && \
  python3 utils/git-sync-deps

# Build SPIRV-Tools 
RUN \
  mkdir /data/git/SPIRV-Tools/pre-built && \
  cd /data/git/SPIRV-Tools/pre-built && \
  cmake -G Ninja -DSPIRV_SKIP_TESTS=ON -DCMAKE_BUILD_TYPE=Debug .. && \
  cmake --build . --config Debug -j 8

ENV PATH /data/git/SPIRV-Tools/pre-built/tools:${PATH}

# Install glslang
RUN \
  mkdir /data/glslang && \
  cd /data/glslang && \
  curl -sSLo glslang.zip https://github.com/KhronosGroup/glslang/releases/download/master-tot/glslang-master-linux-Debug.zip && \
  unzip glslang.zip

ENV PATH /data/glslang/bin:${PATH}

# Download Vulkan CTS
RUN \
    cd /data/git && \
    git clone https://github.com/KhronosGroup/VK-GL-CTS.git

RUN \
    cd /data/git/VK-GL-CTS && \
    git checkout 8252a3d3cdd3cc4333c714f225a902e19b2d75d9

# Alloystar deps
ENV DEBIAN_FRONTEND="noninteractive" TZ="Europe/London"
RUN \
    apt-get update && \
    apt-get -y -qq install openjdk-8-jdk openjdk-8-jre ant

# Install Alloystar
ENV JAVA_HOME /usr/lib/jvm/java-8-openjdk-amd64/
RUN \
    cd /data/git && \
    git clone https://github.com/johnwickerson/alloystar.git && \
    cd alloystar && \
    git fetch --prune && \
    git checkout origin/extra_features && \
    ant all

# Install VulkanSDK Deps
RUN \
    apt-get -y -qq install libglm-dev cmake libxcb-dri3-0 libxcb-present0 libpciaccess0 \
    libpng-dev libxcb-keysyms1-dev libxcb-dri3-dev libx11-dev g++ gcc g++-multilib \
    libmirclient-dev libwayland-dev libxrandr-dev libxcb-randr0-dev libxcb-ewmh-dev \
    git python python3 bison libx11-xcb-dev liblz4-dev libzstd-dev python3-distutils \
    qt5-default ocaml-core ninja-build pkg-config libxml2-dev wayland-protocols

# Install VulkanSDK
RUN \
    cd /data && mkdir /data/vulkansdk && \
    wget https://sdk.lunarg.com/sdk/download/1.3.224.1/linux/vulkansdk-linux-x86_64-1.3.224.1.tar.gz && \
    cd /data/ && \
    tar -xzf vulkansdk-linux-x86_64-1.3.224.1.tar.gz -C /data/vulkansdk

# RUN source /data/vulkansdk/1.3.224.1/setup-env.sh
ENV VULKAN_SDK /data/vulkansdk/1.3.224.1/x86_64
ENV PATH ${VULKAN_SDK}/bin:${PATH}
ENV LD_LIBRARY_PATH ${VULKAN_SDK}/lib 
ENV VK_LAYER_PATH	${VULKAN_SDK}/etc/vulkan/explicit_layer.d

# Install SwiftShader
RUN apt-get -y -qq install libxcb1 libxcb1-dev libxcb-shm0-dev
RUN \
  cd /data/git && \
  git clone https://github.com/google/swiftshader.git && \
  cd swiftshader && \
  git checkout d15c42482560fba311e3cac90203438ad972df55

RUN \
  cd /data/git/swiftshader/build && \
  cmake .. && \
  cmake --build . -j8

# Set SwiftShader as the driver
ENV VK_ICD_FILENAMES /data/git/swiftshader/build/Linux/vk_swiftshader_icd.json

# Install Amber
RUN \
  cd /data/git && \
  git clone https://github.com/google/amber.git && \
  cd amber && \
  ./tools/git-sync-deps

RUN \
  cd /data/git/amber && \
  mkdir -p out/Debug && \
  cd out/Debug && \
  cmake -DAMBER_SKIP_TESTS=True -GNinja ../.. && \
  ninja

ENV PATH /data/git/amber/out/Debug/amber:${PATH}
RUN /data/git/amber/out/Debug/amber -V

# Tidy up
RUN mkdir /data/git/spirv-control-flow/VulkanCTS
RUN mkdir -p /data/git/spirv-control-flow/fleshing/test_sets/vulkan_cts/xml
RUN rm /data/vulkansdk-linux-x86_64-1.3.224.1.tar.gz
RUN rm /data/git/cmake-3.24.2.tar.gz

