#!/usr/bin/env python

"""
=======================================================================
    isCFGdeemedFeasible.py

    This tool checks whether the control flow graph is deemed feasible.
=======================================================================
"""

import sys, getopt
import platform
import argparse
import filecmp
import os, subprocess
import re
import csv
import time
from pathlib import Path
from sys import platform as _platform
from subprocess import Popen,PIPE
from argparse import ArgumentParser, SUPPRESS


CURR_DIR = os.path.dirname(__file__)

# program description
t = 'This tool checks whether the control flow graph is deemed feasible.'

# Disable default help
parser = ArgumentParser(description=t, add_help=False)
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

required.add_argument('-a','--path_to_alloy_Files',
                    required=True,
                    help='The path to the Vulkan CTS .als files folder',
                    )
required.add_argument('-x','--path_to_XML_Output_Folder',
                    required=True,
                    help='The path to the generated instance XML files'
                    )
required.add_argument('-c','--path_to_AlloyStar',
                    required=True,
                    help='The Alloy* (https://github.com/johnwickerson/alloystar) packs the RunAlloy tool which allows Alloy run from the command line'
                    )

optional.add_argument('-m','--memory',
                    type=int,
                    required=False,
                    default = 3,
                    help='Maximum memory in [GB]'
                    )
optional.add_argument('-s','--solver',
                    required=False,
                    default = "sat4j",
                    choices=['sat4j', 'cryptominisat', 'glucose', 'plingeling', 'lingeling', 'minisatprover', 'minisat'],
                    help = 'Constraint/SAT Solver: By default, the pure Java solver "SAT4J" is chosen since it runs on every platform and operating system. If you require faster performance, you can try one of the native solver such as MiniSat or ZChaff.',
                    )

optional.add_argument("--block-limit", required=False, type=int, default=100, help="Any .als files containing more blocks than this limit will be skipped.")

args = parser.parse_args()


def get_processor_info():
    # returns the required Java Native Interface (JNI) lbrary
    if _platform == "linux" or _platform == "linux2":
        if platform.machine() == "AMD64":
            JNIlibrary = os.path.join(args.path_to_AlloyStar, 'amd64-linux')
        else:
            JNIlibrary = os.path.join(args.path_to_AlloyStar, 'x86-linux')
    elif _platform == "darwin":
        JNIlibrary = os.path.join(args.path_to_AlloyStar, 'x86-mac')
    elif _platform == "win32":
        JNIlibrary = os.path.join(args.path_to_AlloyStar, 'x86-windows')
    elif _platform == "freebsd7" or _platform == "freebsd8" or _platform == "freebsdN":
        JNIlibrary = os.path.join(args.path_to_AlloyStar, 'x86-freebsd')
    return JNIlibrary


def blocks(als_filepath):
    with open(als_filepath) as f:
        file_contents = f.read()
        blocks = int(re.search(r'\#blocks:\s+(\d+)', file_contents).group(1))
    return blocks


def exit_blocks(als_filepath):
    with open(als_filepath) as f:
        file_contents = f.read()
        exit_blocks = int(re.search(r'\#exit blocks:\s+(\d+)', file_contents).group(1))
    return exit_blocks


def jumps(als_filepath):
    with open(als_filepath) as f:
        file_contents = f.read()
        jumps = int(re.search(r'\#jumps:\s+(\d+)', file_contents).group(1))
    return jumps


def cyclomatic_complexity(als_filepath):
    return jumps(als_filepath) - blocks(als_filepath) +2*exit_blocks(als_filepath)


def header_blocks(als_filepath):
    with open(als_filepath) as f:
        for line in f:
            if re.search('HeaderBlock = ', line):
                line_s = line.rstrip()
                header_blocks = line_s.count('+')+1 if not re.search('none', line_s) else 0
                return header_blocks
    return None


def loop_headers(als_filepath):
    with open(als_filepath) as f:
        for line in f:
            if re.search('LoopHeader = ', line):
                line_s = line.rstrip()
                loop_headers = line_s.count('+') + 1 if not re.search('none', line_s) else 0
                return loop_headers
    return None


def switch_blocks(als_filepath):
    with open(als_filepath) as f:
        for line in f:
            if re.search('SwitchBlock = ', line):
                line_s = line.rstrip()
                switch_blocks = line_s.count('+') + 1 if not re.search('none', line_s) else 0
                return switch_blocks
    return None

