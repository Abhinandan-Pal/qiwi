# calclex.py

from sly import Lexer

class QiwiLexer(Lexer):
    tokens = { NUM, ID, WHILE, IF, ELSE, PRINT, FN,
               EQ, LT, LE, GT, GE, NE, USE, AS, 
               IF_QC, IF_QM ,AND, OR, NAND, NOR, XOR, XNOR, PERSIST }


    literals = { '~','(', ')', '{', '}', '[',']' ,';' , '-' , '+' , '*' , '/' , '=' , ',' , '.', ':'}

    # String containing ignored characters
    ignore = ' \t'

    # Regular expression rules for tokens
    EQ      = r'=='
    LE      = r'<='
    LT      = r'<'
    GE      = r'>='
    GT      = r'>'
    NE      = r'!='


    @_(r'\d+')
    def NUM(self, t):
        t.value = int(t.value)
        return t

    # Identifiers and keywords
    ID = r'[a-zA-Z_][a-zA-Z0-9_]*'
    ID['if'] = IF
    ID['else'] = ELSE
    ID['while'] = WHILE
    ID['print'] = PRINT
    ID['fn']    = FN
    ID['use']  = USE
    ID['as']  = AS
    ID['if_qc']  = IF_QC
    ID['if_qm']  = IF_QM
    ID['or'] = OR
    ID['and'] = AND
    ID['nand'] = NAND
    ID['nor'] = NOR 
    ID['xor'] = XOR
    ID['xnor'] = XNOR
    ID['persist'] = PERSIST


    ignore_comment = r'//.*'

    # Line number tracking
    @_(r'\n+')
    def ignore_newline(self, t):
        self.lineno += t.value.count('\n')

    def error(self, t):
        print('Line %d: Bad character %r' % (self.lineno, t.value[0]))
        self.index += 1
