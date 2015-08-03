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
import optparse

execution_result_catalogue = {"nw": ["result.txt",
                                     "command_output.txt"]}

def debug(s):
    sys.stderr.write("[DEBUG] %s\n" % s)

def warn(s):
    sys.stderr.write("[WARNING] %s\n" % s)

def error(s):
    sys.stderr.write("[ERROR] %s\n" % s)

    
def get_last_modified_time(paths):
    ts = [os.path.getmtime(p) for p in paths]
    dt = datetime.datetime.fromtimestamp(max(ts))
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
        version_file = file(version_file_path)
        reg_pattern = re.compile("Info: Version ([0-9\.]+) Build")
        for line in version_file:
            m = reg_pattern.search(line)
            if m is None:
                continue
            v = m.groups()[0]
            return v
    warn("Compiler version number not found")
    return None

def get_kernel_version(kernel_dir_path):
    m = re.search("_(v[0-9]+(_.+)?)$", kernel_dir_path)
    if m:
        return m.groups()[0]
    warn("Kernel version unknown")
    return None

def mkdir(top, path_components):
    assert os.path.exists(top)
    assert os.path.isdir(top)
    for d in path_components:
        top = os.path.join(top, d)
        if not os.path.exists(top):
            os.mkdir(top)
    return top

def get_compile_dest_path(repo_top_dir_path, bench_name,
                          kernel_dir_path, kernel_version,
                          aocl_version):
    compile_top_path = "compile"
    ts = get_last_modified_time([kernel_dir_path])
    board = get_board_name(kernel_dir_path)
    p = mkdir(repo_top_dir_path,
              [compile_top_path, board, "aocl_" +
               aocl_version, bench_name, kernel_version,
               ts])
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

def copy_compilation_results(repository,
                             bench_name, kernel_dir,
                             kernel_version, aocl_version):
    dest = get_compile_dest_path(repository,
                                 bench_name,
                                 kernel_dir, kernel_version,
                                 aocl_version)

    print "Copy compilation results to " + dest
    
    copy_kernel_files(kernel_dir, dest)
    return

def get_execution_result_files(args, benchmark_name):
    # when supplied by the user
    if len(args) > 0:
        return args
    # See whether its file list is known
    if benchmark_name in execution_result_catalogue:
        return execution_result_catalogue[benchmark_name]
    error("Result files unknown\n")
    sys.exit(1)

def get_execution_dest_path(repo_top_dir_path, sys_name, bench_name,
                            kernel_dir_path, kernel_version,
                            aocl_version, execution_result_files):
    exec_top_path = "exec"
    kernel_ts = get_last_modified_time([kernel_dir_path])
    exec_ts = get_last_modified_time(execution_result_files)
    board = get_board_name(kernel_dir_path)
    p = mkdir(repo_top_dir_path,
              [exec_top_path, board, sys_name,
               "aocl_" + aocl_version, bench_name,
               kernel_version, exec_ts])
    return p

def create_pointer_to_compile(basedir, repository,
                              bench_name, kernel_dir,
                              kernel_version, aocl_version):
    # python does not support symlink on Windows
    link_name = "compile"
    link_target = get_compile_dest_path(
        repository, bench_name, kernel_dir,
        kernel_version, aocl_version)
    
    p = os.path.join(basedir, link_name)
    f = file(p, 'w')
    f.write("%s\n" % link_target)
    f.close()
    return
    

def copy_execution_results(repository, sys_name,
                           bench_name, kernel_dir,
                           kernel_version, aocl_version,
                           execution_result_files):
    dest = get_execution_dest_path(repository, sys_name, bench_name,
                                   kernel_dir, kernel_version,
                                   aocl_version,
                                   execution_result_files)

    print "Copy execution results to " + dest
    
    for fp in execution_result_files:
        debug("Copying %s to %s" % (fp, dest))
        dest_fp = os.path.join(dest, os.path.basename(fp))
        if os.path.exists(dest_fp):
            warn("Skipping %s since it already exists at: %s" % (fp, dest_fp))
            continue
        shutil.copyfile(fp, dest_fp)

    print "Create a file containing the path to compile information directory"
    create_pointer_to_compile(dest,  repository,
                              bench_name, kernel_dir,
                              kernel_version, aocl_version)
    return
        
def main():
    usage = "usage: %prog [parameters] [execution-results-files]"
    parser = optparse.OptionParser(usage)
    parser.add_option("-c", "--compilation", dest="is_compile",
                      action="store_true", help="collect compile results")
    parser.add_option("-e", "--execution", dest="is_compile",
                      action="store_false", help="collect execution results")
    parser.add_option("-k", "--kernel", dest="kernel_dir_path",
                      help="kernel directory path (REQUIRED)")
    parser.add_option("-r", "--repository", dest="repository",
                      help="repository path (REQUIRED)")
    parser.add_option("-s", "--system", dest="sys_name",
                      help="system name")
    parser.add_option("-b", "--benchmark", dest="benchmark_name",
                      help="benchmark name (REQUIRED)")
    parser.add_option("-v", "--kernel-version", dest="kernel_version",
                      help="kernel version (OPTIONAL)")
    parser.add_option("-a", "--aocl-version", dest="aocl_version",
                      help="AOCL version (OPTIONAL)")
    
    (options, args) = parser.parse_args()
    if options.is_compile and len(args) != 0:
        error("Incorrect number of arguments")
        parser.print_help()        
        sys.exit(1)

    if options.kernel_dir_path is None or \
       options.repository is None or \
       (not options.is_compile and options.sys_name is None) or \
       options.benchmark_name is None or \
       options.is_compile is None:
        error("Missing required argument")
        parser.print_help()        
        sys.exit(1)

    kernel_version = options.kernel_version
    if kernel_version is None:
        kernel_version = get_kernel_version(options.kernel_dir_path)
    # if not specified by the user nor detected automatically, use the
    # default name "default"
    if kernel_version is None:
        kernel_version = "default"

    aocl_version = options.aocl_version
    if aocl_version is None:
        aocl_version = get_aocl_version(options.kernel_dir_path)
    assert aocl_version is not None

    if options.is_compile:
        copy_compilation_results(options.repository,
                                 options.benchmark_name,
                                 options.kernel_dir_path,
                                 kernel_version,
                                 aocl_version)
    else:
        execution_result_files = get_execution_result_files(args, options.benchmark_name)
        copy_execution_results(options.repository,
                               options.sys_name,
                               options.benchmark_name,
                               options.kernel_dir_path,
                               kernel_version,
                               aocl_version,
                               execution_result_files)
        
    return
    
if __name__ == "__main__":
    main()


    
