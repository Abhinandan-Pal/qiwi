from typing import cast

import subprocess
import sys
import ply.lex as lex
import ply.yacc as yacc

from . import qiwilexer
from . import qiwiparser
from . import qiwiast
from . import qiwicg

# Build the lexer
lexer = lex.lex(module=qiwilexer)

# test
data = open(sys.argv[1]).read()
lexer.input(data)

while True:
    tok = lexer.token()
    if not tok: # EOF
        break
    #print(tok)

parser = yacc.yacc(module=qiwiparser)

parsed_result = parser.parse(data)
print(parsed_result)

context = qiwicg.generate( parsed_result)
mainfunc = context.functions['main']
mainargs = list(map(lambda x: list(range(context.used_qbits, context.used_qbits + x[1].length)), mainfunc.definition.args))
code = context.functions['main'].generate(context, []).generate_qasm(context)
#subprocess.run(['xclip', '-selection', 'clipboard', '-in'], input=code.encode('utf-8'))
print(code)
