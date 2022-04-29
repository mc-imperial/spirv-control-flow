import amber_utils
import logging
import os
import subprocess
import time

from argparse import ArgumentParser
from pathlib import Path

logger = logging.getLogger(__name__)


# TODO: Could use spirv-val to validate the results. 
def compile_spirv(asm_file: Path, spirv_as: Path) -> Path:
    binary_file = asm_file.replace(".asm", ".spv")
    cmd = [spirv_as, "--target-env", "spv1.3", asm_file, '-o', binary_file]
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        err_string = "SPIR-V compilation failed!\n" \
            f"command: {cmd}\n" \
            f"return code: {result.returncode}\n" \
            f"stdout:\n\n{result.stdout.decode('utf-8')}\n\n" \
            f"stderr:\n\n{result.stderr.decode('utf-8')}\n\n"
        logger.info(err_string)
    assert result.returncode == 0
    logger.info(f"Compiled asm to {binary_file}")
    return binary_file


def spirv_cross_compile(binary_file: Path, cross_compiler: Path, target_lang: str):
    cmd = [cross_compiler, binary_file]
    if target_lang != "glsl":
        cmd += [f"--{target_lang}"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        err_string = "Cross compilation failed!\n" \
            f"command: {cmd}\n" \
            f"return code: {result.returncode}\n" \
            f"stdout:\n\n{result.stdout.decode('utf-8')}\n\n" \
            f"stderr:\n\n{result.stderr.decode('utf-8')}\n\n"
        logger.info(err_string)
    assert result.returncode == 0
    file_extension = target_lang if target_lang != "glsl" else "comp"
    target_lang_file = binary_file.replace(".spv", f".{file_extension}")
    with open(target_lang_file, 'w') as f:
        f.write(result.stdout)
    logger.info(f"cross compiled binary to {target_lang_file}")
    return target_lang_file


def cross_compile(binary_file: Path, cross_compiler: Path, cross_compiler_name: str, target_lang: str) -> Path:
    if cross_compiler_name == "spirv-cross":
        return spirv_cross_compile(binary_file, cross_compiler, target_lang)
    else:
        assert False


def validate_target_lang_output(target_lang_compiler: Path, target_lang: str, target_lang_file: Path):
    cmd = [target_lang_compiler, target_lang_file]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        err_string = f"ERROR: Compilation of {target_lang_file} failed!\n" \
            f"command: {cmd}\n" \
            f"return code: {result.returncode}\n" \
            f"stdout:\n\n{result.stdout}\n\n" \
            f"stderr:\n\n{result.stderr}\n\n"
        logger.info(err_string)
        return False
    return True
    

def run_cross_compilation(amber_folder: Path, spirv_as: Path, cross_compiler: Path, cross_compiler_name: str, target_lang: str, target_lang_compiler: Path):
    configure_logging()
    logger.info(f"Using amber folder: {amber_folder}")

    files_with_compilation_errors = []
    for amber_file in amber_utils.get_amber_files(amber_folder):
        logger.info(f"Cross compiling amber file {amber_file}")
        spirv_asm = amber_utils.extract_asm(amber_file)
        logger.info(f"Extracted:\n{spirv_asm}")
        asm_file = amber_file.replace(".amber", ".asm")
        with open(asm_file, 'w') as f:
            f.write(spirv_asm)
        binary_file = compile_spirv(asm_file, spirv_as)
        target_lang_file = cross_compile(binary_file, cross_compiler, cross_compiler_name, target_lang)
        success = validate_target_lang_output(target_lang_compiler, target_lang, target_lang_file)
        if not success:
            files_with_compilation_errors.append(target_lang_file)
    
    res_str = f"Finished cross compilation. Found {len(files_with_compilation_errors)} compilation errors."
    if len(files_with_compilation_errors) > 0:
        for file in files_with_compilation_errors:
            res_str += f"\n{file}"
    logger.info(res_str)

def parse_args():
    parser = ArgumentParser()

    parser.add_argument('amber_folder',
                        help='Path to the amber files that should be cross compiled.', type=Path)
    
    parser.add_argument('spirv_as_path', help='Path to spirv-as.', type=Path)

    parser.add_argument('cross_compiler_path', help='Path to the cross-compiler.', type=Path)

    parser.add_argument('target_lang', help="The language to cross compile to.", default="glsl", choices=["glsl", "hlsl", "msl"], type=str)

    parser.add_argument('target_lang_compiler_path', help="The compiler/validator to use to check the target language output.", type=Path)

    parser.add_argument('--cross-compiler-name', default="spirv-cross", choices=["spirv-cross"], required=False,
                        help='The compiler to use for cross compilation. Only spirv-cross is currently supported.', type=str)
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

    os.makedirs("cross_compilation_logs", exist_ok=True)
    log_filename = f"cross_compilation_logs/cross_compilation_{time.time_ns()}.log"
    file_handler = logging.FileHandler(filename=log_filename)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.info(f"Logging to {log_filename}")


def main():
    args = parse_args()
    amber_folder = os.path.join(os.getcwd(), args.amber_folder)
    run_cross_compilation(amber_folder, args.spirv_as_path, args.cross_compiler_path, args.cross_compiler_name, args.target_lang, args.target_lang_compiler_path)


if __name__ == "__main__":
    main()