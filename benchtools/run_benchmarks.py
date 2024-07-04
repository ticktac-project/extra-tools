#!/usr/bin/env python3

import argparse
from io import StringIO
import itertools
import json
import subprocess
import sys

# This script runs TChecker programs on TChecker models as specified by the 
# input JSON benchmark specification file. It runs each program on each model 
# and extract the statistics produced by the programs. These statistics are #
# output to a JSON file.
# JSON format description available at:
# https://github.com/ticktac-project/extra-tools/blob/master/benchtools/README.md


# Creates dictionary from TChecker stats output
# output : TChecker stats output as a string of the form 'KEY1 VALUE1\nKEY2 VALUE2\n ..."
# (KEY and VALUE shall not contain any space except leading or trailing spaces)
# returns a dictionary mapping each KEY in output to its VALUE, with leading and trailing
# spaces stripped
def tchecker_stats_as_dict(output):
    d = {}
    with StringIO(output) as f:
        lines = f.readlines()
        for line in lines:
            info = line.split(" ")
            d[info[0]] = info[1].strip()
    return d


# Build a model from a script
# cmd : script command as a string
# args : arguments to script as an array of strings
# returns bytes produced by cmd on stdout
def build_model(cmd, args):
    process = subprocess.run([cmd] + args, capture_output=True)
    if process.returncode != 0:
        print("Script failure with return code", process.returncode)
        sys.exit()
    return process.stdout


# Run a program on a model
# cmd : program command as a string
# args : arguments to program command as an array of strings
# timeout : timeout for command
# model : input model for the program, as a string
# returns dictionary of statistics produced by the program
def run_program(cmd, args, timeout, model):
    stats = {}
    try:
        process = subprocess.run(
            [cmd] + args,
            capture_output=True,
            timeout=timeout,
            input=model,
        )
        if process.returncode == 0:
            stats = tchecker_stats_as_dict(process.stdout.decode())
            stats["status"] = "success"
        else:
            stats["status"] = "error"
    except subprocess.TimeoutExpired:
        stats["status"] = "timeout"
    return stats


# Extract statistics
# tchecker_stats : dict of stats output by TChecker tool
# expected_keys : list of expected stats keys
# returns a dict of stats with one entry for each key in expected_keys and
# corresponding value from tchecker_stats
# a warning has been reported for each key in expected_keys which is missing
# in tchecker_stats
def extract_stats(tchecker_stats, expected_keys):
    stats = {"status": tchecker_stats["status"]}
    if tchecker_stats["status"] == "success":
        for key in expected_keys:
            if key not in tchecker_stats:
                print("*** WARNING: unknown stat", key)
            else:
                stats[key] = tchecker_stats[key]
    return stats


# Computes the column of model's matrix where to reset the skip flag
# model : model description inside a benchmark
# returns a column number in the model's matrix if any, -1 otherwise
def reset_skip_column(model):
    if "reset_skip" not in model:
        return None
    reset_skip = model["reset_skip"]
    if (reset_skip < 0) or (reset_skip >= len(model["matrix"])):
        print("*** reset_skip should be between 0 and the size of 'matrix' - 1")
        sys.exit()
    return reset_skip


