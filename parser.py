import tokenizer
import tokens
from tokens import *
import ssa
from operator import mul
from functools import reduce


class Parser:
    def __init__(self, filepath: str, debug=False, tokenDebug=False):
        self.t = tokenizer.Tokenizer(filepath, tokenDebug)
        self.sym = None
        self.debug = debug

        self.endVarDecl = True
        self.collectArr = False
        self.identTable = []
        self.arrayDict = {}
        self.arrayOffset = {}
        self.arrayAddress = {}
        self.level = 0
        self.spacing = 2
        self.dataBaseAddr = -1

        self.relOp = [Tokens.eqlToken, Tokens.neqToken,
                      Tokens.geqToken, Tokens.leqToken,
                      Tokens.gtrToken, Tokens.lssToken]

        self.ssa = ssa.SSA(self.t)
        # (opType, joinID, entryID)
        #  opType: 0, join if-then block, (ssa, entry/else)
        #          1, join else block, right-hand side (entry/if, ssa)
        #          2, join while block, left-hand side (ssa, entry)
        self.joinStack = []

        # stores the branch instruction ID and basic block it branches to
        self.branchInsts = []  # (opPos, instID, branchBB)

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
        self.endVarDecl = True
        self.collectArr = False
        dataBase = False
        arrSize = []
        while self.sym != Tokens.funcToken and self.sym != Tokens.beginToken:
            # typeDecl = “var” | “array” “[“ number “]” { “[“ number “]”}
            if self.sym == Tokens.varToken:
                self.next()
                self.endVarDecl = False
            elif self.sym == Tokens.arrToken:
                if not dataBase:
                    self.dataBaseAddr, _ = self.ssa.DefineIR(IRTokens.constToken, 0, "Base")
                    dataBase = True
                self.collectArr = True
                self.endVarDecl = False
                self.next()
                arrSize = [self.parseArraySize()]
                while self.sym == Tokens.openbracketToken:
                    arrSize.append(self.parseArraySize())

            if not self.endVarDecl:
                if self.sym > 255:
                    if self.collectArr:
                        self.arrayDict[self.sym] = tuple(arrSize)
                        self.arrayOffset[self.sym] = tuple(self.defineOffsets(arrSize))
                        self.arrayAddress[self.sym], _ = self.ssa.DefineIR(IRTokens.constToken, 0,
                                                                           f'{self.t.GetTokenStr(self.sym)}BaseAddr')
                        #self.arrayTable.append((self.sym, tuple(arrSize)))
                    else:
                        self.identTable.append(self.sym)
                    self.next()
                else:
                    self.t.close()
                    raise SyntaxError("Keyword cannot be used as variable name")

            if self.sym == Tokens.semiToken:
                self.next()
                self.endVarDecl = True
                self.collectArr = False
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

        # change branch instructions
        for braInsts in self.branchInsts:
            brOp1 = self.ssa.GetFirstInstInBlock(braInsts[2])
            if braInsts[0] == 0:
                self.ssa.ChangeOperands(braInsts[1], op1=brOp1)
            else:
                self.ssa.ChangeOperands(braInsts[1], op2=brOp1)

        if self.debug:
            print(f'{" " * self.level * self.spacing}Exit C{self.level}')

    def parseArraySize(self):
        self.CheckFor(Tokens.openbracketToken)
        self.CheckFor(Tokens.number)
        size = self.t.lastNum
        #self.ssa.DefineIR(IRTokens.constToken, 0, self.t.lastNum)
        self.CheckFor(Tokens.closebracketToken)
        return size

    def defineOffsets(self, arrSize):
        # precomputes the memory offsets in arrays
        totalSize = reduce(mul, arrSize)
        offsetSizes = []
        currOffset = 1
        for i in range(len(arrSize) - 1):
            currOffset *= arrSize[i]
            offset = totalSize//currOffset
            instID, _ = self.ssa.DefineIR(IRTokens.constToken, 0, offset)
            offsetSizes.append((offset, instID))
        offsetSizes.append((1, -1))
        return offsetSizes

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
        LHSArray = False
        currBB = self.ssa.GetCurrBasicBlock()
        if ident in self.identTable:
            self.CheckFor(Tokens.becomesToken)
        elif ident in self.arrayDict:
            LHSArray = True
            arrBaseInstID, offsetID, instList = self.arrayAddrInstCalculation(ident, currBB)
            self.CheckFor(Tokens.becomesToken)

        instNode, instList, operands = self.expression()
        varAssign = False
        # used in copy propagation. we want to save a copy of this version
        if len(instList) == 0 and operands[0] == 1:
            varAssign = True
            instList = [operands]
        if LHSArray:
            instID, _ = self.ssa.DefineIR(IRTokens.storeToken, currBB, arrBaseInstID, offsetID, storeData=instNode)
            self.ssa.AddKillInst(ident, self.joinStack, currBB, arrBaseInstID)
        else:
            (version, inst, op) = self.ssa.AssignVariable(ident, instNode, currBB, instList, varAssign=varAssign)
            self.ssa.AddPhiNode(ident, inst, self.joinStack, currBB, varAssign=varAssign, operands=operands)

        if self.debug:
            print(f'Assigning {self.t.GetTokenStr(ident)} to {instNode}, {operands}')
            print(f'Dependency of {self.t.GetTokenStr(ident)} {instList}')
        if not LHSArray and not varAssign:
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
            instID, _ = self.ssa.DefineIR(IRTokens.readToken, self.ssa.GetCurrBasicBlock())
            #return instID
        elif self.sym == Tokens.outputNewLineToken:
            self.next()
            if self.sym == Tokens.openparenToken:
                self.next()
                self.CheckFor(Tokens.closeparenToken)
            instID, _  = self.ssa.DefineIR(IRTokens.writeNLToken, self.ssa.GetCurrBasicBlock())
            #return instID
        elif self.sym == Tokens.outputNumToken:
            self.next()
            self.CheckFor(Tokens.openparenToken)
            opID, instList, operand = self.expression()
            instID, _ = self.ssa.DefineIR(IRTokens.writeToken, self.ssa.GetCurrBasicBlock(), opID, var1=operand)
            self.CheckFor(Tokens.closeparenToken)
        else:
            instID = 0
            pass
        return instID, [], (2, instID)

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
        else:  # elif relOp == Tokens.geqToken:  # >=
            braInstID = self.ssa.DefineIR(IRTokens.bltToken, currBB, cmpInstID, 0)

        braInstID = braInstID[0]
        # create new block and go to statSequence
        thenID = self.ssa.CreateNewBasicBlock(currBBDom, [currBB], [currBB], blockType="then\\n")
       # print(self.ssa.GetCurrBasicBlock(), self.ssa.GetDomList(thenID))
        self.ssa.AddBlockChild(currBB, thenID)

        joinID = self.ssa.CreateNewBasicBlock(currBBDom, [], [currBB], blockType='join\\n')

        self.ssa.SetCurrBasicBlock(thenID)
        self.joinStack.append((0, joinID, currBB))
        self.statSequence()
        self.joinStack.pop()

        # retrieve the latest block
        # since statSequence could contain new ifStatement/whileStatement flows
        latestThenID = self.ssa.GetCurrBasicBlock()
        thenFirstInst = self.ssa.GetFirstInstInBlock(thenID)
        self.ssa.AddBlockParent(joinID, latestThenID)
        self.ssa.AddBlockChild(latestThenID, joinID)
        # if thenFirstInst == -1:
        #     thenFirstInst = self.ssa.DefineIR(IRTokens.emptyToken, thenID)
        # end then block

        # check for else block
        elseExist = False
        joinParent = currBB
        latestElseID = -1
        if self.sym == Tokens.elseToken:
            self.next()
            elseExist = True

            # this branches straight to join block
            jmpID, _ = self.ssa.DefineIR(IRTokens.braToken, latestThenID, 0)

            elseID = self.ssa.CreateNewBasicBlock(currBBDom, [currBB], [currBB], blockType="else\\n")
            self.ssa.AddBlockChild(currBB, elseID)
            self.joinStack.append((1, joinID, currBB))
            self.statSequence()
            self.joinStack.pop()

            latestElseID = self.ssa.GetCurrBasicBlock()

            # after returning, connect the branch instruction
            # if else block has no instruction, set a nop instruction
            elseFirstInst = self.ssa.GetFirstInstInBlock(elseID)
            if elseFirstInst == -1:
                elseFirstInst, _ = self.ssa.DefineIR(IRTokens.emptyToken, elseID)

            self.ssa.ChangeOperands(braInstID, cmpInstID, elseFirstInst)

            latestElseFirstInst = self.ssa.GetFirstInstInBlock(latestElseID)
            if latestElseFirstInst == -1:
                elseFirstInst, _ = self.ssa.DefineIR(IRTokens.emptyToken, latestElseID)

            joinParent = latestElseID

        # if there's no else block, then the if block falls through with no branch instruction
        # if there are no instructions inside, add it
        if not elseExist:
            if thenFirstInst == -1:
                thenFirstInst, _ = self.ssa.DefineIR(IRTokens.emptyToken, thenID)

        self.CheckFor(Tokens.fiToken)

        # Create join block and add phi nodes
        # Yes, in lecture phi is generated as we go.
        #joinID = self.ssa.CreateNewBasicBlock(currBBDom, joinParent)
        self.ssa.AddBlockParent(joinID, joinParent)
        self.ssa.AddBlockChild(joinParent, joinID)

        #self.ssa.ifElsePhi(latestThenID, joinID, currBB, self.identTable, latestElseID)

        # joinFirstInstID = self.ssa.GetFirstInstInBlock(joinID)
        # if joinFirstInstID == -1:
        #     joinFirstInstID, _ = self.ssa.DefineIR(IRTokens.emptyToken, joinID)

        if elseExist:
            self.ssa.AddBlockChild(latestElseID, joinID)
            # self.ssa.ChangeOperands(jmpID, joinFirstInstID)
            self.branchInsts.append((0, jmpID, joinID))
        else:
            self.ssa.AddBlockChild(currBB, joinID)
            # self.ssa.ChangeOperands(braInstID, cmpInstID, joinFirstInstID)
            self.branchInsts.append((1, braInstID, joinID))
        self.ssa.SetCurrBasicBlock(joinID)
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

        if self.ssa.GetFirstInstInBlock(entryBB) == -1:
            entryFirstInst, _ = self.ssa.DefineIR(IRTokens.emptyToken, entryBB)

        # create join block
        joinBB = self.ssa.CreateNewBasicBlock(entryBBDom, [entryBB], [entryBB], blockType="join\\n", joinType=1)
        joinBBDom = self.ssa.GetDomList(joinBB)
        self.ssa.AddBlockChild(entryBB, joinBB)

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
        else:  # elif relOp == Tokens.geqToken:  # >=
            braInstID = self.ssa.DefineIR(IRTokens.bltToken, joinBB, cmpInstID, 0)

        braInstID = braInstID[0]
        self.CheckFor(Tokens.doToken)
        self.joinStack.append((2, joinBB, entryBB))
        # doBlock
        doBB = self.ssa.CreateNewBasicBlock(joinBBDom, [joinBB], [joinBB], blockType="do\\n", joinBlocks=self.joinStack)

        # connect join block with do block for loop body
        #self.ssa.AddBlockParent(joinBB, doBB)
        #self.ssa.AddBlockChild(doBB, joinBB)
        self.ssa.AddBlockChild(joinBB, doBB)
        self.statSequence()


        # get the latest block from statSequence, need to add an unconditional branch
        latestDoBB = self.ssa.GetCurrBasicBlock()
        self.CheckFor(Tokens.odToken)
        self.ssa.AddBlockChild(latestDoBB, joinBB)
        self.ssa.AddBlockParent(joinBB, latestDoBB)

        # reconcile phi function
        joinFirstID = self.ssa.GetFirstInstInBlock(joinBB)
        self.ssa.DefineIR(IRTokens.braToken, latestDoBB, joinFirstID)

        exitBB = self.ssa.CreateNewBasicBlock(joinBBDom, [joinBB], [joinBB], "exit\\n")

        self.ssa.AddBlockChild(joinBB, exitBB)
        #self.PrintSSA()
        self.ssa.whilePhi(joinBB, latestDoBB, self.identTable)
        self.joinStack.pop()
        self.ssa.AddBlockJoinStack(exitBB, self.joinStack)
        # exitInstID = self.ssa.instructionCount
        # self.ssa.ChangeOperands(braInstID, cmpInstID, exitInstID)
        self.branchInsts.append((1, braInstID, exitBB))

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

        cmpInstID, _ = self.ssa.DefineIR(IRTokens.cmpToken, currBB, ex1, ex2, var1=var1, var2=var2)

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
                instID, flip = self.ssa.DefineIR(IRTokens.addToken, currBB, op1, op2, var1=var, var2=var2)
                instList += instList2
                if flip:
                    instList.append((instID, var2, var))
                else:
                    instList.append((instID, var, var2))
            elif self.sym == Tokens.minusToken:
                self.next()
                op2, instList2, var2 = self.term()
                instID, flip = self.ssa.DefineIR(IRTokens.subToken, currBB, op1, op2, var1=var, var2=var2)
                instList += instList2
                if flip:
                    instList.append((instID, var2, var))
                else:
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
                instID, flip = self.ssa.DefineIR(IRTokens.mulToken, currBB, instID, op2, var1=var, var2=var2)
                instList += instList2
                if flip:
                    instList.append((instID, var2, var))
                else:
                    instList.append((instID, var, var2))
            elif self.sym == Tokens.divToken:
                self.next()
                op2, instList2, var2 = self.factor()
                instID, flip = self.ssa.DefineIR(IRTokens.divToken, currBB, instID, op2, var1=var, var2=var2)
                instList += instList2
                if flip:
                    instList.append((instID, var2, var))
                else:
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
            instID, _ = self.ssa.DefineIR(IRTokens.constToken, currBB, self.t.lastNum)
            operands = (0, instID)
            self.next()
        # designator = ident{ "[" expression "]" }
        elif self.sym > 255:
            # result = self.identTable[self.sym]
            if self.endVarDecl:
                if self.sym not in self.identTable and self.sym not in self.arrayDict.keys():
                    raise SyntaxError(f"Undeclared variable {self.t.GetTokenStr(self.sym)}.")
            if self.sym in self.identTable:
                instID = self.ssa.GetVarInstNode(self.sym, currBB)
                varVersion = self.ssa.GetVarVersion(self.sym, currBB)
                operands = (1, (varVersion[0], self.sym))
                self.next()
            elif self.sym in self.arrayDict:
                print("Loading array")
                ident = self.sym
                self.next()
                arrBaseInstID, offSetID, instList = self.arrayAddrInstCalculation(ident, currBB)
                instID, _ = self.ssa.DefineIR(IRTokens.loadToken, currBB, arrBaseInstID, offSetID)

                operands = (3, (0, arrBaseInstID, offSetID))

        # “(“ expression “)”
        elif self.sym == Tokens.openparenToken:
            self.next()
            instID, instList, operands = self.expression()
            operands = (2, instID)
            self.CheckFor(Tokens.closeparenToken)
        # funcCall
        elif self.sym == Tokens.callToken:
            self.next()
            instID, instList, operands = self.funcCall()
            operands = (2, instID)

        if self.debug:
            print(f'{" " * self.level * self.spacing}Exit F{self.level}: {instID} {instList} {operands}')
        self.level -= 1
        return instID, instList, operands

    def arrayAddrInstCalculation(self, ident, currBB):
        print("in load array")
        print(self.ssa.instructionList)
        arrSize = self.arrayDict[ident]
        offSets = self.arrayOffset[ident]
        sumOffsetID = -1
        prevInstID = -1
        arrBaseInstID, flip = self.ssa.DefineIR(IRTokens.addToken, currBB, self.dataBaseAddr, self.arrayAddress[ident],
                                                var1=(0, self.dataBaseAddr), var2=(0,self.arrayAddress[ident]))
        loadInstList = []
        # address offset calculations
        # whatever expression is calculated above needs to be multiplied with the precomputed offset
        # A[M][N][O]
        # ex A[i][j][k] loads the address: (base + a_base) + 4*((N*O * i) + (O * j) + k)
        # the offset is precomputed in self.arrayOffset, so for example, A's offset would have [N*O, O, 1]

        for i in range(len(arrSize)):
            self.CheckFor(Tokens.openbracketToken)
            instID, instList, operands = self.expression()
            loadInstList += instList
            self.CheckFor(Tokens.closebracketToken)
            # the last offset is always 1, so no need to multiply it
            if offSets[i][1] != -1:
                instID, flip = self.ssa.DefineIR(IRTokens.mulToken, currBB,
                                              instID, offSets[i][1], var1=operands, var2=(0, offSets[i][1]))
                if flip:
                    loadInstList.append((instID, (0, offSets[i][1]), operands))
                else:
                    loadInstList.append((instID, operands, (0, offSets[i][1])))
                operands = (2, instID)

            if i > 0:
                if sumOffsetID == -1:
                    sumOffsetID, _ = self.ssa.DefineIR(IRTokens.addToken, currBB, prevInstID, instID,
                                                       var1=(2, prevInstID), var2=operands)
                    if flip:
                        loadInstList.append((instID, operands, (2, prevInstID)))
                    else:
                        loadInstList.append((instID, (2, prevInstID), operands))
                else:
                    sumOffsetID, _ = self.ssa.DefineIR(IRTokens.addToken, currBB, sumOffsetID, instID,
                                                       var1=(2, sumOffsetID), var2=operands)
                    if flip:
                        loadInstList.append((instID, operands, (2, sumOffsetID)))
                    else:
                        loadInstList.append((instID, (2, sumOffsetID), operands))
            prevInstID = instID
        wordSize, _ = self.ssa.DefineIR(IRTokens.constToken, currBB, 4)
        offSetID, flip = self.ssa.DefineIR(IRTokens.mulToken, currBB, instID, wordSize, var1=operands, var2=(0, wordSize))
        if flip:
            loadInstList.append((offSetID, (0, wordSize), operands))
        else:
            loadInstList.append((offSetID, operands, (0, wordSize)))

        return arrBaseInstID, offSetID, loadInstList


if __name__ == '__main__':
    filePath = './tests/whileTests/whileCSERelations'
    #comp = Parser(filePath + ".txt", True)
    comp = Parser("./test.txt", False)
    comp.computation()
    #comp.PrintSSA()
    dot = comp.GenerateDot(varMode=True, debugMode=False)
    # with open(filePath + '.dot', 'w') as f:
    #     f.write(dot)
    print(dot)
    comp.close()
