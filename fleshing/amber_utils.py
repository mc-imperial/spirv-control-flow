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

import fleshing_runner
import os
import pathlib
import shutil

from argparse import ArgumentParser


def get_amber_files(folder):
    for root, _, files in os.walk(folder):
        for file in files:
            if file.endswith(".amber"):
                yield os.path.join(root, file)


def copy_amber_files(src_folder, dst_folder):
    for test_folder in fleshing_runner.get_test_folders(src_folder):
        full_test_folder_path = os.path.join(src_folder, test_folder)
        for file in os.listdir(full_test_folder_path):
            full_file_path = os.path.join(full_test_folder_path, file)
            if not os.path.isfile(full_file_path) or not file.endswith(".amber"):
                continue
            new_file_name = os.path.join(dst_folder, test_folder + "_" + file)
            shutil.copyfile(full_file_path, new_file_name)


def find_path(amber_file):
    with open(amber_file, 'r') as f:
        lines = f.readlines()
    path_idx = -1
    for idx, line in enumerate(lines):
        if line == "; Follow the path:\n":
            path_idx = idx + 1
            break
    assert path_idx != -1
    path = lines[path_idx].split(';')[1][1:]
    return path


def delete_file(file):
    os.remove(file)


def deduplicate(amber_folder):
    paths = {}
    duplicate_count = 0
    for file in get_amber_files(amber_folder):
        file_path = pathlib.PurePath(file)
        parent_name = file_path.parent.stem
        path = find_path(file_path)
        
        if parent_name not in paths:
            paths[parent_name] = set()
        
        if path in paths[parent_name]:
            duplicate_count += 1
            print(f"deleting file {file_path}")
            delete_file(file_path)
            continue
        paths[parent_name].add(path)


def parse_args():
    t = "Useful amber related functions"
    parser = ArgumentParser(description=t)
    subparsers = parser.add_subparsers(dest='subparser_name')

    copy_parser = subparsers.add_parser("copy")
    copy_parser.add_argument("src_folder")
    copy_parser.add_argument("dst_folder")
    
    deduplicate_parser = subparsers.add_parser("deduplicate")
    deduplicate_parser.add_argument("folder")

    args = parser.parse_args()
    return args


def main():
    args = parse_args()
    
    if args.subparser_name == "copy":
        copy_amber_files(args.src_folder, args.dst_folder)
    elif args.subparser_name == "deduplicate":
        deduplicate(args.folder)
    else:
        print(f"Invalid command: {args.subparser_name}")


if __name__ == "__main__":
    main()