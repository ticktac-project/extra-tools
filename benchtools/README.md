benchtools
==========

Description
-----------

`benchtools` is a set of tools that allow to run benchmarks, collect the statistics produced by TChecker tools on these benchmarks, and build LaTeX tables from these statistics. `benchtools` are written in Python and require Python 3 as well as packages `argparse`, `io`, `itertools`, `json`, `math`, `subprocess` and `sys`.

Usage
-----

`benchtools` consist in two scritps. The first one, `run_benchmarks.py` is used to run selected TChecker programs over specified models, and collect statistics. The set of TChecker programs as well as the set of models and statistics to collect are specified in a JSON file (see below for the file format). A subset of the models and programs to run can be specified with options `-m` and `-p` respectively. For instance, `-m "model 1,model 2" -p "p1,p2,p3` runs programs `p1`, `p2` and `p3` over models `model 1` and `model 2`. The specified models and programs should be defined in `file`. Command usage is obtained by running `run_benchmarks.py -h` in a terminal:

```
usage: run_benchmarks.py [-h] [-o O] [-m M] [-p P] file

Runs a selection of programs over a selection of models and output statistics

positional arguments:
  file        Benchmark JSON specification

options:
  -h, --help  show this help message and exit
  -o O        Output file name (default: standard output)
  -m M        Models selection, as a comma-separated list (default: all)
  -p P        Programs selection, as a comma-separated list (default: all)
```

The second script `make_table.py` builds a LaTeX table from a table specification and the statistics output by `run_benchmarks.py`. See below for a description of the JSON format expected by this script. Usage is obtained by running `make_table.py -h` in a terminal:

```
usage: make_table.py [-h] -t T [-o O] file

positional arguments:
  file        Benchmark JSON output

options:
  -h, --help  show this help message and exit
  -t T        JSON description of table rows and columns
  -o O        Output file name
```

Benchmarks specification
------------------------

The script `run_benchmarks.py` takes as input the specification of the benchmarks to evaluate, in the following JSON format:

```json
{
    "name": "My benchmark",
    "timeout": 60,
    "skip_on_timeout": "True",
    "models": {
        "A": {
            "cmd": "/path/to/script/that/generates/model/A/generate.sh",
            "args": [],
            "matrix": [["2", "3", "4"]]
        },
        "B": {
            "cmd": "/path/to/script/that/generates/model/B/script.py",
            "args": ["--foo", "bar"],
            "matrix": [["3", "4", "5"], ["100", "200"]],
            "reset_skip": 0
        }
    },
    "programs": {
        "reach": {
            "cmd": "/path/to/tchecker/tck-reach",
            "args": ["-a", "reach", "-s", "bfs"],
            "stats": [
                "VISITED_STATES",
                "VISITED_TRANSITIONS"
            ]
        },
        "covreach": {
            "cmd": "/path/to/tchecker/tck-reach",
            "args": ["-a", "covreach"],
            "stats": [
                "VISITED_STATES",
                "VISITED_TRANSITIONS",
                "RUNNING_TIME_SECONDS",
                "MEMORY_MAX_RSS"
            ]
        }
    }
}
```

The specification consists in 5 parts. The `name` of the benchmark, a `timeout` value, and a `skip_on_timeout` flag (optional, `False` by default), a list of `models` and a list of `programs`. The script `run_benchmarks.py` will run each program on each model and collect the statistics specified in the `stats` part of each program. 

The models are instantiated by running the script given at `cmd` with specified arguments and extra arguments obtained from the `matrix`. The `matrix` specifies parameters which are used to generate instances of various size or complexity of the model. In our example above, model `A` will be instantiated by running script `/path/to/script/that/generates/model/A/generate.sh` successively with arguments `2`, `3` and `4`. Instances of model `B` will be obtained by running script `/path/to/script/that/generates/model/B/script.py` with argument `--foo bar` and extra arguments `3 100`, then `3 200`, `4 100` , `4 200`, `5 100` and finally `5 200` successively.

The script `run_benchmarks.py` instantiates the models on-the-fly and applies each program in the `programs` part to the model instance. In our example, the first program `reach` corresponds to running `/path/to/tchecker/tck-reach -a reach -s bfs` and collect statistics `VISITED_STATES` and `VISITED_TRANSITIONS`. The second program `covreach` corresponds to running `/path/to/tchecker/tck-reach -a covreach` and collect statistics `VISITED_STATES`, `VISITED_TRANSITIONS`, `RUNNING_TIME_SECONDS` and `MEMORY_MAX_RSS`.

When running a program on a model instance exceeds `timeout`, the script `run_benchmarks.py` stops the program and proceeds with the next program or model instance. If `skip_on_timeout` is `True`, the script `run_benchmarks.py` will skip running the program that has timed out on the subsequent instances of the same model. But this program will be run on the next model. For instance, if program `reach` times out on instance of model `A` with parameter `3`, then it will not be run on instance of `A` with paramater `4`, however it will be run on model `B`. For models with more complex `matrix`, the value of `reset_skip` allows to reset the skip flag when a specific column of the matrix changes value. On the example above, if program `reach` times out on arguments `4 100`, the next value `4 200` will be skipped. However, it will be run on `5 100` as `reset_skip` has value `0` and the first argument (of index `0`) has changed from `4` to `5`. The value of `reset_skip` should be a valid index in the `matrix` (seen as a list of lists).

The script `run_benchmarks.py` produces statistics as specified in the benchmark specification. The output file format is described in the next section.

Statistics file format
----------------------

When `run_benchmarks.py` terminates, it outputs a JSON file as follows:

