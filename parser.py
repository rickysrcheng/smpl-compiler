import tokenizer
import tokens
from tokens import *
import ssa


class Parser:
    def __init__(self, filepath: str, debug=False, tokenDebug=False):
        self.t = tokenizer.Tokenizer(filepath, tokenDebug)
        self.sym = None
        self.debug = debug

        self.identTable = []
        self.level = 0
        self.spacing = 2

        self.relOp = [Tokens.eqlToken, Tokens.neqToken,
                      Tokens.geqToken, Tokens.leqToken,
                      Tokens.gtrToken, Tokens.lssToken]

        self.ssa = ssa.SSA(self.t)

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
        self.ssa.PrintBlocks(self.t)

    def GenerateDot(self, varMode=False, debugMode=False):
        return self.ssa.GenerateDot(self.t, varMode, debugMode)

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
            #print(self.t.GetTokenStr(self.sym))
            if self.sym == Tokens.varToken:
                self.next()
                endVarDecl = False

            if not endVarDecl:
                if self.sym > 255:
                    self.identTable.append(self.sym)
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
        self.ssa.DefineIR(IRTokens.endToken, self.ssa.GetCurrBasicBlock())
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
                self.next()
                self.funcCall()
            elif self.sym == Tokens.ifToken:
                self.next()
                self.ifStatement()
            elif self.sym == Tokens.whileToken:
                self.next()
                self.whileStatement()
            elif self.sym == Tokens.returnToken:
                pass

            # don't need semicolon in terminating cases
            if self.sym in [Tokens.elseToken, Tokens.fiToken, Tokens.odToken, Tokens.endToken]:
                break
            else:
                self.CheckFor(Tokens.semiToken)
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
        instNode, instList, operands = self.expression()
        (version, inst, op) = self.ssa.AssignVariable(ident, instNode, currBB, instList)
        if self.debug:
            print(f'Assigning {self.t.GetTokenStr(ident)} to {instNode}, {operands}')
            print(f'Dependency of {self.t.GetTokenStr(ident)} {instList}')
        for n in instList:
            self.ssa.AddInstDependency(n[0], (version, ident))
        if self.debug:
            print(f'{" " * self.level * self.spacing}Exit assignment{self.level}')
        self.level -= 1
        return

    def funcCall(self):
        # funcCall = “call” ident [2 “(“ [expression { “,” expression } ] “)” ].

        # three first cases are predefined functions
        if self.sym == Tokens.inputNumToken:
            self.next()
            if self.sym == Tokens.openparenToken:
                self.next()
                self.CheckFor(Tokens.closeparenToken)
            instID = self.ssa.DefineIR(IRTokens.readToken, self.ssa.GetCurrBasicBlock())
            return instID
        elif self.sym == Tokens.outputNewLineToken:
            self.next()
            if self.sym == Tokens.openparenToken:
                self.next()
                self.CheckFor(Tokens.closeparenToken)
            instID = self.ssa.DefineIR(IRTokens.writeNLToken, self.ssa.GetCurrBasicBlock())
            return instID
        elif self.sym == Tokens.outputNumToken:
            self.next()
            self.CheckFor(Tokens.openparenToken)
            opID = self.expression()
            instID = self.ssa.DefineIR(IRTokens.writeToken, self.ssa.GetCurrBasicBlock(), opID)
            self.CheckFor(Tokens.closeparenToken)
        else:
            instID = 0
            pass
        return instID

    def ifStatement(self):
        # ifStatement = “if” relation “then” statSequence [ “else” statSequence ] “fi”.
        # TODO Project step 1
        self.level += 1
        if self.debug:
            print(f'{" " * self.level * self.spacing}In ifStatement{self.level}')

        # Get current basic block
        currBB = self.ssa.GetCurrBasicBlock()
        currBBDom = self.ssa.GetDomList(currBB)

        # call relation
        relOp, cmpInstID = self.relation()

        self.CheckFor(Tokens.thenToken)

        # add branch and save its id
        if relOp == Tokens.eqlToken:    # ==
            braInstID = self.ssa.DefineIR(IRTokens.bneToken, currBB, cmpInstID, 0)
        elif relOp == Tokens.neqToken:  # !=
            braInstID = self.ssa.DefineIR(IRTokens.beqToken, currBB, cmpInstID, 0)
        elif relOp == Tokens.lssToken:  # <
            braInstID = self.ssa.DefineIR(IRTokens.bgeToken, currBB, cmpInstID, 0)
        elif relOp == Tokens.leqToken:  # <=
            braInstID = self.ssa.DefineIR(IRTokens.bgtToken, currBB, cmpInstID, 0)
        elif relOp == Tokens.gtrToken:  # >
            braInstID = self.ssa.DefineIR(IRTokens.bleToken, currBB, cmpInstID, 0)
        elif relOp == Tokens.geqToken:  # >=
            braInstID = self.ssa.DefineIR(IRTokens.bltToken, currBB, cmpInstID, 0)

        # create new block and go to statSequence
        thenID = self.ssa.CreateNewBasicBlock(currBBDom, [currBB])
       # print(self.ssa.GetCurrBasicBlock(), self.ssa.GetDomList(thenID))
        self.ssa.AddBlockChild(currBB, thenID)

        self.statSequence()

        # retrieve the latest block
        # since statSequence could contain new ifStatement/whileStatement flows
        latestThenID = self.ssa.GetCurrBasicBlock()
        thenFirstInst = self.ssa.GetFirstInstInBlock(thenID)
        # if thenFirstInst == -1:
        #     thenFirstInst = self.ssa.DefineIR(IRTokens.emptyToken, thenID)
        # end then block

        # check for else block
        elseExist = False
        joinParent = [latestThenID, currBB]
        latestElseID = -1
        if self.sym == Tokens.elseToken:
            self.next()
            elseExist = True

            # this branches straight to join block
            jmpID = self.ssa.DefineIR(IRTokens.braToken, latestThenID, 0)

            elseID = self.ssa.CreateNewBasicBlock(currBBDom, [currBB])
            self.ssa.AddBlockChild(currBB, elseID)
            self.statSequence()

            latestElseID = self.ssa.GetCurrBasicBlock()

            # after returning, connect the branch instruction
            # if else block has no instruction, set a nop instruction
            elseFirstInst = self.ssa.GetFirstInstInBlock(elseID)
            if elseFirstInst == -1:
                elseFirstInst = self.ssa.DefineIR(IRTokens.emptyToken, elseID)

            self.ssa.ChangeOperands(braInstID, cmpInstID, elseFirstInst)

            joinParent.remove(currBB)
            joinParent.append(latestElseID)

        # if there's no else block, then the if block falls through with no branch instruction
        # if there are no instructions inside, add it
        if not elseExist:
            if thenFirstInst == -1:
                thenFirstInst = self.ssa.DefineIR(IRTokens.emptyToken, thenID)

        self.CheckFor(Tokens.fiToken)

        # Create join block and add phi nodes
        # Yes, in lecture phi is generated as we go.
        joinID = self.ssa.CreateNewBasicBlock(currBBDom, joinParent)
        self.ssa.AddBlockChild(latestThenID, joinID)

        self.ssa.ifElsePhi(latestThenID, joinID, currBB, self.identTable, latestElseID)

        joinFirstInstID = self.ssa.GetFirstInstInBlock(joinID)
        if joinFirstInstID == -1:
            joinFirstInstID = self.ssa.DefineIR(IRTokens.emptyToken, joinID)

        if elseExist:
            self.ssa.AddBlockChild(latestElseID, joinID)
            self.ssa.ChangeOperands(jmpID, joinFirstInstID)
        else:
            self.ssa.AddBlockChild(currBB, joinID)
            self.ssa.ChangeOperands(braInstID, cmpInstID, joinFirstInstID)

        if self.debug:
            print(f'{" " * self.level * self.spacing}Exit ifStatement{self.level}')
        self.level -= 1

    def whileStatement(self):
        # whileStatement = "while" relation "do" statSequence "od"
        # TODO Project step 1
        # Main thing, join block is entry block
        # Need to enter fall-through block to find references to variables
        #     that need to be reconciled
        # Q: How to connect the branch statement?

        self.level += 1
        if self.debug:
            print(f'{" " * self.level * self.spacing}In whileStatement{self.level}')

        # Get current basic block
        entryBB = self.ssa.GetCurrBasicBlock()
        entryBBDom = self.ssa.GetDomList(entryBB)
        #print(entryBB, entryBBDom)

        if self.ssa.GetFirstInstInBlock(entryBB) == -1:
            entryFirstInst = self.ssa.DefineIR(IRTokens.emptyToken, entryBB)

        # create join block
        joinBB = self.ssa.CreateNewBasicBlock(entryBBDom, [entryBB])
        joinBBDom = self.ssa.GetDomList(joinBB)

        # call relation
        relOp, cmpInstID = self.relation()

        # add branch and save its id
        if relOp == Tokens.eqlToken:    # ==
            braInstID = self.ssa.DefineIR(IRTokens.bneToken, joinBB, cmpInstID, 0)
        elif relOp == Tokens.neqToken:  # !=
            braInstID = self.ssa.DefineIR(IRTokens.beqToken, joinBB, cmpInstID, 0)
        elif relOp == Tokens.lssToken:  # <
            braInstID = self.ssa.DefineIR(IRTokens.bgeToken, joinBB, cmpInstID, 0)
        elif relOp == Tokens.leqToken:  # <=
            braInstID = self.ssa.DefineIR(IRTokens.bgtToken, joinBB, cmpInstID, 0)
        elif relOp == Tokens.gtrToken:  # >
            braInstID = self.ssa.DefineIR(IRTokens.bleToken, joinBB, cmpInstID, 0)
        elif relOp == Tokens.geqToken:  # >=
            braInstID = self.ssa.DefineIR(IRTokens.bltToken, joinBB, cmpInstID, 0)

        self.CheckFor(Tokens.doToken)

        # doBlock
        doBB = self.ssa.CreateNewBasicBlock(joinBBDom, [joinBB])

        # connect join block with do block for loop body
        self.ssa.AddBlockParent(joinBB, doBB)
        self.ssa.AddBlockChild(doBB, joinBB)
        self.ssa.AddBlockChild(joinBB, doBB)

        self.statSequence()

        # get the latest block from statSequence, need to add an unconditional branch
        latestDoBB = self.ssa.GetCurrBasicBlock()
        self.CheckFor(Tokens.odToken)

        # reconcile phi function
        self.ssa.whilePhi(joinBB, latestDoBB, self.identTable)

        joinFirstID = self.ssa.GetFirstInstInBlock(joinBB)
        self.ssa.DefineIR(IRTokens.braToken, latestDoBB, joinFirstID)

        exitBB = self.ssa.CreateNewBasicBlock(joinBBDom, [joinBB])
        self.ssa.ChangeOperands(braInstID, cmpInstID, f'BB{exitBB}')

    def returnStatement(self):
        pass

    def relation(self):
        # relation = expression relOp expression

        # add cmp and branch instruction here
        self.level += 1
        if self.debug:
            print(f'{" " * self.level * self.spacing}In relation{self.level}')

        currBB = self.ssa.GetCurrBasicBlock()
        ex1, instList2, var1 = self.expression()

        if self.sym not in self.relOp:
            self.t.close()
            raise SyntaxError(f'Expected relOp, got {self.t.GetTokenStr(self.sym)}')

        relOp = self.sym
        self.next()

        ex2, instList2, var2 = self.expression()

        cmpInstID = self.ssa.DefineIR(IRTokens.cmpToken, currBB, ex1, ex2, var1=var1, var2=var2)

        if self.debug:
            print(f'{" " * self.level * self.spacing}Exit relation{self.level}')
        self.level -= 1

        return relOp, cmpInstID

    def expression(self):
        # expression = term {(“+” | “-”) term}
        self.level += 1
        if self.debug:
            print(f'{" " * self.level * self.spacing}In E{self.level}')
        instID, instList, var = self.term()
        currBB = self.ssa.GetCurrBasicBlock()
        if self.debug:
            print(f'{" " * self.level * self.spacing}E{self.level}: Term 1: {instID}')
        while self.sym == Tokens.plusToken or self.sym == Tokens.minusToken:
            op1 = instID

            if self.sym == Tokens.plusToken:
                self.next()
                op2, instList2, var2 = self.term()
                instID = self.ssa.DefineIR(IRTokens.addToken, currBB, op1, op2, var1=var, var2=var2)
                instList += instList2
                instList.append((instID, var, var2))

            elif self.sym == Tokens.minusToken:
                self.next()
                op2, instList2, var2 = self.term()
                instID = self.ssa.DefineIR(IRTokens.subToken, currBB, op1, op2, var1=var, var2=var2)
                instList += instList2
                instList.append((instID, var, var2))
            var = (2, instID)
            if self.debug:
                opvar = instList
                print(f'{" " * self.level * self.spacing}E{self.level}: Current expression: {instID} {op1} {op2}, {opvar}')

        if self.debug:
            print(f'{" " * self.level * self.spacing}Exit E{self.level}: {instID}')
        self.level -= 1
        return instID, instList, var

    def term(self):
        # term = factor { (“*” | “/”) factor}
        self.level += 1
        if self.debug:
            print(f'{" " * self.level * self.spacing}In T{self.level}')

        instID, instList, var = self.factor()
        currBB = self.ssa.GetCurrBasicBlock()
        # if self.debug:
        #     print(f'{" " * self.level * self.spacing}T{self.level}: Factor 1: {result}')

        while self.sym == Tokens.timesToken or self.sym == Tokens.divToken:
            op1 = instID
            if self.sym == Tokens.timesToken:
                self.next()
                op2, instList2, var2 = self.factor()
                instID = self.ssa.DefineIR(IRTokens.mulToken, currBB, instID, op2, var1=var, var2=var2)
                instList += instList2
                instList.append((instID, var, var2))
            elif self.sym == Tokens.divToken:
                self.next()
                op2, instList2, var2 = self.factor()
                instID = self.ssa.DefineIR(IRTokens.divToken, currBB, instID, op2, var1=var, var2=var2)
                instList += instList2
                instList.append((instID, var, var2))
            var = (2, instID)
            if self.debug:
                opvar = instList
                print(f'{" " * self.level * self.spacing}T{self.level}: Current term: {instID} {op1} {op2}, {opvar}')
        if self.debug:
            print(f'{" " * self.level * self.spacing}Exit T{self.level}: {instID}')
        self.level -= 1
        return instID, instList, var

    def factor(self):
        # factor = designator | number | “(“ expression “)” | funcCall

        self.level += 1
        operands = None
        if self.debug:
            print(f'{" " * self.level * self.spacing}In F{self.level}')
        currBB = self.ssa.GetCurrBasicBlock()
        instList = []
        # number
        if self.sym == Tokens.number:
            # result = self.t.lastNum
            instID = self.ssa.DefineIR(IRTokens.constToken, currBB, self.t.lastNum)
            operands = (0, instID)
            self.next()
        # designator = ident{ "[" expression "]" }
        elif self.sym > 255:
            # result = self.identTable[self.sym]
            instID = self.ssa.GetVarInstNode(self.sym, currBB)
            varVersion = self.ssa.GetVarVersion(self.sym, currBB)
            operands = (1, (varVersion[0], self.sym))
            self.next()
        # “(“ expression “)”
        elif self.sym == Tokens.openparenToken:
            self.next()
            instID, instList, operands = self.expression()
            operands = (2, instID)
            self.CheckFor(Tokens.closeparenToken)
        # funcCall
        elif self.sym == Tokens.callToken:
            self.next()
            instID, operands = self.funcCall()
            operands = (2, instID)

        if self.debug:
            print(f'{" " * self.level * self.spacing}Exit F{self.level}: {instID} {instList} {operands}')
        self.level -= 1
        return instID, instList, operands


if __name__ == '__main__':
    comp = Parser("./tests/whileTests/while.txt", True)
    #comp = Parser("./test.txt", True)
    comp.computation()
    comp.PrintSSA()
    dot = comp.GenerateDot(varMode=True, debugMode=True)

    comp.close()
