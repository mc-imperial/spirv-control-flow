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
import subprocess
import sys

from argparse import ArgumentParser
from pathlib import Path
from typing import Optional

from amber_result import AmberResult

logger = logging.getLogger(__name__)

ANDROID_TEMP_DIR: str = "/data/local/tmp/"


def get_adb_prefix(android_serial: Optional[str]):
    return ["adb"] if android_serial is None else ["adb", "-s", android_serial]


def execute_amber_on_android(android_serial: Optional[str], amber_file_path: Path) -> AmberResult:
    # Push the Amber file to the device
    cmd = get_adb_prefix(android_serial) + ["push", amber_file_path, ANDROID_TEMP_DIR + "test.amber"]
    process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if process.returncode != 0:
        logger.error(
            f'Error pushing Amber file to Android device: stopping. Return code: {process.returncode}, stdout: '
            f'{process.stdout}, stderr: {process.stderr}')
        # If it wasn't possible to push a file to the Android device, this almost certainly means that something major
        # is wrong, e.g. the device is not connected, so it makes sense to exit the testing process completely.
        sys.exit(1)

    amber_command = "./amber -d -t spv1.3 -v 1.1 test.amber"
    cmd = get_adb_prefix(android_serial) + ["shell", f"cd {ANDROID_TEMP_DIR} && " + amber_command]
    process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    result = AmberResult(filename=amber_file_path,
                         return_code=process.returncode,
                         stdout=process.stdout,
                         stderr=process.stderr)

    # Rename the Amber file on the device. This is useful so that if something goes wrong there is an Amber file on the
    # device to inspect. However, it is preferable to rename the Amber file to a name that indicates it is an old file,
    # to avoid accidentally running a newer test on what is actually an old file.
    cmd = get_adb_prefix(android_serial) + ["shell", "mv", ANDROID_TEMP_DIR + "test.amber",
                                            ANDROID_TEMP_DIR + "last_test.amber"]
    process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if process.returncode != 0:
        logger.error(
            f'Error renaming Amber file on Android device: stopping. Return code: {process.returncode}, stdout: '
            f'{process.stdout}, stderr: {process.stderr}')
        # Again, this means that something drastic has happened, so it does not make sense to continue.
        sys.exit(1)

    return result


def main():
    parser = ArgumentParser(description="Run an Amber file on an Android device")

    parser.add_argument('amber_file', help="The Amber file to be executed.", type=Path)
    parser.add_argument('--android_serial',
                        help='Serial number of the Android devices to be used.',
                        type=str)

    args = parser.parse_args()
    print(execute_amber_on_android(android_serial=args.android_serial,
                                   amber_file_path=args.amber_file))


if __name__ == "__main__":
    main()
