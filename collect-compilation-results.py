#!/usr/bin/env python

import sys
import itertools
import os
import os.path
import re
import traceback
import datetime
import shutil
import mimetypes

def debug(s):
    sys.stderr.write("[DEBUG] %s\n" % s)

def warn(s):
    sys.stderr.write("[WARNING] %s\n" % s)

def error(s):
    sys.stderr.write("[ERROR] %s\n" % s)

    
def get_last_modified_time(path):
    dt = datetime.datetime.fromtimestamp(os.path.getmtime(path))
    return dt.strftime("%Y%m%d%H%M%S")

def get_board_name(kernel_dir):
    #sys_desc_file = file(os.path.join(kernel_dir, "sys_description.txt"))
    #sys_desc = sys_desc_file.readline()
    #board = sys_desc.split()[1]
    board_spec_file = file(os.path.join(kernel_dir, "board_spec.xml"))
    for line in board_spec_file:
        m = re.search("<board (.* )?name=\"([^\"]+)\"", line)
        if m is None:
            continue
        return m.groups()[1]
    error("Board name not detected")
    sys.exit(1)

def get_aocl_version(kernel_dir):
    version_file_path = os.path.join(kernel_dir, "quartus_sh_compile.log")
    if os.path.exists(version_file_path):
        version_file = file(os.path.join(kernel_dir, version_file_path))
        reg_pattern = re.compile("Info: Version ([0-9\.]+) Build")
        for line in version_file:
            m = reg_pattern.search(line)
            if m is None:
                continue
            v = m.groups()[0]
            return v
    warn("Version number not found")
    sys.stdout.write("Type compiler version number: ")
    v = sys.stdin.readline().strip()
    return v

def get_kernel_version(kernel_dir_path):
    m = re.search("_(v[0-9]+(_.+)?)$", kernel_dir_path)
    if m:
        return m.groups()[0]
    error("Getting kernel version failed: " + kernel_dir_path)
    sys.exit(1)

def mkdir(top, path_components):
    assert os.path.exists(top)
    assert os.path.isdir(top)
    for d in path_components:
        top = os.path.join(top, d)
        if not os.path.exists(top):
            os.mkdir(top)
    return top

def get_dest_path(repo_top_dir_path, sys_name, bench_name, kernel_dir_path):
    ts = get_last_modified_time(kernel_dir_path)
    board = get_board_name(kernel_dir_path)
    aocl_version = get_aocl_version(kernel_dir_path)
    kernel_version = get_kernel_version(kernel_dir_path)
    
    p = mkdir(repo_top_dir_path, [sys_name, board, "aocl_" +
                                  aocl_version, bench_name,
                                  kernel_version, "compile", ts])
    return p

def copy_kernel_files(kernel_dir_path, dest):
    max_size = 20*1000*1000
    # copy any text files smaller than 20MB
    for f in os.listdir(kernel_dir_path):
        fp = os.path.join(kernel_dir_path, f)
        relevant_suffixes = ["txt", "rpt", "log", "area", "xml",
                             "csv", "summary", "attrib"]
        if not any(fp.endswith("." + sfx) for sfx in relevant_suffixes):
            debug("Skipping a non-relevant file: " + fp)
            continue
        if os.path.getsize(fp) > max_size:
            debug("Skipping a too-large file: " + fp)
            continue
        debug("Copying %s to %s" % (fp, dest))
        dest_fp = os.path.join(dest, os.path.basename(fp))
        if os.path.exists(dest_fp):
            warn("Skipping %s since it already exists at: %s" % (fp, dest_fp))
            continue
        shutil.copyfile(fp, dest_fp)
    return
        
def main():
    if len(sys.argv) != 5:
        error("Usage: %s <kernel_dir_path> <repo_top_dir_path> <sys_name> <benchmark_name>"
              % sys.argv[0])
        sys.exit(1)

    kernel_dir_path = sys.argv[1]
    repo_top_dir_path = sys.argv[2]
    sys_name = sys.argv[3]
    benchmark_name = sys.argv[4]
    
    dest = get_dest_path(repo_top_dir_path, sys_name, benchmark_name,
                         kernel_dir_path)

    copy_kernel_files(kernel_dir_path, dest)
    
    return
    
if __name__ == "__main__":
    main()


    
