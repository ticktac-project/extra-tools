#!/usr/bin/env python3

import argparse
from io import StringIO
import json
import math
import sys

# This script produces a LaTeX table from a JSON benchmark output by script run_benchmark.py
# Each run in the input file correspond to a row in the table, and each algorithm in a row corresponds to a column.
# The table caption corresponds to the 'name' of the benchmark.


# Compute LaTeX tabular columns description
# table_description : JSON description of table
# returns a string representation of LaTeX tabular columns from table_description
def compute_LaTeX_tabular_columns(table_description):
    str = "|l|"  # column for models
    for column in table_description["columns"]:
        str += "|"
        for sub_column in table_description["columns"][column]:
            str += "r|"
    return str


# Compute LaTeX column header rows
# table_description : JSON description of table
# retuns a string with two rows, the first one corresponds to the columns in table_description
# and the second one corresponds to the sub columns in table_description
def compute_LaTeX_column_headers(table_description):
    # Columns header
    s = "Models "  # first column
    for column in table_description["columns"]:
        sub_column_count = len(table_description["columns"][column])
        s += "& \multicolumn{" + str(sub_column_count) + "}{c|}{" + column + "} "
    s += "\\\\\n"
    # Sub columns header
    for column in table_description["columns"]:
        for sub_column in table_description["columns"][column]:
            s += " & " + sub_column
    s += "\\\\\n"
    return s


# Evaluate value expression
# stats : stats dict
# expr : value expression
# returns the value of expression expr evaluated on stats, with the type specified in expr
def evaluate_value(stats, expr):
    value_name = expr["name"]
    if not value_name in stats:
        print("*** ERROR: unknown value name", value_name)
        sys.exit()
    value = stats[value_name]
    if not "type" in expr:
        return value
    elif expr["type"] == "int":
        return int(value)
    elif expr["type"] == "float":
        return float(value)
    else:
        print("*** ERROR: unknown type name", expr["type"])
        sys.exit()


# Evaluate divide expression
# stats : stats dict
# expr : divide expression
# returns the value of expression expr evaluated on stats
def evaluate_divide(stats, expr):
    assert len(expr) == 2
    divisor = None
    value = None
    for e in expr:
        if e == "by":
            divisor = int(expr["by"])
        else:
            value = evaluate(stats, {e: expr[e]})
    if divisor == None:
        print("*** ERROR: missing 'by' in ", expr)
        sys.exit()
    if divisor == 0:
        print("*** ERROR: division by 0")
        sys.exit()
    if value == None:
        print("*** ERROR: missing value to divide in", expr)
        sys.exit()
    return value / divisor


# Evaluate round expression
# stats : stats dict
# expr : round expression
# returns the value of expression expr evaluated on stats
def evaluate_round(stats, expr):
    assert len(expr) == 2
    decimal = None
    value = None
    for e in expr:
        if e == "decimal":
            decimal = int(expr["decimal"])
        else:
            value = evaluate(stats, {e: expr[e]})
    if decimal == None:
        print("*** ERROR: missing 'decimal' in ", expr)
        sys.exit()
    if value == None:
        print("*** ERROR: missing value to round in", expr)
        sys.exit()
    factor = pow(10, decimal)
    return math.floor(value * factor) / factor


# Evaluate expression from table_description
# stats : stats dict
# expr : JSON expression
# returns the value obtained from evaluation of expr over stats
def evaluate(stats, expr):
    if "value" in expr:
        return evaluate_value(stats, expr["value"])
    elif "divide" in expr:
        return evaluate_divide(stats, expr["divide"])
    elif "round" in expr:
        return evaluate_round(stats, expr["round"])
    else:
        print("*** ERROR: unexpected expression", expr)
        sys.exit()


