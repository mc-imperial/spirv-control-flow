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

import logging
import os
import subprocess
import time
import traceback

from argparse import ArgumentParser
from pathlib import Path
from typing import Optional

from amber_result import AmberResult
from run_amber_on_android import execute_amber_on_android

logger = logging.getLogger(__name__)


def execute_amber_on_host(amber_path: Path, amber_file_path: Path) -> AmberResult:
    cmd = [amber_path, "-d", "-t", "spv1.3", "-v", "1.1", amber_file_path]
    try:
        process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5)
        return AmberResult(amber_file_path, process.returncode, process.stdout, process.stderr)
    except subprocess.TimeoutExpired as e:
        logger.error(traceback.format_exc())
        logger.error(amber_file_path)
        return AmberResult(amber_file_path, is_timed_out=True)


def execute_amber_folder(amber_exec_path: Path, amber_folder: Path, use_android: bool, android_serial: Optional[str]):
    amber_results = []
    for root, _, files in os.walk(amber_folder):
        for file in files:
            if not file.endswith(".amber"):
                continue
            amber_file_path = Path(os.path.join(root, file))
            logger.info(f"Executing {amber_file_path}")
            res = execute_amber_on_android(android_serial, amber_file_path) \
                if use_android \
                else execute_amber_on_host(amber_exec_path, amber_file_path)
            amber_results.append(res)
            if res.return_code != 0:
                logger.info(res)
    return amber_results


def run(amber_exec_path, amber_folder, use_android: bool, android_serial: Optional[str]):
    configure_logging()

    if use_android:
        logger.info("--android option selected: tests will be run on a connected Android device. The amber executable "
                    "is assumed to be on that device at location /data/local/tmp/amber. The provided amber_path "
                    f"argument, {amber_exec_path}, will be ignored.")

    amber_results = execute_amber_folder(amber_exec_path=amber_exec_path,
                                         amber_folder=amber_folder,
                                         use_android=use_android,
                                         android_serial=android_serial)
    amber_errors = [res for res in amber_results if res.return_code != 0]
    logger.info(f"Executed {len(amber_results)} amber files")

    error_str = ""
    if len(amber_errors) > 0:    
        error_str += " Files with errors:\n"
        for err in amber_errors:
            error_str += f"{err.filename}\n"
    logger.info(f"{len(amber_errors)} errors found during execution.{error_str}")


def parse_args():
    parser = ArgumentParser(description="Run all amber files in a folder")
    
    parser.add_argument('amber_folder', help="Folder containing amber files.", type=Path)
    parser.add_argument('amber_path', help='The absolute path to amber (https://github.com/google/amber)', type=Path)
    parser.add_argument('--android', help='Run tests on an Android device.', action='store_true')
    parser.add_argument('--android_serial',
                        help='Serial number of the Android devices to be used (requires --android).',
                        type=str)

    args = parser.parse_args()
    if args.android_serial is not None and not args.android:
        parser.error("--android_serial requires --android.")
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
    log_filename = f"logs/amber_runner_{time.time_ns()}.log"
    file_handler = logging.FileHandler(filename=log_filename)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.info(f"Logging results to {log_filename}")


def main():
    args = parse_args()    
    run(amber_exec_path=args.amber_path,
        amber_folder=args.amber_folder,
        use_android=args.android,
        android_serial=args.android_serial)


if __name__ == "__main__":
    main()
