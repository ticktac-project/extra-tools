dot2dot
========

Description
-----------

This tool allows to add/modify attributes of the nodes and edges of a graph represented in the [DOT language](https://graphviz.org/doc/info/lang.html). The modification of attributes is conditional and can be computed from the values of other attributes. Unconditional modification can also be applied on the graph. **dot2dot** is written in Python and requires Python 3 with the module [pygraphviz](https://pygraphviz.github.io/) to be executed.

Usage
-----
The modification(s) can be specified as command line arguments or in a JSON file. If both are provided, the command line arguments may overwrite the changes provided in the JSON file. The format of the JSON file is described below.

To execute this tool, simply run:

    ./dot2dot.py [graph] [options]
    where:
        graph is a dot/graphviz file or - if the graph should be read from the standard input.

run command `./dot2dot.py -h` to get help on the options

Application of a style
----------------------
This tool can be used to highlight some pieces of information in the nodes and edges of the graph by applying a style.
Here is an example of a JSON file for this tool:

    {
       "style1" : {
         "object" : "node",
         "condition" : {
           "a" : "[0-9]+",
           "b" : "3"
         },
         "updates" : {
            "color" : "blue",
            "style" : "filled"
            }
        },

        "style2" : {
            "object" : "edge",
            "condition" : {
                "b" : "2"
            },
            "updates" : {
                "color" : "yellow"
            }
        },

        "style3" : {
            "object" : "graph",
            "updates" : {
                "label" : "Example graph",
                "fontname" : "Helvetica-Oblique",
    		    "fontsize" : "36"
            }
        }
    }

A style file is made of several style sections. Each style section has a name (*style1*, *style2* and *style3* in the example above) and is made of up to three components:
- *object* is one of "graph", "node" or "edge": it specifies on which elements of the graph the style shall be applied.
- *condition* is a list of pairs *"attribute": "expression"* that is matched by all objects of the selected type such that each attribute in the condition has a value that matches the corresponding regular expression. The regular expression should follow the Python regular expression language. As an example, *style1* above matches all nodes with an attribute *a* that contains a number and an attribute *b* which has value 3. The condition is optional for nodes and edges, and no condition shall be provided for the graph. If no condition is provided, all objects of the selected type match.
- finally, *updates* is a list of attributes that will be added (or modified) on the selected objects. This tool can be used to set any attribute on graphs, nodes and edges. In particular, it can be used to set [attributes recognised by the graphviz tool](https://graphviz.org/doc/info/attrs.html).

All values in the JSON file must be strings.

As an example, consider the following dot graph:

    digraph foo {
        n1 [color=blue, b=3, a=4];
        n2 ;
        n3 [color=green, label="n3", a=3];
        n1 -> n2 [color=orchid, b=2, a=5];
        n3 -> n1 [color=cyan, b=1];
    }

The command `./dot2dot.py example.dot -s example.json` where example.dot is the graph above and example.json is the JSON file above produces the following graph:

    digraph foo {
            graph [fontname="Helvetica-Oblique",
                   fontsize=36,
                   label="Example graph"
            ];
            n1      [a=4,
                    b=3,
                    color=blue,
                    style=filled];
            n1 -> n2        [a=5,
                    b=2,
                    color=yellow];
            n3      [a=3,
                    color=green,
                    label=n3];
            n3 -> n1        [b=1,
                    color=cyan];
    }

As specified in the JSON file, the node n1 where *a* is a positive integer and *b* equals 3 has been colored in blue and the edge `n1 -> n2` where *b* equals 2 has been colored in yellow. The other elements remain unchanged.


Compute attributes from the value of others
-------------------------------------------

The modification can also be specified using the command line options `-g` for graph, `-n` for nodes and `-e` for edges and the new attributes' values can be
computed from other attributes' values. The first argument following `-n` or `-e` is a condition that selects the nodes/edges on which the style shall be applied. The modifications are specified by the next arguments. Unconditional styles are specified by the empty condition *""*.  The condition is followed by attributes assignments of the form *a=foo* that sets the value of attribute *a* to value *foo*. For instance, option `-n a=foo` specifies that the value of attribute *a* is set to *foo* for each node in the graph. The value of attributes can be computed from the value of other attributes using references. A reference *%a%* denotes the value of attribute *a*. Graph style `-g` should not be given any condition.

As an example, consider the following graph expressed in the DOT language:

    digraph example {
        n1 [a=4, b=toto];
        n2 ;
        n3 [a=6];
        n1 -> n2 [c=5, d=tata];
        n3 -> n1 [c=6];
    }

The command `./dot2dot.py example.dot -n "" label="%a%, %b%" -e "" label=edge`, where `example.dot` contains the graph above, outputs a graph in dot language whose edges are labelled "edge" and whose nodes are labelled *"%a%, %b%"* where *%a%* and *%b%* are replaced by the values of attributes *a* and *b* of the node. When a node does not possess an attribute *a*, the value of *%a%* is the empty string "". The command above outputs the following graph:

    digraph example {
            node [label="\N"];
            n1      [a=4,
                    b=toto,
                    label="4, toto"];
            n2      [label=", "];
            n1 -> n2        [c=5,
                    d=tata,
                    label="edge"];
            n3      [a=6,
                    label="6, "];
            n3 -> n1        [c=6,
                    label="edge"];
    }

The value of a reference *%a%* is the value of the attribute in the input file, even when the command overwrites the attribute. For instance, the command `./dotattributes.py example.dot -n "" a="%b%" -n "" c="%a%"` will set the value of attribute *c* to the value of attribute *a* in the input file, and not the value of attribute *b*. On the example above, we end up with node *n1* as follows: `n1 [a=toto,b=toto,c=4]`.


It is naturally possible to combine the computation of attributes from other attributes' value and the application of a style.
If both a JSON style file and command line options are provided, the command line options may overwrite the style specified in the JSON file.