# Compute a LaTeX table column in a row
# data : JSON benchmark results
# table_description : JSON description of table
# row : row name
# column : column name
# returns a string with LaTeX tabular column in row with values computed from data according to
# table_description
def compute_LaTeX_row_column(data, table_description, row, column):
    assert row in table_description["rows"]
    assert column in table_description["columns"]
    assert row in data["stats"]
    sub_columns_count = len(table_description["columns"][column])
    if not column in data["stats"][row]:
        print("*** WARNING: missing", column, "in row", row)
        return " & \multicolumn{" + str(sub_columns_count) + "}{c|}{missing}"
    status = data["stats"][row][column]["status"]
    if status != "success":
        return " & \multicolumn{" + str(sub_columns_count) + "}{c|}{" + status + "}"
    s = ""
    for sub_column in table_description["columns"][column]:
        expr = table_description["columns"][column][sub_column]
        value = evaluate(data["stats"][row][column], expr)
        s += " & " + str(value)
    return s


# Compute one LaTeX table row
# data : JSON benchmark results
# table_description : JSON description of table
# row : row name
# returns a string with LaTeX tabular row with values computed from data according to
# table_description
def compute_LaTeX_row(data, table_description, row):
    assert row in table_description["rows"]
    if not row in data["stats"]:
        print("*** WARNING: missing row", row)
        return ""
    s = row
    for column in table_description["columns"]:
        s += compute_LaTeX_row_column(data, table_description, row, column)
    return s


# Compute LaTeX table rows
# data : JSON benchmark results
# table_description : JSON description of table
# returns a string with LaTeX tabular rows with values computed from data according to
# table_description
def compute_LaTeX_rows(data, table_description):
    s = ""
    for row in table_description["rows"]:
        if row == "":
            s += "\\hline\n"
        else:
            s += compute_LaTeX_row(data, table_description, row) + "\\\\\n"
    return s


# Create a LaTeX table from a JSON benchmark results (see file format above)
# data : JSON benchmark results
# table_description : JSON description of table
def create_LaTeX_table(data, table_description):
    assert "name" in data
    tabular_columns = compute_LaTeX_tabular_columns(table_description)
    tabular_header_rows = compute_LaTeX_column_headers(table_description)
    tabular_rows = compute_LaTeX_rows(data, table_description)
    table_name = f"{data['name']}"
    table = "\\begin{table}\n"
    table += "  \\begin{tabular}{" + tabular_columns + "}\n"
    table += "    \\hline\n"
    table += tabular_header_rows
    table += "    \\hline\n"
    table += tabular_rows
    table += "    \\hline\n"
    table += "   \\end{tabular}\n"
    table += f"  \\caption" + "{" + table_name + "}\n"
    table += "\\end{table}\n"
    return table


# Parse command-line
parser = argparse.ArgumentParser()
parser.add_argument("file", nargs=1, help=""" Benchmark JSON output""")
parser.add_argument(
    "-t", required=True, help=""" JSON description of table rows and columns"""
)
parser.add_argument("-o", help=""" Output file name""")
args = parser.parse_args()

table_description_file = open(args.t, "r")
table_description = json.load(table_description_file)
table_description_file.close()

results_file = open(args.file[0], "r")
results = json.load(results_file)
results_file.close()

table = create_LaTeX_table(results, table_description)

if args.o == None:
    print(table)
else:
    with open(args.o, "w") as table_file:
        table_file.write(table)
        table_file.close()


# Extract satistics
# tchecker_stats : dict of stats output by TChecker tool
# format : filter and map to aply on tchecker_stats (see format above)
# return a dict of stats extracted from tchecker_stats forllowing format
def extract_stats(tchecker_stats, format):
    stats = {"status": tchecker_stats["status"]}
    if tchecker_stats["status"] == "success":
        for d in format:
            if d in tchecker_stats:
                name = format[d]["name"] if "name" in format[d] else d
                value = (
                    float(tchecker_stats[d])
                    if "type" in format[d] and format[d]["type"] == "float"
                    else int(tchecker_stats[d])
                )
                if "divide" in format[d]:
                    value /= format[d]["divide"]
                if "decimal" in format[d]:
                    ndecimal = int(format[d]["decimal"])
                    value *= pow(10, ndecimal)
                    value = math.floor(value)
                    value /= pow(10, ndecimal)
                stats[name] = value
            else:
                print("Unknown data", d)
    return stats
