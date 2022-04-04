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

import argparse
import os
import pathlib
import re
import shutil
import subprocess

from pathlib import Path
from typing import Set


class Scraper:

    TEMPDIR: str = '.scrapertemp'

    def __init__(self,
                 output_dir: Path,
                 vk_gl_cts_path: Path,
                 glslang_path: Path,
                 spirv_as_path: Path,
                 spirv_dis_path: Path,
                 spirv_to_alloy_path: Path,
                 skip_validation: bool,
                 alloy_module_prefix: str):
        self.output_dir: Path = output_dir
        self.vk_gl_cts_path: Path = vk_gl_cts_path
        self.glslang_path: Path = glslang_path
        self.spirv_as_path: Path = spirv_as_path
        self.spirv_dis_path: Path = spirv_dis_path
        self.spirv_to_alloy_path: Path = spirv_to_alloy_path
        self.spirv_cache: Set[bytes] = set()
        self.alloy_cache: Set[str] = set()
        self.example_count: int = 0
        self.skip_validation: bool = skip_validation
        self.alloy_module_prefix: str = alloy_module_prefix

    def list_amber_files(self):
        for root, folders, files in os.walk(self.vk_gl_cts_path):
            for filename in folders + files:
                if pathlib.Path(filename).suffix == '.amber':
                    yield os.path.join(root, filename)
        
    def handle_shader(self, amber_filename, glsl_ext, shader_text):
        binary_filename = self.TEMPDIR + os.sep + 'temp.spv'
        assembly_filename = self.TEMPDIR + os.sep + 'dis.asm'
        if glsl_ext is not None:
            tempfilename = self.TEMPDIR + os.sep + 'temp.' + glsl_ext
            cmd = [self.glslang_path, '-V', '--target-env', 'vulkan1.1', tempfilename, '-o', binary_filename]
        else:
            tempfilename = self.TEMPDIR + os.sep + 'temp.asm'
            cmd = [self.spirv_as_path, tempfilename, '-o', binary_filename]

        with open(tempfilename, 'w') as outfile:
            outfile.write(shader_text)
        result = subprocess.run(cmd, capture_output=True)
        if result.returncode != 0:
            # Something went wrong
            print("command failed: %s\n\n" % cmd)
            print("return code = %d" % result.returncode)
            print("stdout:\n\n%s\n\n" % result.stdout.decode('utf-8'))
            print("stderr:\n\n%s\n\n" % result.stderr.decode('utf-8'))
            print(open(tempfilename).read())

        # Check that execution was successful.
        assert result.returncode == 0
        
        with open(binary_filename, 'rb') as binfile:
            temp = binfile.read()
            if temp in self.spirv_cache:
                return
            self.spirv_cache.add(temp)
            cmd = [self.spirv_dis_path, binary_filename, '--raw-id', '-o', assembly_filename]
            result = subprocess.run(cmd, capture_output=True)
            assert result.returncode == 0
            asm = open(assembly_filename, 'r').read()
            pattern = re.compile(r'%(\d+) = OpFunction ')
            for instruction_id in re.findall(pattern, asm):
                alloy_module_prefix = os.sep.join([str(self.alloy_module_prefix), f's{self.example_count:03}'])
                cmd = [self.spirv_to_alloy_path, binary_filename, instruction_id, alloy_module_prefix]
                if self.skip_validation:
                    cmd += ["skip-validation"]
                result = subprocess.run(cmd, capture_output=True)

                if result.returncode != 0:
                    # Something went wrong
                    print("command failed: %s\n\n" % cmd)
                    print("return code = %d" % result.returncode)
                    print("stdout:\n\n%s\n\n" % result.stdout.decode('utf-8'))
                    print("stderr:\n\n%s\n\n" % result.stderr.decode('utf-8'))

                assert result.returncode == 0
                stdout_string = result.stdout.decode('utf-8')
                maybe_cache_entry = '\n'.join(stdout_string.split('\n')[1:])
                if maybe_cache_entry in self.alloy_cache:
                    continue
                self.alloy_cache.add(maybe_cache_entry)
                output_file_prefix = os.sep.join([str(self.output_dir), f's{self.example_count:03}'])
                with open(output_file_prefix + '.als', 'w') as output_file:
                    output_file.write('// ' + amber_filename[len(str(self.vk_gl_cts_path)):] + '\n')
                    output_file.write(stdout_string)
                    self.example_count += 1

    def doit(self):
        if os.path.exists(self.TEMPDIR):
            shutil.rmtree(self.TEMPDIR)
        os.mkdir(self.TEMPDIR)
        for f in self.list_amber_files():
            print(f)
            with open(f, 'r') as amberfile:
                lines = amberfile.readlines()
                index = 0
                while index < len(lines):
                    components = re.split(r'\s|\[|]', lines[index].strip())
                    if len(components) > 1 and components[0] == 'SHADER' and 'PASSTHROUGH' not in components:
                        if 'fragment' in components:
                            glsl_ext = 'frag'
                        elif 'vertex' in components:
                            glsl_ext = 'vert'
                        elif 'geometry' in components:
                            glsl_ext = 'geom'
                        elif 'compute' in components:
                            glsl_ext = 'comp'
                        elif 'tessellation_control' in components:
                            glsl_ext = 'tesc'
                        elif 'tessellation_evaluation' in components:
                            glsl_ext = 'tese'
                        else:
                            assert False
                        if 'GLSL' in components:
                            pass
                        elif 'SPIRV-ASM' in components:
                            glsl_ext = None
                        else:
                            assert False
                        index += 1
                        shader_text = ""
                        while not lines[index].startswith('END'):
                            shader_text += lines[index]
                            index += 1
                    elif len(components) > 1 and lines[index][0] == '[' and 'shader' in components and\
                            'passthrough' not in components:
                        if 'fragment' in components:
                            glsl_ext = 'frag'
                        elif 'vertex' in components:
                            glsl_ext = 'vert'
                        elif 'geometry' in components:
                            glsl_ext = 'geom'
                        elif 'compute' in components:
                            glsl_ext = 'comp'
                        elif 'tessellation' in components and 'control' in components:
                            glsl_ext = 'tesc'
                        elif 'tessellation' in components and 'evaluation' in components:
                            glsl_ext = 'tese'
                        else:
                            assert False
                        if 'spirv' in components:
                            glsl_ext = None
                        index += 1
                        shader_text = ""
                        while not lines[index].startswith('['):
                            shader_text += lines[index]
                            index += 1
                    else:
                        index += 1
                        continue
                    index += 1
                    self.handle_shader(f, glsl_ext, shader_text)
        shutil.rmtree(self.TEMPDIR)


