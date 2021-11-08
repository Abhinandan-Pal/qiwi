from sly import Parser
from qiwi_lex import QiwiLexer

class QiwiParser(Parser):
	tokens = QiwiLexer.tokens

	start = 'program'

	precedence = (
       ('left', '+', '-'),
       ('left', '*', '/'),
       ('right', UMINUS)		# Unary minus operator
    )

	@_('')
	def empty(self, p):
    	pass
#------
    @_('empty')
	def program(self, p):
		return []

	@_('funcdef program')
	def program(self, p):
		return [p.funcdef] + p.program
#------
	@_('FN ID "(" argsdecl ")" type "{" statements "}" ')
	def funcdef(self, p):
		return ASTFuncDef(ASTID(p.ID), p.type, p.argsdecl, p.statements )

	@_('FN ID "(" argsdecl ")" "{" statements "}" ')  # for void
	def funcdef(self, p):
		return  ASTFuncDef(ASTID(p.ID), None , p.argsdecl, p.statements )
#------
	@_('empty')
	def argsdecl(self, p):
		return []

	@_('argdecl')
	def argsdecl(self, p):
		return [p.argdecl]

	@_('argdecl "," argsdecl')
	def argsdecl(self, p):
		return [p.argdecl] + p.argsdecl
#------
	@_('ID ":" ID')
	def argdecl(self, p):
		if p[3][0] != 'q':
			raise RuntimeError(f"Unknown type {p[3]}")

		num = int(p[3][1:])
		return (ASTID(p[1]), ASTTypeQ(num))
#------
	@_('expr')						#basically return statement
	def statements(self, p):
		return [p.expr]

	@_('statement ";" statements')
	def statements(self, p):
		return [p.expr]	+ p.statements
#------
	@_('assignment')
	def statement(self, p):
		return p.assignment
#------
	@_('ID "=" expr')
	def assignment(self, p):
		return ASTAssign(ASTID(p.ID), p.expr)			# might be a bug along with line 77

	@_('ID ":" ID "=" expr')
	def assignment(self, p):
		if p[3][0] != 'q':
			raise RuntimeError(f"Unknown type {p[3]}")

		num = int(p[3][1:])
		return ASTAssign(ASTID(p.ID), p.expr , ASTTypeQ(num))
#------
	@_('expr "+" expr',
   'expr "-" expr',
   'expr "*" expr',
   'expr "/" expr')
	def expr(self, p):
    	return ASTExpBinary(p[3], p[2], p[1])

    @_('ID')
    def expr(self, p):
    	return ASTID(p.ID)

    @_('ID "[" NUM "]"')
    def expr(self, p):
    	return ASTIndexedID(p.ID,p.NUM)

    @_('ID "(" args ")"')
    def expr(self, p):
    	return ASTFuncCall(ASTID(p.ID,p.args))
#------
	@_('empty')
	def args(self, p):
		return []

	@_('arg')
	def args(self, p):
		return [p.arg]

	@_('arg "," args')
	def args(self, p):
		return [p.arg] + p.args
#-----
	@_('expr')
	def arg(self, p):
		return p.expr
#-----
	@_('QINT "[" NUM "]"')
	def type(self, p)
		return ASTTypeQ(p.num) 
#-----
	def error(self, p):
    	if p:
         	print("Syntax error at token", p.type)
         	# Just discard the token and tell the parser it's okay.
        	 self.errok()
     	else:
        	print("Syntax error at EOF")