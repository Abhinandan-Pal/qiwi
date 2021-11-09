reserved_keywords = {
   'fn'   : 'KEY_FN',
   'if'   : 'KEY_IF',
   'else' : 'KEY_ELSE',
}

# token names
tokens = list(reserved_keywords.values()) + [
    'OP_ADD',
    'OP_SUB',
    'OP_MUL',
    'OP_DIV',

    'LPAREN',
    'RPAREN',
    'LBRACE',
    'RBRACE',
    'LBRACK',
    'RBRACK',
    'ASSIGN',
    'COMMA',
    'COLON',
    'EOS',

    'CST_INT',
    'ID',
    'TYPE_QINT',
]

# Regex only tokens
t_OP_ADD = r'\+'
t_OP_SUB = r'-'
t_OP_MUL = r'\*'
t_OP_DIV = r'/'

t_LPAREN = r'\('
t_RPAREN = r'\)'
t_LBRACE = r'\{'
t_RBRACE = r'\}'
t_LBRACK = r'\['
t_RBRACK = r'\]'
t_ASSIGN = r'='
t_COMMA  = r','
t_COLON  = r':'
t_EOS    = r';'

t_KEY_FN   = r'fn'
t_KEY_IF   = r'if'
t_KEY_ELSE = r'else'

t_ignore_COMMENT = r'//.*'

def t_CST_INT(t):
    r'\d+'
    t.value = int(t.value)
    return t

def t_ID(t):
    r'\w+'
    if t.value == 'q':
        t.type = 'TYPE_QINT'
    else:
        t.type = reserved_keywords.get(t.value, 'ID')
    return t

# track line numbers
def t_newline(t):
    r'\n+'
    t.lexer.lineno += len(t.value)

# Ignored characters
t_ignore  = ' \t'

# Error handling rule
def t_error(t):
    print(f"ERROR: { t.lexer.lineno }: Unknown character '{ t.value[0] }'")
    t.lexer.skip(1)
