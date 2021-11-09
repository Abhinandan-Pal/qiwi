from typing import cast

import subprocess
import sys
import ply.lex as lex
import ply.yacc as yacc

from . import qiwilexer
from . import qiwiparser
from . import qiwiast
from . import qiwicg


use_files = []

# Build the lexer
lexer = lex.lex(module=qiwilexer)

# test
main_source = open(sys.argv[1]).read()
lexer.input(main_source)

while True:
    tok = lexer.token()
    if not tok: # EOF
        break
    #print(tok)


parser = yacc.yacc(module=qiwiparser)

parsed_result = parser.parse(main_source)

context = qiwicg.Context()
context.current_name_space = "self"
qiwicg.generate(parsed_result,context)

collector = parsed_result
for file,name_space in use_files:
    context.current_name_space = name_space
    use_sorce = open(file).read()
    parsed_result = parser.parse(use_sorce)
    qiwicg.generate(parsed_result,context)
    collector += parsed_result
print(collector)


mainfunc = context.functions[('main','self')]
mainargs = list(map(lambda x: list(range(context.used_qbits, context.used_qbits + x[1].length)), mainfunc.definition.args))
code = context.functions[('main','self')].generate(context, []).generate_qasm(context)
#subprocess.run(['xclip', '-selection', 'clipboard', '-in'], input=code.encode('utf-8'))
print(code)
