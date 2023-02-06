from enum import IntEnum

class Tokens(IntEnum):
    errorToken = 0

    timesToken = 1          # '*'
    divToken = 2            # '/'

    plusToken = 11          # '+'
    minusToken = 12         # '-'

    eqlToken = 20           # '=='
    neqToken = 21           # '!='
    lssToken = 22           # '<'
    geqToken = 23           # '>='
    leqToken = 24           # '<='
    gtrToken = 25           # '>'

    periodToken = 30        # '.'
    commaToken = 31         # ','
    openbracketToken = 32   # '['
    closebracketToken = 34  # ']'
    closeparenToken = 35    # ')'

    becomesToken = 40       # '<-'
    thenToken = 41          # 'then'
    doToken = 42            # 'do'

    openparenToken = 50     # '('

    number = 60             # number
    ident = 61              # identifier

    semiToken = 70          # ';'

    endToken = 80           # '}'
    odToken = 81            # 'od'
    fiToken = 82            # 'fi'

    elseToken = 90          # 'else'

    letToken = 100          # 'let'
    callToken = 101         # 'call'
    ifToken = 102           # 'if'
    whileToken = 103        # 'while'
    returnToken = 104       # 'return'

    varToken = 110          # 'var'
    arrToken = 111          # 'array'
    voidToken = 112         # 'void'
    funcToken = 113         # 'function'
    procToken = 114         # 'procedure'

    beginToken = 150        # '{'
    mainToken = 200         # 'computation'
    eofToken = 255          # end of file
