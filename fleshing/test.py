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

import amber_utils
import os
import subprocess
import sys

from argparse import ArgumentParser, SUPPRESS
from pathlib import Path

FLESHING_SEEDS = [4146157812055343106, 377640362442442020, 2724190633622417527, 4657734160498974690, 5627702630468474306, 3592584056284402362, 6663908743611393935, 8479204090612807687, 8874160793401512792, 4552655026277917815, 5209811639908745011, 3545828945084118806, 3500628840747955820, 2989646351514237039, 1904810676886634332, 303342002339387206, 3125691367195659943, 7428363805061972677, 6268828976684345804, 5241053766631009287]

def run_cts_scraper(args):
    program_path = os.path.join(os.path.dirname(__file__), "..", "spirv-to-alloy", "scrape-vulkan-cts.py")
    alloy_module_prefix = str(args.path_to_alloy_files)[str(args.path_to_alloy_files).find("fleshing"):]
    print(f"Alloy module prefix: {alloy_module_prefix}")
    scrape_vulkan_cts_cmd = ["python3", program_path, args.path_to_alloy_files, alloy_module_prefix, args.vk_gl_cts_path, args.glslang_path, args.spirv_as_path, args.spirv_dis_path, args.spirv_to_alloy_path]
    if args.skip_validation:
       scrape_vulkan_cts_cmd += ["--skip-validation"]
    
    print(f"Running Vulkan CTS scraper with command: {scrape_vulkan_cts_cmd}")
    scraping_result = subprocess.run(scrape_vulkan_cts_cmd, capture_output=True, text=True)
    if scraping_result.returncode != 0:
        print(scraping_result.stdout)
        print(scraping_result.stderr)
        print("Error running Vulkan CTS Scraper")
        sys.exit(1)
    print(scraping_result.stdout)

def run_xml_generator(args):
    program_path = os.path.join(os.path.dirname(__file__), "..", "isCFGdeemedFeasible.py")
    xml_generator_cmd = ["python3", program_path, "-a", args.path_to_alloy_files, "-x", args.path_to_xml_files, "-c", args.path_to_alloystar]
    if args.memory:
        xml_generator_cmd += ["-m", str(args.memory)]
    if args.solver:
        xml_generator_cmd += ["-s", args.solver]

    print(f"Running xml generation with command: {xml_generator_cmd}")
    xml_generator_result = subprocess.run(xml_generator_cmd, capture_output=True, text=True)
    print(xml_generator_result.stdout)
    print(xml_generator_result.stderr)
    if xml_generator_result.returncode != 0:
        print("Error running xml generation process")
        sys.exit(1)

def generate_xml_files(args):
    run_cts_scraper(args)
    run_xml_generator(args)

def run_fleshing(xml_path, seeds, x_threads=1, y_threads=1, z_threads=1, x_workgroups=1, y_workgroups=1, z_workgroups=1, include_barriers=False, include_op_phi=False):
    program_path = os.path.join(os.path.dirname(__file__), "fleshing_runner.py")
    fleshing_cmd = ["python3", program_path, xml_path, "--fleshing-seeds"] + [str(seed) for seed in seeds] + ["--x-threads", str(x_threads), "--y-threads", str(y_threads), "--z-threads", str(z_threads), "--x-workgroups", str(x_workgroups), "--y-workgroups", str(y_workgroups), "--z-workgroups", str(z_workgroups)]
    if include_barriers:
        fleshing_cmd += ["--simple-barriers"]
    if include_op_phi:
        fleshing_cmd += ["--op-phi"]

    print(f"Running {fleshing_cmd}")
    fleshing_result = subprocess.run(fleshing_cmd, capture_output=True, text=True)
    if fleshing_result.returncode != 0:
        print(fleshing_result.stdout)
        print(fleshing_result.stderr)
        print("Error running fleshing process")
        sys.exit(1)
    print(fleshing_result.stdout)  

