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
# JSON format description abaibale at:
# https://github.com/ticktac-project/extra-tools/blob/master/benchtools/README.md


# Creates dictionary from TChecker stats output
# output : TChecker stats output as a string of the form 'KEY1 VALUE1\nKEY2 VALUE2\n ..."
# (KEY and VALUE shall no contain any space except leading or traling spaces)
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
# returns dictionnary of statistics produced by the program
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


# Extract satistics
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
            if not key in tchecker_stats:
                print("*** WARNING: unknown stat", key)
            else:
                stats[key] = tchecker_stats[key]
    return stats


# Computes the column of model's matrix where to reset the skip flag
# model : model description inside a benchmark
# returns a column number in the model's matrix if any, -1 otherwise
def reset_skip_column(model):
    if not "reset_skip" in model:
        return None
    reset_skip = model["reset_skip"]
    if (reset_skip < 0) or (reset_skip >= len(model["matrix"])):
        print("*** reset_skip should be between 0 and the size of 'matrix' - 1")
        sys.exit()
    return reset_skip

# Runs all experiments listed in a benchmark
# benchmark : list of experiments
# returns table of stats as described in benchmarks
def run_benchmark(benchmark):
    results = {"name": benchmark["name"], "stats": {}}
    timeout = int(benchmark["timeout"]) if "timeout" in benchmark else None
    skip_on_timeout = (
        True if "skip_on_timeout" in benchmark and benchmark["skip_on_timeout"] == "True" else False
    )
    for model_name in benchmark["models"]:
        skip = {program_name: False for program_name in benchmark["programs"]}
        reset_skip_col = reset_skip_column(benchmark["models"][model_name])
        model = benchmark["models"][model_name]
        last_reset_skip_value = 0 # arbitrary
        for config in itertools.product(*model["matrix"]):
            # reset skip if needed
            if reset_skip_col != None and config[reset_skip_col] != last_reset_skip_value:
                skip = {program_name: False for program_name in benchmark["programs"]}
            last_reset_skip_value = config[reset_skip_col] if reset_skip_col != None else last_reset_skip_value
            # build model
            model_fullname = model_name + " " + " ".join(config)
            print("- Building model", model_fullname, "...", flush=True)
            m = build_model(model["cmd"], model["args"] + list(config))
            results["stats"][model_fullname] = {}
            # run each program
            for program_name in benchmark["programs"]:
                program = benchmark["programs"][program_name]
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


# Parse command-line
parser = argparse.ArgumentParser()
parser.add_argument("file", nargs=1, help=""" Benchmark JSON specification""")
parser.add_argument("-o", help=""" Output file name""")
args = parser.parse_args()

with open(args.file[0], "r") as read_file:
    benchmark = json.load(read_file)
    results = run_benchmark(benchmark)
    if args.o == None:
        json.dump(results)
    else:
        with open(args.o, "w") as write_file:
            json.dump(results, write_file)
            write_file.close()
    read_file.close()
