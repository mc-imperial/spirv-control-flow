#!/usr/bin/env python

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

import argparse
import glob
import os
import pathlib
import re
import shutil
import subprocess
import sys

from pathlib import Path


class Converter:

    TEMPDIR: str = '.converter'

    def __init__(self,
                 input_dir: Path,
                 output_dir: Path,
                 spirv_as_path: Path,
                 spirv_to_alloy_path: Path):
        self.input_dir: Path = input_dir
        self.output_dir: Path = output_dir
        self.spirv_as_path: Path = spirv_as_path
        self.spirv_to_alloy_path: Path = spirv_to_alloy_path

    def convert_asm_file(self, asm_filename):
        binary_filename = self.TEMPDIR + os.sep + 'temp.spv'
        cmd = [self.spirv_as_path, asm_filename, '-o', binary_filename, '--preserve-numeric-ids']
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

        assembly_text = open(asm_filename, 'r').read()
        pattern = re.compile(r'%(\d+) = OpFunction ')
        matches = re.findall(pattern, assembly_text)
        if len(matches) != 1:
            print(f"Error: there should be exactly one OpFunction instruction in {asm_filename}")
            sys.exit(1)
        function_id = matches[0]
        output_file_prefix = os.sep.join([str(self.output_dir), os.path.splitext(os.path.basename(asm_filename))[0]])
        cmd = [str(self.spirv_to_alloy_path), binary_filename, function_id, output_file_prefix]
        result = subprocess.run(cmd, capture_output=True)

        if result.returncode != 0:
            # Something went wrong
            print("command failed: %s\n\n" % cmd)
            print("return code = %d" % result.returncode)
            print("stdout:\n\n%s\n\n" % result.stdout.decode('utf-8'))
            print("stderr:\n\n%s\n\n" % result.stderr.decode('utf-8'))

        assert result.returncode == 0

        with open(output_file_prefix + '.als', 'w') as output_file:
            output_file.write(result.stdout.decode('utf-8'))

    def doit(self):
        if os.path.exists(self.TEMPDIR):
            shutil.rmtree(self.TEMPDIR)
        os.mkdir(self.TEMPDIR)
        for f in glob.glob(str(self.input_dir) + os.sep + "*.asm"):
            print(f)
            self.convert_asm_file(f)
        shutil.rmtree(self.TEMPDIR)


def main():
    parser = argparse.ArgumentParser('A tool to turn a directory of SPIR-V assembly files into a directory of Alloy '
                                     'files.')
    parser.add_argument("input_dir", help="Input directory containing .asm files; all .asm files in the root of this "
                                          "directory will be converted.", type=Path)
    parser.add_argument("output_dir", help="Output directory to which Alloy files should be stored.", type=Path)
    parser.add_argument("spirv_as_path", help="Path to spirv-as.", type=Path)
    parser.add_argument("spirv_to_alloy_path", help="Path to spirv-to-alloy.", type=Path)
    args = parser.parse_args()
    converter = Converter(input_dir=args.input_dir,
                          output_dir=args.output_dir,
                          spirv_as_path=args.spirv_as_path,
                          spirv_to_alloy_path=args.spirv_to_alloy_path)
    converter.doit()


if __name__ == "__main__":
    main()