# Runs all experiments listed in a benchmark
# benchmark : JSON description of benchmark
# selected_models : list of models from benchmark to run
# selected_programs : list of programs from benchmark to run
# returns table of stats as described in benchmarks
def run_benchmark(benchmark, selected_models, selected_programs, cmds_only=False):
    results = {"name": benchmark["name"], "stats": {}}
    timeout = int(benchmark["timeout"]) if "timeout" in benchmark else None
    skip_on_timeout = (
        True if "skip_on_timeout" in benchmark and benchmark["skip_on_timeout"] == "True" else False
    )
    for model_name in selected_models:
        skip = {program_name: False for program_name in benchmark["programs"]}
        reset_skip_col = reset_skip_column(benchmark["models"][model_name])
        model = benchmark["models"][model_name]
        last_reset_skip_value = 0  # arbitrary
        for config in itertools.product(*model["matrix"]):
            # reset skip if needed
            if reset_skip_col is not None and config[reset_skip_col] != last_reset_skip_value:
                skip = {program_name: False for program_name in benchmark["programs"]}
            last_reset_skip_value = config[reset_skip_col] if reset_skip_col is not None else last_reset_skip_value
            # build model
            model_fullname = model_name + " " + " ".join(config)
            if not cmds_only:
                print("- Building model", model_fullname, "...", flush=True)
                results["stats"][model_fullname] = {}
            m = build_model(model["cmd"], model["args"] + list(config))
            # run each program
            for program_name in selected_programs:
                program = benchmark["programs"][program_name]
                if cmds_only:
                    model_cmd = " ".join([model["cmd"]] + model["args"] + list(config))
                    tool_cmd = " ".join([program["cmd"]] + program["args"])
                    print("{0}:{1}:{2}:{3}".format(model_fullname, model_cmd, program_name, tool_cmd))
                else:
                    print("   Running", program_name, "...", end="", flush=True)
                    if skip_on_timeout and skip[program_name]:
                        stats = {"status": "skipped"}
                    else:
                        stats = run_program(program["cmd"], program["args"], timeout, m)
                    print(stats["status"])
                    results["stats"][model_fullname][program_name] = extract_stats(
                        stats, program["stats"]
                    )
                    if stats["status"] == "timeout":
                        skip[program_name] = True
    return results


def print_commands(benchmark, selected_models, selected_programs):
    run_benchmark(benchmark, selected_models, selected_programs, True)


# Compute the list of specified benchmarks
# The result is a dictionary containing an entry "rows" usable in a table specification
def print_benchmarks(benchmark, selected_models, selected_programs):
    results = []
    for model_name in selected_models:
        model = benchmark["models"][model_name]
        for config in itertools.product(*model["matrix"]):
            model_fullname = model_name + " " + " ".join(config)
            results.append(model_fullname)
    return dict(rows=results)


# Select names in a list
# names : list of names
# selection : string of comma-separated names, or None
# return all if selection is None, otherwise the list of names in selection
# that appear in all
def select(names, selection):
    if selection is None:
        return names
    selected = selection.split(",")
    for s in selected:
        if s not in names:
            print("Unknown choice", s)
            sys.exit()
    return selected


def main():
    # Parse command-line
    parser = argparse.ArgumentParser(description="Runs a selection of programs over a selection of models and output "
                                                 "statistics")
    parser.add_argument("file", nargs=1, help=""" Benchmark JSON specification""")
    parser.add_argument("-o", help=""" Output file name (default: standard output)""")
    parser.add_argument("-m", help=""" Models selection, as a comma-separated list (default: all)""")
    parser.add_argument("-p", help=""" Programs selection, as a comma-separated list (default: all)""")
    parser.add_argument("-E", "--only-commands", help=""" Print only commands to execute""", action='store_true', default=False)
    parser.add_argument("-l", "--list-benchmarks", help=""" Print the list of specified benchmarks """,
                        action='store_true', default=False)
    args = parser.parse_args()

    out_filename = args.file[0]

    with open(out_filename, "r") as read_file:
        benchmark = json.load(read_file)
        selected_models = select(list(benchmark["models"]), args.m)
        selected_programs = select(list(benchmark["programs"]), args.p)
        if args.only_commands:
            print_commands(benchmark, selected_models, selected_programs)
        else:
            if args.list_benchmarks:
                results = print_benchmarks(benchmark, selected_models, selected_programs)
            else:
                results = run_benchmark(benchmark, selected_models, selected_programs, sys.stderr)
            if args.o is None:
                json.dump(results, sys.stdout,indent=2)
            else:
                with open(args.o, "w") as write_file:
                    json.dump(results, write_file)
                    write_file.close()
        read_file.close()


if __name__ == "__main__":
    main()
