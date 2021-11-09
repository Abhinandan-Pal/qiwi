from .qiwilexer import tokens
 
from . import qiwiast
import __main__
start = 'program'

def p_program_import_fnprogram(p):
    'program : imports fnprogram'
    __main__.use_files = p[1]
    #print(p[1])
    p[0] = p[2]

def p_imports_import_imports(p):
    'imports : import imports'
    p[0] = p[1] + p[2]
    
def p_imports_blank(p):
    'imports : '
    p[0] = []

def p_import_use(p):
    'import : KEY_USE ID EOS'
    p[0] = [((p[2]+".txt"),"self")]

def p_fnprogram_blank(p):
    'fnprogram :'
    p[0] = []

def p_fnprogram_functions(p):
    'fnprogram : funcdef fnprogram'
    p[0] = [p[1]] + p[2]

def p_funcdef(p):
    'funcdef : KEY_FN ID LPAREN argsdecl RPAREN type LBRACE statements RBRACE'
    p[0] = qiwiast.ASTFuncDef(qiwiast.ASTID(p[2]), p[6], p[4], p[8])

def p_funcdef_void(p):
    'funcdef : KEY_FN ID LPAREN argsdecl RPAREN LBRACE statements RBRACE'
    p[0] = qiwiast.ASTFuncDef(qiwiast.ASTID(p[2]), None, p[4], p[7])

def p_argsdecl_null(p):
    'argsdecl :'
    p[0] = []

def p_argsdecl_argdecl(p):
    'argsdecl : argdecl'
    p[0] = [p[1]]

def p_argsdecl_argdecls(p):
    'argsdecl : argdecl COMMA argsdecl'
    p[0] = [p[1]] + p[3]

def p_argdecl(p):
    'argdecl : ID COLON ID'
    if p[3][0] != 'q':
        raise RuntimeError(f"Unknown type {p[3]}")

    if (p[3][1:] == 'N'):
        num = None
    else:    
        num = int(p[3][1:])
    p[0] = (qiwiast.ASTID(p[1]), qiwiast.ASTTypeQ(num))

def p_statements_expression(p):
    'statements : expression'
    p[0] = [p[1]]

def p_statements_statements(p):
    'statements : statement EOS statements'
    p[0] = [p[1]] + p[3]

def p_statement(p):
    'statement : assignment'
    p[0] = p[1]

def p_assignment(p):
    'assignment : ID ASSIGN expression'
    p[0] = qiwiast.ASTAssignment(qiwiast.ASTID(p[1]), p[3])

def p_assignment_typed(p):
    'assignment : ID COLON ID ASSIGN expression'
    if p[3][0] != 'q':
        raise RuntimeError(f"Unknown type {p[3]}")

    num = int(p[3][1:])
    p[0] = qiwiast.ASTAssignment(qiwiast.ASTID(p[1]), p[5], qiwiast.ASTTypeQ(num))

def p_expression_arithmatic(p):
    '''expression : LPAREN expression OP_ADD expression RPAREN
                  | LPAREN expression OP_SUB expression RPAREN
                  | LPAREN expression OP_MUL expression RPAREN
                  | LPAREN expression OP_DIV expression RPAREN'''
    p[0] = qiwiast.ASTExpBinary(p[3], p[2], p[4])

def p_expression_number(p):
    'expression : CST_INT'
    p[0] = qiwiast.ASTInt(p[1])

def p_expression_id(p):
    'expression : ID'
    p[0] = qiwiast.ASTID(p[1])

def p_expression_indexedid(p):
    'expression : ID LBRACK CST_INT RBRACK'
    p[0] = qiwiast.ASTIndexedID(p[1], p[3])

def p_expression_call(p):
    'expression : ID LPAREN args RPAREN'
    p[0] = qiwiast.ASTFuncCall(qiwiast.ASTID(p[1]), p[3])

def p_expression_import_call(p):
    'expression : ID COLON ID LPAREN args RPAREN'
    p[0] = qiwiast.ASTFuncCall(qiwiast.ASTID(p[3]), p[5],p[1])

def p_args_null(p):
    'args :'
    p[0] = []

def p_args_arg(p):
    'args : arg'
    p[0] = [p[1]]

def p_args_args(p):
    'args : arg COMMA args'
    p[0] = [p[1]] + p[3]

def p_arg(p):
    'arg : expression'
    p[0] = p[1]

#def p_type(p):
#    'type : TYPE_QINT LBRACK RBRACK'
#    p[0] = qiwiast.ASTTypeQ(None)

def p_type_len(p):
    'type : TYPE_QINT LBRACK CST_INT RBRACK'
    p[0] = qiwiast.ASTTypeQ(p[3])

# Error rule for syntax errors
def p_error(p):
    print(f"Syntax error at: {p}")
