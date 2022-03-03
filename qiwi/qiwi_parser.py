from sly import Parser
from . import qiwi_lex
from . import qiwiast
import __main__


class QiwiParser(Parser):
    tokens = qiwi_lex.QiwiLexer.tokens

    start = 'program'

    precedence = (
        ('left', '+', '-'),
        ('left', '*', '/'),
    )
# ------

    @_('')
    def empty(self, p):
        pass

    @_('imports fnprogram')
    def program(self, p):
        __main__.use_files = __main__.use_files.union(set(p.imports))
        return p.fnprogram
# ------

    @_('impt imports')
    def imports(self, p):
        return p[0] + p.imports

    @_('empty')
    def imports(self, p):
        return []

    @_('USE ID AS ID ";"')
    def impt(self, p):
        return [((p[1]+".txt"), p[3])]

# ------
    @_('empty')
    def fnprogram(self, p):
        return []

    @_('funcdef fnprogram')
    def fnprogram(self, p):
        return [p.funcdef] + p.fnprogram
# ------

    @_('FN ID "(" argsdecl ")" "{" statements "}" ')  # for void
    def funcdef(self, p):
        return qiwiast.ASTFuncDef(qiwiast.ASTID(p.ID), None, p.argsdecl, p.statements)
# ------

    @_('empty')
    def argsdecl(self, p):
        return []

    @_('argdecl')
    def argsdecl(self, p):
        return [p.argdecl]

    @_('argdecl "," argsdecl')
    def argsdecl(self, p):
        return [p.argdecl] + p.argsdecl
# ------

    @_('ID ":" ID')
    def argdecl(self, p):
        if p[2] == 'c':
            return (qiwiast.ASTID(p[0]), qiwiast.ASTTypeQ(False, num), False)
        if p[2][0] != 'q':
            raise RuntimeError(f"Unknown type {p[2]}")

        if (p[2][1:] == 'N'):
            num = None
        else:
            num = int(p[2][1:])
        return (qiwiast.ASTID(p[0]), qiwiast.ASTTypeQ(True, num), False)

    @_('PERSIST ID ":" ID')
    def argdecl(self, p):
        if p[3] == 'c':
            raise RuntimeError(f"PERSIST cant be used on classical data")
        if p[3][0] != 'q':
            raise RuntimeError(f"Unknown type {p[3]}")

        if (p[3][1:] == 'N'):
            num = None
        else:
            num = int(p[3][1:])
        return (qiwiast.ASTID(p[1]), qiwiast.ASTTypeQ(True, num), True)
# ------

    @_('expr')  # basically return statement
    def statements(self, p):
        return [p.expr]

    @_('statement ";" statements')
    def statements(self, p):
        return [p[0]] + p[2]
# ------

    @_('assignment')
    def statement(self, p):
        return p.assignment

    @_('if_qc_state')
    def statement(self, p):
        return p.if_qc_state
# ------

    @_('ID "=" expr')
    def assignment(self, p):
        return qiwiast.ASTAssignment(qiwiast.ASTID(p.ID), p.expr)

    @_('ID "[" NUM "]" "=" expr')
    def assignment(self, p):
        return qiwiast.ASTAssignment(qiwiast.ASTID(p.ID), p.expr, index=p.NUM)

    @_('ID ":" ID "=" expr')
    def assignment(self, p):
        if p[2] == 'c':
            return qiwiast.ASTAssignment(qiwiast.ASTID(p[0]), p.expr, type=qiwiast.ASTTypeQ(False, None))
        if p[2][0] != 'q':
            raise RuntimeError(f"Unknown type {p[2]}")

        if (p[2][1:] == 'N'):
            num = None
        else:
            num = int(p[2][1:])
        return qiwiast.ASTAssignment(qiwiast.ASTID(p[0]), p.expr, type=qiwiast.ASTTypeQ(True, num))
# ------

    @_('expr "+" expr',
       'expr "-" expr',
       'expr "*" expr',
       'expr "/" expr')
    def expr(self, p):
        return qiwiast.ASTExpBinary(p[1], p[0], p[2])

    @_('ID')
    def expr(self, p):
        return qiwiast.ASTID(p.ID)

    @_(' "|" expr "|" ')
    def expr(self, p):
        return qiwiast.ASTlen(p.expr)

    @_('"(" expr ")"')
    def expr(self, p):
        return p.expr

    @_('NUM')
    def expr(self, p):
        return qiwiast.ASTInt(p.NUM)

    @_('ID "[" NUM "]"')
    def expr(self, p):
        return qiwiast.ASTIndexedID(p.ID, p.NUM)

    @_('ID "(" args ")"')
    def expr(self, p):
        return qiwiast.ASTFuncCall(qiwiast.ASTID(p.ID), p.args)

    @_('ID "." ID "(" args ")"')
    def expr(self, p):
        return qiwiast.ASTFuncCall(qiwiast.ASTID(p[2]), p.args, p[0])
# ------

    @_('empty')
    def args(self, p):
        return []

    @_('arg')
    def args(self, p):
        return [p.arg]

    @_('arg "," args')
    def args(self, p):
        return [p.arg] + p.args
# -----

    @_('expr')
    def arg(self, p):
        return p.expr
# -----

    @_('expr EQ expr',
       'expr LE expr',
       'expr LT expr',
       'expr GE expr',
       'expr GT expr',
       'expr NE expr')
    def bexpr(self, p):
        return qiwiast.ASTRelational(p[1], p[0], p[2])

    @_('expr')
    def bexpr(self, p):
        return p.expr
# -----

    @_('IF_QC "(" if_qc_expr ")" "{" expr "}"')
    def if_qc_state(self, p):
        return qiwiast.ASTIf_qc(p.if_qc_expr, p.expr)

    @_('bexpr')
    def if_qc_expr(self, p):
        return (p.bexpr, 'SINGLE', None)

    @_('bexpr op_qc bexpr')
    def if_qc_expr(self, p):
        return (p[0], p[1], p[2])

    @_('OR', 'AND', 'NOR',
       'NAND', 'XOR', 'XNOR')
    def op_qc(self, p):
        return p[0]
# -----

    @_('if_c')
    def statement(self, p):
        a, b = p.if_c
        return qiwiast.ASTIf_c(a, b, None)

    @_('if_c ELSE "{" statements "}"')
    def statement(self, p):
        a, b = p.if_c
        return qiwiast.ASTIf_c(a, b, p.statements)

    @_('IF_C "(" bexpr ")" "{" statements "}"')
    def if_c(self, p):
        return (p.bexpr, p.statements)
# -----

    @_('if_qm_expr')
    def expr(self, p):
        a, b = p.if_qm_expr
        return qiwiast.ASTIf_qm(a, b)

    @_('if_qm_expr ELSE "{" expr "}"')
    def expr(self, p):
        a, b = p.if_qm_expr
        return qiwiast.ASTIf_qm(a, b, p.expr)

    @_('IF_QM "(" expr ")" "{" expr "}"')
    def if_qm_expr(self, p):
        return (p.expr0, p.expr1)
# -----

    @_('for_c')
    def statement(self, p):
        return p.for_c

    @_('FOR ID IN "[" expr ":" expr ":" expr  "]" "{" statements "}"')
    def for_c(self, p):
        return qiwiast.ASTFor_c(qiwiast.ASTID(p.ID), p.expr0, p.expr1, p.expr2, p.statements)
# -----

    def error(self, p):
        if p:
            print("Syntax error at token", p.type)
            # Just discard the token and tell the parser it's okay.
            self.errok()
        else:
            print("Syntax error at EOF")
