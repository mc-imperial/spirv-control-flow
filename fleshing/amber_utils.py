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
import statistics

from argparse import ArgumentParser
from pathlib import Path
from typing import Dict, FrozenSet, Set, Tuple


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


def path_stats(amber_folder) -> Tuple[float, float, int, int, float, float, int]:
    all_paths: Dict[str, FrozenSet[str]] = {}
    barriers_in_file: Dict[str, int] = {}
    for file in get_amber_files(amber_folder):
        paths: FrozenSet[str] = find_paths(file)
        all_paths[str(file)] = paths
        barriers_in_file[str(file)] = sum([len(get_barrier_blocks(path)) for path in paths])
    
    lengths = [len(paths) for paths in all_paths.values()]
    return statistics.mean(lengths), statistics.median(lengths), max(lengths), len(all_paths), statistics.mean(barriers_in_file.values()), statistics.median(barriers_in_file.values()), max(barriers_in_file.values())


def get_barrier_blocks(path: str) -> Set[str]:
    blocks = path.split(" ")
    return set(block for block in blocks if "b(" in block)


def find_paths(amber_file) -> FrozenSet[str]:
    paths = set()
    with open(amber_file, 'r') as f:
        lines = f.readlines()

    for idx, line in enumerate(lines):
        if "; unique path #" in line:
            path = lines[idx].split(':')[1][1:]
            paths.add(path)
    assert len(paths) > 0
    return frozenset(paths)


def delete_file(file):
    os.remove(file)


def deduplicate(amber_folder):
    all_paths: Dict[str, Set[str]] = {}
    duplicate_count = 0
    for file in get_amber_files(amber_folder):
        file_path = pathlib.PurePath(file)
        parent_name = file_path.parent.stem
        paths: FrozenSet[str] = find_paths(file_path)
        
        if parent_name not in all_paths:
            all_paths[parent_name] = set()
        
        if paths in all_paths[parent_name]:
            duplicate_count += 1
            print(f"deleting file {file_path}")
            delete_file(file_path)
            continue
        all_paths[parent_name].add(paths)
    print(f"Removed {duplicate_count} paths in total")


def extract_asm(amber_file: Path) -> str:
    with open(amber_file, 'r') as f:
        lines = f.read()
    start_idx = lines.find('; SPIR-V')
    end_idx = lines.find('END')
    return lines[start_idx:end_idx]


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