# calclex.py

from sly import Lexer


class QiwiLexer(Lexer):
    tokens = {NUM, ID, ELSE, FN, FOR,
              EQ, LT, LE, GT, GE, NE, USE,TIMES,DO, IF, CTRL,
              AND, OR, NAND, NOR, XOR, XNOR, IF_C, PERSIST, IN}

    literals = {'|', '~', '(', ')', '{', '}',
                '[', ']', ';', '-', '+', '*', '/', '=', ',', '.', ':'}

    # String containing ignored characters
    ignore = ' \t'

    # Regular expression rules for tokens
    EQ = r'=='
    LE = r'<='
    LT = r'<'
    GE = r'>='
    GT = r'>'
    NE = r'!='

    @_(r'\d+')
    def NUM(self, t):
        t.value = int(t.value)
        return t

    # Identifiers and keywords
    ID = r'[a-zA-Z_][a-zA-Z0-9_]*'
    ID['else'] = ELSE
    ID['for'] = FOR
    ID['fn'] = FN
    ID['use'] = USE
    ID['if'] = IF
    ID['if_c'] = IF_C
    ID['or'] = OR
    ID['and'] = AND
    ID['nand'] = NAND
    ID['nor'] = NOR
    ID['xor'] = XOR
    ID['xnor'] = XNOR
    ID['persist'] = PERSIST
    ID['in'] = IN
    ID['times'] = TIMES
    ID['do'] = DO
    ID['ctrl'] = CTRL

    ignore_comment = r'//.*'

    # Line number tracking
    @_(r'\n+')
    def ignore_newline(self, t):
        self.lineno += t.value.count('\n')

    def error(self, t):
        print('Line %d: Bad character %r' % (self.lineno, t.value[0]))
        self.index += 1