def main():
    parser = argparse.ArgumentParser('A tool to scrape shaders from the Vulkan CTS and generate corresponding Alloy '
                                     'files.')
    parser.add_argument("output_dir", help="Output directory to which Alloy files should be stored.", type=Path)
    parser.add_argument("alloy_module_prefix")
    parser.add_argument("vk_gl_cts_path", help="Path to VK-GL-CTS checkout.", type=Path)
    parser.add_argument("glslang_path", help="Path to glslangValidator.", type=Path)
    parser.add_argument("spirv_as_path", help="Path to spirv-as.", type=Path)
    parser.add_argument("spirv_dis_path", help="Path to spirv-dis.", type=Path)
    parser.add_argument("spirv_to_alloy_path", help="Path to spirv-to-alloy.", type=Path)

    parser.add_argument("--skip-validation", required=False, default=False, action='store_true',
        help="This options skips generating the validCFG/Valid check in the resulting .als files.")
    args = parser.parse_args()
    scraper = Scraper(output_dir=args.output_dir,
                      vk_gl_cts_path=args.vk_gl_cts_path,
                      glslang_path=args.glslang_path,
                      spirv_as_path=args.spirv_as_path,
                      spirv_dis_path=args.spirv_dis_path,
                      spirv_to_alloy_path=args.spirv_to_alloy_path,
                      skip_validation=args.skip_validation,
                      alloy_module_prefix=args.alloy_module_prefix)
    scraper.doit()


if __name__ == "__main__":
    main()
