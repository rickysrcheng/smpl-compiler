import tokenizer
import tokens
from tokens import *
import ssa


class Parser:
    def __init__(self, filepath: str, debug=False, tokenDebug=False):
        self.t = tokenizer.Tokenizer(filepath, tokenDebug)
        self.sym = None
        self.debug = debug

        self.identTable = {}
        self.level = 0
        self.spacing = 2

        self.relOp = [Tokens.eqlToken, Tokens.neqToken,
                      Tokens.geqToken, Tokens.leqToken,
                      Tokens.gtrToken, Tokens.lssToken]

        self.ssa = ssa.SSA()

    def next(self):
        self.sym = self.t.GetNext()

    def close(self):
        self.t.close()

    def CheckFor(self, token: Tokens) -> None:
        if self.sym == token:
            self.next()
        else:
            raise SyntaxError(f'Expected {self.t.GetTokenStr(token)}, got {self.t.GetTokenStr(self.sym)}')

    def PrintSSA(self):
        self.ssa.PrintInstructions()
        self.ssa.PrintBlocks()

    # def template(self):
    #	  self.level += 1
    #     if self.debug:
    #         print(f'{" "*self.level*self.spacing}In template{self.level}')
    #     ### Do stuff here
    #     if self.debug:
    #         print(f'{" "*self.level*self.spacing}Exit template{self.level}')
    #     self.level -= 1
    #     return

    def computation(self):
        # computation = "main" { varDecl } { funcDecl } "{"" statSequence "}" ".".
        self.next()
        self.CheckFor(Tokens.mainToken)
        if self.debug:
            print(f'{" " * self.level * self.spacing}In C{self.level}')

        # Variable instantiation
        # varDecl = typeDecl indent { “,” ident } “;”

        endVarDecl = True
        while self.sym != Tokens.funcToken and self.sym != Tokens.beginToken:
            # typeDecl = “var” | “array” “[“ number “]” { “[“ number “]”}
            print(self.t.GetTokenStr(self.sym))
            if self.sym == Tokens.varToken:
                self.next()
                endVarDecl = False

            if not endVarDecl:
                if self.sym > 255:
                    self.identTable[self.sym] = None
                    self.next()
                else:
                    self.t.close()
                    raise SyntaxError("Keyword cannot be used as variable name")
            elif self.sym == Tokens.arrToken:
                pass

            if self.sym == Tokens.semiToken:
                self.next()
                endVarDecl = True
            elif self.sym == Tokens.commaToken:
                self.next()
            else:
                self.t.close()
                raise SyntaxError(f"Expected \',\' or \';\', got {self.sym}")

        # Function instantiation
        if self.sym == Tokens.funcToken:
            pass

        # move to statSequence
        self.CheckFor(Tokens.beginToken)
        self.statSequence()
        self.CheckFor(Tokens.endToken)

        self.CheckFor(Tokens.periodToken)
        if self.debug:
            print(f'{" " * self.level * self.spacing}Exit C{self.level}')

    def statSequence(self):
        # statSequence = statement { “;” statement } [ “;” ]
        # originally nested in computation but broken out since other rules uses it too
        self.level += 1
        if self.debug:
            print(f'{" " * self.level * self.spacing}In statSequence{self.level}')
        # Do stuff here
        while True:
            # statement = assignment | funcCall | ifStatement | whileStatement | returnStatement
            if self.sym == Tokens.letToken:
                self.next()
                self.assignment()
            elif self.sym == Tokens.callToken:
                pass
            elif self.sym == Tokens.ifToken:
                self.next()
                self.ifStatement()
            elif self.sym == Tokens.whileToken:
                pass
            elif self.sym == Tokens.returnToken:
                pass
            elif self.sym == Tokens.semiToken:
                self.next()
            else:
                break
        if self.debug:
            print(f'{" " * self.level * self.spacing}Exit statSequence{self.level}')
        self.level -= 1
        return

    def assignment(self):
        # assignment = “let” designator “<-” expression
        self.level += 1
        if self.debug:
            print(f'{" " * self.level * self.spacing}In assignment{self.level}')

        # Do stuff here
        # first check if designator has been declared
        if self.sym in self.identTable:
            pass
        ident = self.sym
        self.next()
        self.CheckFor(Tokens.becomesToken)

        currBB = self.ssa.GetCurrBasicBlock()
        instNode = self.expression()
        self.ssa.AssignVariable(ident, instNode, currBB)
        print(f'Assigning {self.t.GetTokenStr(ident)} to {instNode}')
        if self.debug:
            print(f'{" " * self.level * self.spacing}Exit assignment{self.level}')
        self.level -= 1
        return

    def funcCall(self):
        pass

    def ifStatement(self):
        # ifStatement = “if” relation “then” statSequence [ “else” statSequence ] “fi”.
        # TODO Project step 1
        self.level += 1
        if self.debug:
            print(f'{" " * self.level * self.spacing}In ifStatement{self.level}')

        # Get current basic block
        currBB = self.ssa.GetCurrBasicBlock()
        currBBDom = self.ssa.GetDomList(currBB)
        print(currBB, currBBDom)

        # call relation
        relOp, cmpInstID = self.relation()

        self.CheckFor(Tokens.thenToken)

        # add branch and save its id
        if relOp == Tokens.eqlToken:
            braInstID = self.ssa.DefineIR(IRTokens.beqToken, currBB, cmpInstID, 0)
        elif relOp == Tokens.neqToken:
            braInstID = self.ssa.DefineIR(IRTokens.bneToken, currBB, cmpInstID, 0)
        elif relOp == Tokens.lssToken:
            braInstID = self.ssa.DefineIR(IRTokens.bltToken, currBB, cmpInstID, 0)
        elif relOp == Tokens.leqToken:
            braInstID = self.ssa.DefineIR(IRTokens.bleToken, currBB, cmpInstID, 0)
        elif relOp == Tokens.gtrToken:
            braInstID = self.ssa.DefineIR(IRTokens.bgtToken, currBB, cmpInstID, 0)
        elif relOp == Tokens.geqToken:
            braInstID = self.ssa.DefineIR(IRTokens.bgeToken, currBB, cmpInstID, 0)

        # create new block and go to statSequence
        thenID = self.ssa.CreateNewBasicBlock(currBBDom, [currBB])
        print(self.ssa.GetCurrBasicBlock(), self.ssa.GetDomList(thenID))
        self.ssa.AddBlockChild(currBB, thenID)

        self.statSequence()

        # retrieve the latest block
        # since statSequence could contain new ifStatement/whileStatement flows
        latestThenID = self.ssa.GetCurrBasicBlock()
        # end then block

        # check for else block
        elseExist = False
        joinParent = [latestThenID]
        if self.sym == Tokens.elseToken:
            self.next()
            elseExist = True
            jmpID = self.ssa.DefineIR(IRTokens.braToken, thenID, 0, 0)

            elseID = self.ssa.CreateNewBasicBlock(currBBDom, [currBB])
            self.ssa.AddBlockChild(currBB, elseID)

            self.statSequence()

            latestElseID = self.ssa.GetCurrBasicBlock()
            joinParent.append(latestElseID)

        self.CheckFor(Tokens.fiToken)
        self.ssa.PrintInstructions()
        # Create join block and add phi nodes
        # Yes, in lecture phi is generated as we go.
        joinID = self.ssa.CreateNewBasicBlock(currBBDom, joinParent)
        self.ssa.AddBlockChild(latestThenID, joinID)
        if elseExist:
            self.ssa.AddBlockChild(latestElseID, joinID)

        if self.debug:
            print(f'{" " * self.level * self.spacing}Exit ifStatement{self.level}')
        self.level -= 1

    def whileStatement(self):
        # TODO Project step 1
        pass

    def returnStatement(self):
        pass

    def relation(self):
        # relation = expression relOp expression

        # add cmp and branch instruction here
        self.level += 1
        if self.debug:
            print(f'{" " * self.level * self.spacing}In relation{self.level}')

        currBB = self.ssa.GetCurrBasicBlock()
        ex1 = self.expression()

        if self.sym not in self.relOp:
            self.t.close()
            raise SyntaxError(f'Expected relOp, got {self.sym}')

        relOp = self.sym
        self.next()

        ex2 = self.expression()

        cmpInstID = self.ssa.DefineIR(IRTokens.cmpToken, currBB, ex1, ex2)

        if self.debug:
            print(f'{" " * self.level * self.spacing}Exit relation{self.level}')
        self.level -= 1

        return relOp, cmpInstID

    def expression(self):
        # expression = term {(“+” | “-”) term}
        self.level += 1
        if self.debug:
            print(f'{" " * self.level * self.spacing}In E{self.level}')
        instID = self.term()
        currBB = self.ssa.GetCurrBasicBlock()
        if self.debug:
            print(f'{" " * self.level * self.spacing}E{self.level}: Term 1: {instID}')
        while self.sym == Tokens.plusToken or self.sym == Tokens.minusToken:
            op1 = instID
            if self.sym == Tokens.plusToken:
                self.next()
                op2 = self.term()
                instID = self.ssa.DefineIR(IRTokens.addToken, currBB, op1, op2)
            elif self.sym == Tokens.minusToken:
                self.next()
                op2 = self.term()
                instID = self.ssa.DefineIR(IRTokens.subToken, currBB, op1, op2)

            if self.debug:
                print(f'{" " * self.level * self.spacing}E{self.level}: Current expression: {instID} {op1} {op2}')
        if self.debug:
            print(f'{" " * self.level * self.spacing}Exit E{self.level}: {instID}')
        self.level -= 1
        return instID

    def term(self):
        # term = factor { (“*” | “/”) factor}
        self.level += 1
        if self.debug:
            print(f'{" " * self.level * self.spacing}In T{self.level}')
        instID = self.factor()
        currBB = self.ssa.GetCurrBasicBlock()
        # if self.debug:
        #     print(f'{" " * self.level * self.spacing}T{self.level}: Factor 1: {result}')

        while self.sym == Tokens.timesToken or self.sym == Tokens.divToken:
            op1 = instID
            if self.sym == Tokens.timesToken:
                self.next()
                op2 = self.factor()
                instID = self.ssa.DefineIR(IRTokens.mulToken, currBB, instID, op2)
            elif self.sym == Tokens.divToken:
                self.next()
                op2 = self.factor()
                instID = self.ssa.DefineIR(IRTokens.divToken, currBB, instID, op2)
            if self.debug:
                print(f'{" " * self.level * self.spacing}T{self.level}: Current term: {instID} {op1} {op2}')
        if self.debug:
            print(f'{" " * self.level * self.spacing}Exit T{self.level}: {instID}')
        self.level -= 1
        return instID

    def factor(self):
        # factor = designator | number | “(“ expression “)” | funcCall

        self.level += 1
        if self.debug:
            print(f'{" " * self.level * self.spacing}In F{self.level}')
        currBB = self.ssa.GetCurrBasicBlock()
        # number
        if self.sym == Tokens.number:
            # result = self.t.lastNum
            instID = self.ssa.DefineIR(IRTokens.constToken, currBB, self.t.lastNum)
            self.next()
        # designator = ident{ "[" expression "]" }
        elif self.sym > 255:
            # result = self.identTable[self.sym]
            instID = self.ssa.GetVarInstNode(self.sym, currBB)
            self.next()
        # “(“ expression “)”
        elif self.sym == Tokens.openparenToken:
            self.next()
            instID = self.expression()
            self.CheckFor(Tokens.closeparenToken)
        # funcCall
        elif self.sym == Tokens.callToken:
            pass

        if self.debug:
            print(f'{" " * self.level * self.spacing}Exit F{self.level}: {instID}')
        self.level -= 1
        return instID


if __name__ == '__main__':
    comp = Parser("./test.txt", True)
    comp.computation()
    comp.PrintSSA()
    comp.close()