t_OoM = 0
def translation_time_vars_clauses(outp):
    if 'Translation took' in outp:
        for line in outp.split('\n'):
            if re.search('Translation took', line):
                line_s = line.rstrip()
                tt = re.findall(r'[\d\.\d]+', line_s)
                return tt
    elif 'java.lang.OutOfMemoryError' in outp:
        return ['-', '-', '-', t_OoM, '-', '-', '-']
    return ['-', '-', '-', '-', '-', '-', '-']



def solving_time(outp):
    for line in outp.split('\n'):
        if re.search('Solving took', line):
            line = line.rstrip()
            st = re.findall(r'[\d\.\d]+', line)[0]
            return st
    return '-'


def feasible(outp):
    if 'xml' in outp:
        return True
    elif 'OutOfMemoryError' in outp:
        return 'OutOfMemory'
    else:
        return False


if not os.path.exists(args.path_to_XML_Output_Folder):
    os.mkdir(args.path_to_XML_Output_Folder)

def parse_output(outp, als_filepath):
    # parse the output and write the data to a csv file
    with open(os.path.join(args.path_to_XML_Output_Folder, 'out.csv'), 'a+', encoding='UTF8', newline='') as out_csv:
        writer = csv.writer(out_csv)
        blcks = blocks(als_filepath)
        hb = header_blocks(als_filepath)
        lh = loop_headers(als_filepath)
        jmps = jumps(als_filepath)
        ex_blocks = exit_blocks(als_filepath)
        sb = switch_blocks(als_filepath)
        cyc_complexity = jmps - blcks +2*ex_blocks
        tt_v_c = translation_time_vars_clauses(outp)
        #header = ['CFG',                  'Blocks', 'HeaderBlocks', 'LoopHeaders', 'SelectionHeaders', 'SwitchBlocks',  'Jumps', 'ExitBlocks', 'CyclomaticComplexity', 'TranslationTime', 'SolvingTime',      'Vars',     'PrimaryVars', 'Clauses', 'Feasible']
        data =    [Path(als_filepath).stem, blcks,    hb,             lh,            hb-lh-sb,           sb,              jmps,    ex_blocks,    cyc_complexity,         tt_v_c[3],         solving_time(outp), tt_v_c[4], tt_v_c[5],      tt_v_c[6], feasible(outp)]
        #print(data)
        writer.writerow(data)

def is_likely_to_timeout(path_to_als, block_limit=100):
    num_blocks = blocks(path_to_als)
    return num_blocks > block_limit

