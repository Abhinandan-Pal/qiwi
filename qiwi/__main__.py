from typing import cast

import subprocess
import sys
import ply.lex as lex
import ply.yacc as yacc

from . import qiwi_lex
from . import qiwi_parser
from . import qiwiast
from . import qiwicg


use_files = set()
used_files = set()

# Build the lexer
lexer = qiwi_lex.QiwiLexer()
parser = qiwi_parser.QiwiParser()

# test
main_source = open(sys.argv[1]).read()

for tok in lexer.tokenize(main_source):
    #print(tok)
    pass
print("LEX SUCCESS")

parsed_result = parser.parse(lexer.tokenize(main_source))
used_files.add(sys.argv[1])

context = qiwicg.Context()
context.current_name_space = "self"
qiwicg.generate(parsed_result,context)

collector = parsed_result
print(f"USE FILE : {use_files}")
while (len(use_files)!=0):
    print(f"USE FILE : {use_files}")
    file,name_space = use_files.pop()
    if file not in used_files:
        context.current_name_space = name_space
        use_source = open(file).read()
        parsed_result = parser.parse(lexer.tokenize(use_source))
        qiwicg.generate(parsed_result,context)
        collector += parsed_result
        used_files.add(file)

print(collector)


mainfunc = context.functions[('main','self')][0]
mainargs = list(map(lambda x: list(range(context.used_qbits, context.used_qbits + x[1].length)), mainfunc.definition.args))
code = context.functions[('main','self')][0].generate(context, []).generate_qasm(context)
#subprocess.run(['xclip', '-selection', 'clipboard', '-in'], input=code.encode('utf-8'))
print(code)
