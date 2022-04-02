import logging
import os
import subprocess
import time

from argparse import ArgumentParser

logger = logging.getLogger(__name__)

class AmberResult:

    def __init__(self, filename, return_code, stdout, stderr):
        self.filename = filename
        self.return_code = return_code
        self.stdout = stdout
        self.stderr = stderr
    
    def __str__(self):
        success_str = "Success" if self.return_code == 0 else "Failure"
        ret = f"{success_str}: {self.filename}"
        ret += self.stdout
        ret += self.stderr
        return ret

def execute_amber(amber_path, amber_file_path):
    cmd = [amber_path, "-t", "spv1.3", "-v", "1.1", amber_file_path]
    process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return AmberResult(amber_file_path, process.returncode, process.stdout, process.stderr)

def execute_amber_folder(amber_exec_path, amber_folder):
    amber_results = []
    for root, _, files in os.walk(amber_folder):
        for file in files:
            if not file.endswith(".amber"):
                continue
            amber_file_path = os.path.join(root, file)
            res = execute_amber(amber_exec_path, amber_file_path)
            amber_results.append(res)
            if res.return_code != 0:
                logger.info(res)
    return amber_results

def run(amber_exec_path, amber_folder):
    configure_logging()
    
    amber_results = execute_amber_folder(amber_exec_path, amber_folder)
    amber_errors = [res for res in amber_results if res.return_code != 0]
    logger.info(f"Executed {len(amber_results)} amber files")

    error_str = ""
    if len(amber_errors) > 0:    
        error_str += " Files with errors:\n"
        for err in amber_errors:
            error_str += f"{err.filename}\n"
    logger.info(f"{len(amber_errors)} errors found during execution.{error_str}")

def parse_args():
    t = "Run all amber files in a folder"
    parser = ArgumentParser(description=t)
    
    parser.add_argument('amber_folder', help="Folder containing amber files.")
    parser.add_argument('amber_path', help='The absolute path to amber (https://github.com/google/amber)')

    args = parser.parse_args()
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

    file_handler = logging.FileHandler(filename=f"amber_runner_{time.time_ns()}.log")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

def main():
    args = parse_args()    
    run(args.amber_path, args.amber_folder)

if __name__ == "__main__":
    main()