```json
{
    "name": "My benchmark",
    "stats": {
        "A 2": {
            "reach": {
                "status": "success",
                "VISITED_STATES": "125",
                "VISITED_TRANSITIONS": "765"
            },
            "covreach": {
                "MEMORY_MAX_RSS": "254705664",
                "RUNNING_TIME_SECONDS": "0.000561834",
                "status": "success",
                "VISITED_STATES": "81",
                "VISITED_TRANSITIONS": "144"
            }
        },
        "A 3": {
            "reach": {
                "status": "timeout"
            },
            "covreach": {
                "MEMORY_MAX_RSS": "542705872",
                "RUNNING_TIME_SECONDS": "0.60568236",
                "status": "success",
                "VISITED_STATES": "7618",
                "VISITED_TRANSITIONS": "15421"
            }
        },
        "A 4": {
            "reach": {
                "status": "skipped"
            },
            "covreach": {
                "MEMORY_MAX_RSS": "753976222",
                "RUNNING_TIME_SECONDS": "54.3109409",
                "status": "success",
                "VISITED_STATES": "245389",
                "VISITED_TRANSITIONS": "1745620"
            }
        },
        ...
    }
}
```

The `name` is the copied from the benchmark specification. Then, the file contains one `stats` entry for each instance of each model. Only the entries corresponding to instances of model `A` are shown above for readability. In the example above, `A 2` corresponds to the runs of the programs on the instances of model `A` with parameter `2`.

Each `stats` entry has a dictionary of statistics for each program in the benchmark. For `A 2`, we find an entry for the first program `reach` and a second entry for the other program `covreach`. For each of them, the file contains the statistics specified in the benchmark file presented in the previous section. It also contains a `status` information. The `status` can be `success` when the run was successful, `timeout` if the run has timed out, `skipped` when the run was skipped (i.e. the program has not been run on the instance), and `error` when an error occurred.

In our example, program `reach` timed out on instance `A 3`. Then it was not run on instance `A 4` (`status` is `skipped`) since `skip_on_timeout` is `True` in the benchmark specification. Thus the program `reach` is not run on any subsequent instance of model `A`. However, it restarts running from the first instance of the next model (model `B` is our example).

Table specification
-------------------

The script `make_table.py` can be used to build a LaTeX table from the statistics file output by `run_benchmarks.py` and described in the previous section. To that purpose, `make_table.py` takes as input a table description as follows:

```json
{
    "parameters": {
      "tabular" : "False"
    },
    "rows": [
        "A 2",
        "A 3",
        "A 4",
        "",
        "B 3 100",
        "B 4 100"
    ],
    "columns": {
        "reach": {
            "N": {
                "value": {
                    "name": "VISITED_STATES"
                }
            },
            "T": {
                "value": {
                    "name": "VISITED_TRANSITIONS"
                }
            }
        },
        "covreach": {
            "N ": {
                "value": {
                    "name": "VISITED_STATES"
                }
            },
            "T": {
                "value": {
                    "name": "VISITED_TRANSITIONS"
                }
            },
            "time": {
                "enabled" : "False",
                "round": {
                    "value": {
                        "name": "RUNNING_TIME_SECONDS",
                        "type": "float"
                    },
                    "decimal": 1
                }
            },
            "mem": {
                "round": {
                    "divide": {
                        "value": {
                            "name": "MEMORY_MAX_RSS",
                            "type": "int"
                        },
                        "by": 1048576
                    },
                    "decimal": 1
                }
            }
        }
    }
}
```

The table specification consists in a list of parameters, rows and a list of columns. For rows, we only specify row names. They should correspond to entries in the `stats` part of the satitistics file (see previous section). Empty row names correspond to separators (`\hline` in LaTeX).

The columns of the table should correspond to program names in the statistics file (here `reach` and `covreach`). Then, for each column, we specify sub columns that will contain the values in the table. In our example, the column `reach` will have sub columns `N` and `T`, and column `covreach` will have sub columns `N`, `T`, `time` and `mem`. For each sub column, we specify how the value is obtained.
A flag `enabled` can be used for each sub-column to indicate that then sub-column is taken into account or not; by default it is the case.

A value in the table is obtained by application of functions to the values in the statistics file. The function `value` returns the value of the satistics with the given `name` and `type` (which is `str` is the type is not specified). The function `divide` returns its sub value divided by the denominator specified with `by`. And the function `round` rounds up values to the specified `decimal` number.

In our example, the value in row `A 2`, column `reach` and sub column `N` is obtained by reading the value in entry `A 2`/`reach`/`VISITED_STATES` in the `stats` dictionnary of the input file (see section above). The value in row `A 3`, column `covreach`, sub column `mem` is obtained from the value in entry `A 3`/`covreach`/`MEMORY_MAX_RSS`, which is divided by 1048576, and rounded to the first decimal.

The values are computed only when the `status` of computation is `success`. In all other cases, the status is written to the table instead of the values.

Only one parameter is currently supported. A Boolean string assigned to parameter `tabular` indicates, if `True`, the generated table is not enclosed by a `table` environment and no caption is produced. 

The script `make_table.py` will produce the following LaTeX table from the specification above and the statistics in the previous section:

```latex
\begin{table}
  \begin{tabular}{|l||r|r||r|r|r|r|}
    \hline
Models & \multicolumn{2}{c|}{reach} & \multicolumn{4}{c|}{covreach} \\
 & N & T & N & T & time & mem\\
    \hline
A 2 & 125 & 765 & 81 & 144 & 0.0 & 242.9\\
A 3 & \multicolumn{2}{c|}{timeout} & 7618 & 15421 & 0.6 & 517.5\\
A 4 & \multicolumn{2}{c|}{skipped} & 245389 & 1745620 & 54.3 & 719.0\\
    \hline
    % B part is not shown for readability
    \hline
   \end{tabular}
  \caption{My benchmark}
\end{table}
```
