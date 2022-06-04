from typing import cast

import argparse

from . import qiwi_lex
from . import qiwi_parser
from . import qiwiast
from . import qiwicg

import qiskit.circuit
import pyzx

# parse command line arguments
parser = argparse.ArgumentParser("qiwi")
parser.add_argument("srcfile", help="qiwi source file path")
parser.add_argument("-o", "--outfile", help="output QASM file path")
parser.add_argument("-O", "--optimize",
                    help="optimize result using ZX calculus", action="store_true")
parser.add_argument(
    "-d", "--draw", help="Draw result circuit", action="store_true")
parser.add_argument("-v", "--verbose", default=0,
                    help="display extra information", action="count")
parser.add_argument("-l", "--dump-lexer",
                    help="display result from lexer", action="store_true")
parser.add_argument("-p", "--dump-parser",
                    help="display result from parser", action="store_true")
args = parser.parse_args()


def info(*arg):
    if args.verbose >= 1:
        print(arg)


def log(*arg):
    if args.verbose >= 2:
        print(arg)


# files yet to be parsed
use_files = set()

# files already parsed
used_files = set()

# Build the lexer and parser
lexer = qiwi_lex.QiwiLexer()
parser = qiwi_parser.QiwiParser()

# create compilation context for global information
context = qiwicg.Context()
context.current_name_space = "self"

# handle main source file
main_source = open(args.srcfile).read()

if args.dump_lexer:
    for token in lexer.tokenize(main_source):
        print(token)

lexer_result = lexer.tokenize(main_source)

# the parsed result is a list of top level ASTNodes
parsed_result = cast(list[qiwiast.ASTNode], parser.parse(lexer_result))

if args.dump_parser:
    print(parsed_result)

used_files.add(args.srcfile)
qiwicg.generate(parsed_result, context)

while (len(use_files) != 0):
    name_space = use_files.pop()
    file = name_space + ".qiwi"
    if file not in used_files:
        context.current_name_space = name_space
        use_source = open(file).read()
        parsed_result = cast(list[qiwiast.ASTNode],
                             parser.parse(lexer.tokenize(use_source)))
        qiwicg.generate(parsed_result, context)
        used_files.add(file)

if ('main', 'self') not in context.functions:
    raise RuntimeError("main() function not defined")
mainfunc = context.functions[('main', 'self')][0]

mainargs = list(map(
    lambda x: list(
        range(context.used_qbits, context.used_qbits + x[1].length)),
    mainfunc.definition.args))
context.current_name_space = 'self'
qasmcode = context.functions[('main', 'self')][0].generate(context, [])
output_lines = qasmcode.output
qasmcode = qasmcode.generate_qasm(context)

if args.optimize:
    zxcircuit = pyzx.Circuit.from_qasm(qasmcode)
    info(zxcircuit.stats())
    g = zxcircuit.to_graph()
    pyzx.simplify.full_reduce(g)
    zxcircuit = pyzx.extract_circuit(g)
    info(zxcircuit)
    qasmcode = zxcircuit.to_qasm()

if args.draw:
    qiskitcirc = qiskit.circuit.QuantumCircuit.from_qasm_str(qasmcode)
    print(qiskitcirc)

output_text = "Output lines: {}".format(', '.join(map(str, output_lines)))
if args.outfile:
    with open(args.outfile, 'w') as outfile:
        outfile.write(qasmcode)
        outfile.write('\n// ' + output_text + '\n')
else:
    print(qasmcode)
    print(output_text)
