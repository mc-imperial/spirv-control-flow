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

import cProfile
import fleshout
import io
import logging
import os
import pstats
import random
import sys
import time
import traceback

from argparse import ArgumentParser

logger = logging.getLogger(__name__)


def profile(func):
    def wrapper(*args, **kwargs):
        pr = cProfile.Profile()
        pr.enable()
        retval = func(*args, **kwargs)
        pr.disable()
        s = io.StringIO()
        sortby = pstats.SortKey.CUMULATIVE
        ps = pstats.Stats(pr, stream=s).sort_stats(sortby)
        logger.info(ps.print_stats())
        logger.info(s.getvalue())
        return retval

    return wrapper


def get_test_folders(xml_folder):
    return [test_folder for test_folder in next(os.walk(xml_folder))[1]]

@profile
def run_fleshing(xml_folder, seeds, x_threads=1, y_threads=1, z_threads=1, x_workgroups=1, y_workgroups=1, z_workgroups=1, include_barriers=False, include_op_phi=False):
    configure_logging()
    start_time = time.perf_counter()
    files_with_errors = []
    files_with_terminal_node_issues = []
    num_xml_files_processed = 0
    num_amber_files_produced = 0
    for test_folder in get_test_folders(xml_folder):
        test_file = os.path.join(xml_folder, test_folder, "test_0.xml")

        if not os.path.isfile(test_file):
            logger.info(f"Skipping {test_file} as it doesn't exist")
            continue

        for seed in seeds:
            logger.info(f"Fleshing {test_file} with seed {seed}")
            try:
                _, amber_program_str = fleshout.fleshout(test_file, seed=seed, x_threads=x_threads, y_threads=y_threads, z_threads=z_threads, x_workgroups=x_workgroups, y_workgroups=y_workgroups, z_workgroups=z_workgroups, include_barriers=include_barriers, include_op_phi=include_op_phi)
                amber_file_path = test_file.replace(".xml", f"_{seed}") + ".amber"
                with open(amber_file_path, 'w') as amber_file:
                    amber_file.write(amber_program_str)
                num_amber_files_produced += 1
            except (fleshout.NoTerminalNodesInCFGError, fleshout.AllTerminalNodesUnreachableError):
                files_with_terminal_node_issues.append(test_file)
                logger.error(traceback.format_exc())
                logger.error(test_file)
                logger.error(seed)
                break # No point trying a different seed
            except (KeyError, AssertionError, fleshout.TerminalNodesUnreachableFromCurrentNodeError):
                files_with_errors.append(test_file)
                logger.error(traceback.format_exc())
                logger.error(test_file)
                logger.error(seed)
        num_xml_files_processed += 1

    elapsed_time = time.perf_counter() - start_time
    logger.info(f"Found {len(files_with_terminal_node_issues)} CFGs have either no terminal nodes or all terminal nodes are unreachable")
    logger.info(f"Found {len(files_with_errors)} errors when generating amber files")
    logger.info(f"Produced {num_amber_files_produced} amber files from {num_xml_files_processed} xml files")
    logger.info(f"Fleshing executed in: {elapsed_time} seconds")


def parse_args():
    t = "This tool fleshes out a folder of xml CFG skeletons generated by Alloy. " \
        "Amber files are generated in the same directory as the xml file they are generated from."
    parser = ArgumentParser(description=t)

    parser.add_argument('xml_folder',
                        help='The folder containing xml skeletons generated by Alloy. \
                            The xml skeletons should be in a file called test_0.xml and the folder \
                            containing the xml file should be the name of the skeleton.')
    
    parser.add_argument("--runner-seed", type=int, 
                        help='The seed to use for the PNG in the runner. This can be used to reproduce a particular '
                        'fleshing run, however it does not affect the seeds used when fleshing individual files. To '
                        'guarantee reproducibility the seed should be paired with the exact same fleshing seeds.')

    seeds_or_repeat_group = parser.add_mutually_exclusive_group(required=False)

    seeds_or_repeat_group.add_argument("--fleshing-seeds", nargs="+", type=int, 
                        help='The seeds used for fleshing. These can be used to reproduce the same paths in the flesher.')
    
    seeds_or_repeat_group.add_argument("--repeats", type=int, help='The number of times fleshing is run per xml file.')

    parser.add_argument("--x-threads", type=int, default=1, 
                        help='The maximum number of threads in the x dimension')
    
    parser.add_argument("--y-threads", type=int, default=1, 
                        help='The maximum number of threads in the y dimension')
    
    parser.add_argument("--z-threads", type=int, default=1, 
                        help='The maximum number of threads in the z dimension')
    
    parser.add_argument("--x-workgroups", type=int, default=1, 
                        help='The maximum number of workgroups in the x dimension')
    
    parser.add_argument("--y-workgroups", type=int, default=1, 
                        help='The maximum number of workgroups in the y dimension')
    
    parser.add_argument("--z-workgroups", type=int, default=1, 
                        help='The maximum number of workgroups in the z dimension')
    
    parser.add_argument("--op-phi", action='store_true',
                        help='Use OpPhi instructions for output and directions index variables')
    
    parser.add_argument("--simple-barriers", action='store_true', 
                        help='Add barriers along a single path. If there are multiple threads, all threads follow that same path.')

    args = parser.parse_args()

    if not args.runner_seed:
        args.runner_seed = random.randrange(0, sys.maxsize)

    if args.fleshing_seeds is None and args.repeats is None:
        args.repeats = 1

    if args.fleshing_seeds is None:
        args.fleshing_seeds = []
        for _ in range(args.repeats):
            args.fleshing_seeds.append(random.randrange(0, sys.maxsize))
    return args


def configure_logging():
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        fmt='%(asctime)s.%(msecs)03d: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    os.makedirs("logs", exist_ok=True)
    log_filename = f"logs/fleshing_runner_{time.time_ns()}.log"
    file_handler = logging.FileHandler(filename=log_filename)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.info(f"Logging to {log_filename}")


def main():
    args = parse_args()
    xml_folder = os.path.join(os.getcwd(), args.xml_folder)
    logger.info(f"Input folder: {args.xml_folder}")
    logger.info(f"Runner seed: {args.runner_seed}")
    logger.info(f"Fleshing seeds: {args.fleshing_seeds}") 

    logger.info("Fleshing...")
    run_fleshing(xml_folder, args.fleshing_seeds, x_threads=args.x_threads, y_threads=args.y_threads, z_threads=args.z_threads, x_workgroups=args.x_workgroups, y_workgroups=args.y_workgroups, z_workgroups=args.z_workgroups, include_barriers=args.simple_barriers, include_op_phi=args.op_phi)

    logger.info(f"runner seed: {args.runner_seed}")
    logger.info(f"fleshing seeds: {args.fleshing_seeds}")


if __name__ == "__main__":
    main()