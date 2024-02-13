#!/usr/bin/env python3

import argparse
from io import StringIO
import json
import math
import sys

# This script produces a LaTeX table from a JSON benchmark output by script run_benchmark.py
# Each run in the input file correspond to a row in the table, and each algorithm in a row corresponds to a column.
# The table caption corresponds to the 'name' of the benchmark.

# Check if the column/sub_column has to be used for the generated table
# table_description : JSON description of table
# column: column name
# sub_column: sub-column name
# return True if either no 'enabled' flag is enabled in specified or if the flag is "True"
def sub_column_is_enabled(table_description, column, sub_column):
    assert column in table_description["columns"]
    col = table_description["columns"][column]
    assert sub_column in col
    return not ("enabled" in col[sub_column]) or col[sub_column]["enabled"] == "True"


# Computes the list of enabled sub-columns for a given column
# table_description : JSON description of table
# column: column name
# return The list of enabled sub-columns of 'column'
def enabled_sub_columns(table_description, column):
    assert column in table_description["columns"]
    return [sc for sc in table_description["columns"][column] if sub_column_is_enabled(table_description, column, sc)]


# Compute LaTeX tabular columns description
# table_description : JSON description of table
# returns a string representation of LaTeX tabular columns from table_description
def compute_LaTeX_tabular_columns(table_description):
    str = "|l|"  # column for models
    for column in table_description["columns"]:
        str += "|"
        for sub_column in enabled_sub_columns(table_description, column):
            str += "r|"
    return str


# Compute LaTeX column header rows
# table_description : JSON description of table
# retuns a string with two rows, the first one corresponds to the columns in table_description
# and the second one corresponds to the sub columns in table_description
def compute_LaTeX_column_headers(table_description):
    # Columns header
    s = "Models "  # first column
    sc_h = "" # sub-columns headers
    for column in table_description["columns"]:
        sub_columns = enabled_sub_columns(table_description, column)
        sub_column_count = len(sub_columns)
        s += "& \multicolumn{" + str(sub_column_count) + "}{c|}{" + column + "} "
        for sub_column in sub_columns:
            sc_h += " & " + sub_column
    s += "\\\\\n" + sc_h + "\\\\\n"
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


# Evaluate percent expression
# stats : stats dict
# expr : percent expression
# returns the value of expression expr evaluated on stats
def evaluate_percent(stats, expr):
    assert len(expr) == 2
    num = None
    den = None
    for e in expr:
        if e == "num":
            num = evaluate(stats, expr[e])
        else:
            den = evaluate(stats, expr[e])
    if den == None:
        print("*** ERROR: missing 'den' in ", expr)
        sys.exit()
    if num == None:
        print("*** ERROR: missing 'num' in", expr)
        sys.exit()
    if den == 0:
        assert num == 0
        return 100.00
    return math.floor((100.0 * num / den) * 100) / 100


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
    elif "percent" in expr:
        return evaluate_percent(stats, expr["percent"])
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
    sub_columns = enabled_sub_columns(table_description, column)
    sub_columns_count = len(sub_columns)
    if not column in data["stats"][row]:
        print("*** WARNING: missing", column, "in row", row)
        return " & \multicolumn{" + str(sub_columns_count) + "}{c|}{missing}"
    status = data["stats"][row][column]["status"]
    if status != "success":
        return " & \multicolumn{" + str(sub_columns_count) + "}{c|}{" + status + "}"
    s = ""
    for sub_column in sub_columns:
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


# Check if the given parameter exists in the table description
# table_description : JSON description of table
# parameter : name of the parameter to look for
# return True if the parameter is specified or False if not
def has_parameter(table_description, parameter):
    return "parameters" in table_description and parameter in table_description["parameters"]


# Return the JSON value of given paramter
# table_description : JSON description of table
# parameter : name of the parameter to look for
# return the value of `parameter` if it exists or None if not
def get_parameter(table_description, parameter):
    if has_parameter(table_description, parameter):
        return table_description["parameters"][parameter]
    return None


# Check in table_description if on the tabular environment must be generated
# table_description : JSON description of table
# return True if the parameter `tabular` exists and is "True"
def parameter_only_tabular(table_description):
    only_tabular = get_parameter(table_description, "tabular")
    return only_tabular == "True"


# Create a LaTeX table from a JSON benchmark results (see file format above)
# data : JSON benchmark results
# table_description : JSON description of table
def create_LaTeX_table(data, table_description):
    assert "name" in data
    tabular_columns = compute_LaTeX_tabular_columns(table_description)
    tabular_header_rows = compute_LaTeX_column_headers(table_description)
    tabular_rows = compute_LaTeX_rows(data, table_description)
    tabular_only = parameter_only_tabular(table_description)
    table = "" if tabular_only else "\\begin{table}\n"
    table += "  \\begin{tabular}{" + tabular_columns + "}\n"
    table += "    \\hline\n"
    table += tabular_header_rows
    table += "    \\hline\n"
    table += tabular_rows
    table += "    \\hline\n"
    table += "   \\end{tabular}\n"
    if not tabular_only:
        table_name = f"{data['name']}"
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