def checkCFG():
    infeasible = ''
    skipped = ''
    errors = ''
    out_file = open(os.path.join(args.path_to_XML_Output_Folder, "outputs.txt"),"w+")
    # create csv and write header
    out_csv = open(os.path.join(args.path_to_XML_Output_Folder, "out.csv"), "w")
    header = ['CFG', 'Blocks', 'HeaderBlocks', 'LoopHeaders', 'SelectionHeaders', 'SwitchBlocks', 'Jumps', 'ExitBlocks',
              'CyclomaticComplexity', 'TranslationTime', 'SolvingTime', 'Vars', 'PrimaryVars', 'Clauses', 'Feasible']
    csv.writer(out_csv).writerow(header)
    out_csv.close()
    sorted_files = []
    for file in os.listdir(args.path_to_alloy_Files):
        if file.endswith('.als'):
            sorted_files.append((file, os.path.getsize(os.path.join(args.path_to_alloy_Files, file))))
        else:
            continue
    # Sort data by size (smallest to largest)
    sorted_files.sort(key=lambda x: x[1])
    number_als_files = len(sorted_files)
    current_file = 0
    for i in range(0, number_als_files):
        filename = sorted_files[i][0]
        output = ''
        current_file += 1
        divider = '\n\n\n\n'+str(current_file) + '/' + str(number_als_files)+'\n════════════════════════════════════════════════════════════'
        output += divider+'\n'
        print(divider)
        path_to_als = os.path.join(args.path_to_alloy_Files, filename)
        output += str(path_to_als)+'\n'
        print(path_to_als)

        if is_likely_to_timeout(path_to_als, block_limit=args.block_limit):
            block_limit_warning = f"Skipping {path_to_als} as it will likely take too long to compute.\nSee is_likely_to_timeout for more details."
            print(block_limit_warning)
            output += f'\n{block_limit_warning}'
            out_file.write(output)
            skipped += f"{path_to_als}\n"
            continue

        basefilename = os.path.splitext(filename)[0]
        cmd = 'cd '+args.path_to_AlloyStar+' && ' \
              'mkdir -p '+os.path.join(args.path_to_XML_Output_Folder, basefilename)+' && ' \
              'java -Xmx'+str(args.memory)+'g -Djava.library.path='+get_processor_info()+' -Dout='+os.path.join(args.path_to_XML_Output_Folder, basefilename)+' -Dquiet=false -Dsolver='+args.solver+' -Dhigherorder=true -Dcmd=0 edu/mit/csail/sdg/alloy4whole/RunAlloy '+path_to_als
        tmp = Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, text=True)

        global t_OoM
        t_OoM = 0
        start_time = time.time()

        # Getting realtime output
        while True:
            line_output = tmp.stdout.readline()
            if line_output == '' and tmp.poll() is not None:
                break
            if line_output and line_output.strip() != '':
                print(line_output.strip())
                output += str(line_output)
        
        if tmp.returncode != 0:
            error_str = "".join(tmp.stderr.readlines())
            print(error_str)
            output += error_str
            errors += str(path_to_als) + '\n'

        t_OoM = round(time.time() - start_time, 2)
        print('Elapsed time: ' + str(t_OoM) + 's')
        output += 'Elapsed time: ' + str(t_OoM) + 's'
        if 'No solution found' in output:
            infeasible += str(path_to_als) + '\n'

        # REMOVE XML DUPLICATES
        # List all xml files
        DATA_DIR = Path(os.path.join(args.path_to_XML_Output_Folder, basefilename))
        allfiles = sorted(os.listdir(DATA_DIR))
        xmlfiles = [i for i in allfiles if i.endswith('.xml')]
        # list containing the classes of documents with the same content
        duplicates = []
        # comparison of the documents
        for fil in xmlfiles:
            is_duplicate = False
            # "equivalence classes"
            for class_ in duplicates:
                is_duplicate = filecmp.cmp(
                    DATA_DIR / fil,
                    DATA_DIR / class_[0],
                    shallow=False #  Setting this parameter to False instructs filecmp to look at the contents of the files and not the metadata, such as filesize,
                )
                if is_duplicate:
                    class_.append(fil)
                    break
            if not is_duplicate:
                duplicates.append([fil])

        print('\nThe identified "equivalence classes" are: \n', duplicates)
        output += '\nThe identified "equivalence classes" are: \n'+ str(duplicates)
        # remove the duplicates
        for class_ in duplicates:
            for fi in class_[1:]:
                os.remove(DATA_DIR / fi)
        print('Duplicates have been removed.')
        output += '\nDuplicates have been removed.'
        out_file.write(output)

        # parse the output and write the data to a csv file
        parse_output(output, path_to_als)

    number_infeasible = infeasible.count('\n')
    number_skipped = skipped.count("\n")
    number_errors = errors.count("\n")

    hurrah = """
                                      \O/
                                       |
                                       |
                                     _/ \_
                                            """
    bord = '##=##=##=##=##=##=##=##=##=##=##=##=##=##=##=##=##=##=##=##=##=##=##=##=##=##=##=##\n\n'
    final = f'{number_als_files} GRAPHS WERE PROCESSED. {number_errors} GRAPHS HAD ERRORS. {number_als_files - number_skipped - number_errors} GRAPHS WERE CHECKED. {number_infeasible} ARE INFEASIBLE. {number_skipped} WERE SKIPPED.'
    if number_errors > 0:
        final += f'\nTHE {number_errors} GRAPHS BELOW HAVE ERRORS:\n {errors}'
    if number_infeasible > 0:
        final += f'\nTHE {number_infeasible} GRAPHS BELOW ARE DEEMED INFEASIBLE:\n {infeasible}'
    if number_skipped > 0:
        final += f'\nTHE {number_skipped} GRAPHS BELOW WERE SKIPPED:\n{skipped}'
    
    final += '\nALL OUTPUTS SAVED IN '+str(os.path.join(args.path_to_XML_Output_Folder, "outputs.txt"))+'\n\n'
    _final = '\n\n\n'+hurrah+'\n'+bord+final+bord
    print(_final)
    out_file.write(_final)
    out_file.close()
#print(os.name)
#print( platform.machine() )
#print(_platform)
#print(CURR_DIR)


def main():
    checkCFG()


if __name__ == "__main__":
    main()
