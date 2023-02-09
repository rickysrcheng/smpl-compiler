from tokens import Tokens


class FileReader:
    def __init__(self, filepath):
        self.f = open(filepath, 'r')
        self.__EOF = False
        self.__ERROR = False

    def GetNext(self):
        if self.__ERROR:
            return 0

        if self.__EOF:
            return ''

        sym = self.f.read(1)
        if sym == '':
            self.__EOF = True
        return sym

    def Error(self, errorMsg):
        self.__ERROR = True
        print('Error')
        self.close()

    def close(self):
        self.f.close()


class Tokenizer:
    def __init__(self, filepath, debug=False):
        self.f = FileReader(filepath)
        self.sym = ""
        self.__next()
        self.tokenTable = {
            'main': Tokens.mainToken,
            '{': Tokens.beginToken,

            'procedure': Tokens.procToken,
            'function': Tokens.funcToken,
            'void': Tokens.voidToken,
            'array': Tokens.arrToken,
            'var': Tokens.varToken,

            'return': Tokens.returnToken,
            'while': Tokens.whileToken,
            'if': Tokens.ifToken,
            'call': Tokens.callToken,
            'let': Tokens.letToken,

            'else': Tokens.elseToken,

            'fi': Tokens.fiToken,
            'od': Tokens.odToken,
            '}': Tokens.endToken,

            ';': Tokens.semiToken,

            'ident': Tokens.ident,
            'number': Tokens.number,

            '(': Tokens.openparenToken,

            'do': Tokens.doToken,
            'then': Tokens.thenToken,
            '<-': Tokens.becomesToken,

            ')': Tokens.closeparenToken,
            ']': Tokens.closebracketToken,
            '[': Tokens.openbracketToken,
            ',': Tokens.commaToken,
            '.': Tokens.periodToken,

            '>': Tokens.gtrToken,
            '<=': Tokens.leqToken,
            '>=': Tokens.geqToken,
            '<': Tokens.lssToken,
            '!=': Tokens.neqToken,
            '==': Tokens.eqlToken,

            '-': Tokens.minusToken,
            '+': Tokens.plusToken,

            '/': Tokens.divToken,
            '*': Tokens.timesToken
        }

        self.globalKeyword = ['main', 'procedure', 'function', 'void', 'array', 'var',
                              'return', 'while', 'if', 'call', 'let', 'fi', 'od', 'do', 'then']

        self.singleSymbol = ['*', '/', '+', '-', '.', ',', '[', ']', '(', ')', ';', '{', '}']

        self.lastNum = None
        self.lastId = None

        self.idCounter = max([t.value for t in Tokens]) + 1  # for new identifiers
        self.EOF = False
        self.ERROR = False
        self.debug = debug

    def __next(self):
        self.sym = self.f.GetNext()

    def close(self):
        self.f.close()

    def GetNext(self):
        if self.EOF:
            if self.debug:
                print("", Tokens.eofToken)
            return Tokens.eofToken
        elif self.ERROR:
            return Tokens.errorToken

        result = ''

        # get rid of whitespaces
        while self.sym.isspace():  # self.sym in [" ","\n", "\t"]:
            self.__next()

        token = 0
        if self.sym == '':
            self.EOF = True
            token = Tokens.eofToken

        # starting symbol is number
        elif self.sym in "0123456789":
            token = self.tokenTable['number']
            result = int(self.sym)
            self.__next()
            # keep collecting until non-numeric char occurs
            while self.sym in "0123456789":
                result = 10 * result + int(self.sym)
                self.__next()
            self.lastNum = result

        # starting symbol is identifier
        elif self.sym.isalpha():
            result = self.sym
            self.__next()
            # keep collecting until a non-alphanumeric char occurs
            while self.sym.isalnum():
                result += self.sym
                self.__next()
            # print(result)
            if result in self.globalKeyword:
                token = self.tokenTable[result]
            else:
                if result in self.tokenTable:
                    token = self.tokenTable[result]
                else:
                    token = self.idCounter
                    self.tokenTable[result] = self.idCounter
                    self.idCounter += 1

            self.lastId = token

        else:  # otherwise it's a special symbol
            # there's so many...
            if self.sym == "":
                self.EOF = True
                token = Tokens.eofToken
            elif self.sym in self.singleSymbol:
                result = self.sym
                token = self.tokenTable[self.sym]
                self.__next()
            else:  # deals with token subsets of [20-25] and 40, relops and '<-'
                firstChar = self.sym
                result = self.sym
                if firstChar in '=!<>':
                    self.__next()
                    if self.sym == '=':  # '==', '!=', '>=', '<='
                        token = self.tokenTable[firstChar + self.sym]
                        result += self.sym
                        self.__next()
                    elif self.sym == '-':  # '<-'
                        token = self.tokenTable[firstChar + self.sym]
                        result += self.sym
                        self.__next()
                    else:
                        if firstChar == '>' or firstChar == '<':  # '<', '>'
                            token = self.tokenTable[firstChar]
                        else:
                            # otherwise we have '!' and '='
                            # 	which is not valid on its own
                            token = Tokens.errorToken
                            self.ERROR = True
                else:
                    token = Tokens.errorToken
                    self.ERROR = True

        if self.debug:
            print(result, token)
        return token


if __name__ == '__main__':
    comp = Tokenizer("p2.txt", False)
    token = 0
    i = 0
    while i < 5:
        token = comp.GetNext()
        if token == Tokens.eofToken:
            i += 1
    # print(token)
    comp.close()