def run_amber(amber_path, amber_folder):
    program_path = os.path.join(os.path.dirname(__file__), "amber_runner.py")
    amber_cmd = ["python3", program_path, amber_folder, amber_path]

    print(f"Running {amber_cmd}")
    amber_result = subprocess.run(amber_cmd, capture_output=True, text=True)
    if amber_result.returncode != 0:
        print(amber_result.stdout)
        print(amber_result.stderr)
        print("Error executing amber files")
        sys.exit(1)
    print(amber_result.stdout)  

def run(args):
    if not args.skip_xml_generation:
        print("Generating xml files...")
        generate_xml_files(args)
    else:
        print("Skipping xml generation...")
    
    run_fleshing(args.path_to_xml_files, FLESHING_SEEDS, x_threads=args.x_threads, y_threads=args.y_threads, z_threads=args.z_threads, x_workgroups=args.x_workgroups, y_workgroups=args.y_workgroups, z_workgroups=args.z_workgroups, include_barriers=args.simple_barriers, include_op_phi=args.op_phi)
    amber_utils.deduplicate(args.path_to_xml_files)
    run_amber(args.path_to_amber, args.path_to_xml_files) # amber files are generated in same folder as xml


def parse_args():
    parser = ArgumentParser(add_help=False)
    required = parser.add_argument_group('required arguments')
    optional = parser.add_argument_group('optional arguments')

    # Add back help
    optional.add_argument(
        '-h',
        '--help',
        action='help',
        default=SUPPRESS,
        help='show this help message and exit'
    )

    required.add_argument("--vk_gl_cts_path", required=True, help="Path to VK-GL-CTS checkout.", type=Path)
    required.add_argument("--glslang_path", required=True, help="Path to glslangValidator.", type=Path)
    required.add_argument("--spirv_as_path", required=True, help="Path to spirv-as.", type=Path)
    required.add_argument("--spirv_dis_path", required=True, help="Path to spirv-dis.", type=Path)
    required.add_argument("--spirv_to_alloy_path", required=True, help="Path to spirv-to-alloy.", type=Path)
    required.add_argument('--path_to_alloy_files', required=True, help='The path to the Vulkan CTS .als files folder', type=Path)
    required.add_argument('--path_to_xml_files', required=True, help='The path to the generated instance XML files'),
    required.add_argument('--path_to_alloystar', required=True, help='The Alloy* (https://github.com/johnwickerson/alloystar) packs the RunAlloy tool which allows Alloy run from the command line', type=Path)
    required.add_argument('--path_to_amber', required=True, help='Path to Amber (https://github.com/google/amber)', type=Path)

    optional.add_argument('--memory', type=int, required=False, default = 3, help='Maximum memory in [GB]')
    optional.add_argument('--solver', required=False, default = "sat4j", choices=['sat4j', 'cryptominisat', 'glucose', 'plingeling', 'lingeling', 'minisatprover', 'minisat'], help = 'Constraint/SAT Solver: By default, the pure Java solver "SAT4J" is chosen since it runs on every platform and operating system. If you require faster performance, you can try one of the native solver such as MiniSat or ZChaff.')
    optional.add_argument("--skip-validation", required=False, default=False, action='store_true', help="This options skips generating the validCFG/Valid check in the resulting .als files.")
    optional.add_argument("--skip-xml-generation", required=False, default=False, action='store_true', help="Use xml files located in --path_to_xml_files for testing instead of generating new xml files.")
    optional.add_argument("--x-threads", type=int, default=1, help='Number of threads in the x dimension')
    optional.add_argument("--y-threads", type=int, default=1, help='Number of threads in the y dimension')
    optional.add_argument("--z-threads", type=int, default=1, help='Number of threads in the z dimension')
    optional.add_argument("--x-workgroups", type=int, default=1, help='Number of workgroups in the x dimension')
    optional.add_argument("--y-workgroups", type=int, default=1, help='Number of workgroups in the y dimension')
    optional.add_argument("--z-workgroups", type=int, default=1, help='Number of workgroups in the z dimension')
    optional.add_argument("--op-phi", action='store_true', help='Use OpPhi instructions for output and directions index variables')
    optional.add_argument("--simple-barriers", action='store_true', help='Add barriers along a single path. If there are multiple threads, all threads follow that same path.')

    return parser.parse_args()

def main():
    args = parse_args()
    run(args)

if __name__ == "__main__":
    main()
