from __future__ import annotations
from cfg import *
from tokens import *


class SSA:
    """
    Maintains control flow graphs, basic blocks, value tables
    """

    def __init__(self, tokenizer, debug=False):
        self.opDct = {
            IRTokens.constToken: "const",
            IRTokens.addToken: 'add',
            IRTokens.subToken: 'sub',
            IRTokens.mulToken: 'mul',
            IRTokens.divToken: 'div',
            IRTokens.cmpToken: 'cmp',
            IRTokens.addaToken: 'adda',
            IRTokens.loadToken: 'load',
            IRTokens.storeToken: 'store',
            IRTokens.endToken: 'end',
            IRTokens.phiToken: 'phi',
            IRTokens.braToken: 'bra',
            IRTokens.bneToken: 'bne',
            IRTokens.beqToken: 'beq',
            IRTokens.bleToken: 'ble',
            IRTokens.bltToken: 'blt',  # bacon lettuce tomato
            IRTokens.bgeToken: 'bge',
            IRTokens.bgtToken: 'bgt',

            IRTokens.nopToken: 'nop',
            IRTokens.emptyToken: '\\<empty\\>',

            IRTokens.readToken: 'read',
            IRTokens.writeToken: 'write',
            IRTokens.writeNLToken: 'writeNL'
        }

        self.uncopyableInstruction = [
            IRTokens.endToken,

            IRTokens.braToken,
            IRTokens.bneToken,
            IRTokens.beqToken,
            IRTokens.bleToken,
            IRTokens.bltToken,
            IRTokens.bgeToken,
            IRTokens.bgtToken,

            IRTokens.readToken,
            IRTokens.writeToken,
            IRTokens.writeNLToken,

            IRTokens.nopToken,
            IRTokens.emptyToken
        ]

        # it's commutative, not agnostic
        self.operandAgnostic = [
            IRTokens.addToken,
            IRTokens.mulToken
        ]

        self.instructionCount = 0  # always incrementing
        self.instructionList = []

        # I guess we don't need this if we're just appending to BBList
        # and never deleting
        self.basicBlockCount = 0  # always incrementing

        self.BBList = []
        self.BBList.append(BasicBlock(self.GetNextBBID()))
        block1 = BasicBlock(self.GetNextBBID())
        self.BBList[0].AddChild(block1.bbID)
        block1.AddParent(0)
        block1.AddDominator(0)
        block1.AddIDominator(0)
        self.BBList.append(block1)
        self.CurrentBasicBlock = 1
        self.t = tokenizer

        self.phiNodes = []

    def GetNextBBID(self):
        # Gets the next BBID and increments BBID count
        ID = self.basicBlockCount
        self.basicBlockCount += 1
        return ID

    def GetNextInstID(self):
        ID = self.instructionCount
        self.instructionCount += 1
        return ID

    def GetInstPosInBB(self, instID, bb_id):
        insts = self.BBList[bb_id].instructions
        for i in range(len(insts)):
            if insts[i] == instID:
                return i
        return -1

    def DefineIR(self, operation, bb_id, operand1=None, operand2=None, inst_position=-1, var1=None, var2=None):
        """
        Called by parser to generate an IR code
        :param operation: the operation {add, sub, mul, div, cmp, phi, and others}
        :param operand1: first operand, may be omitted (in case of read and end)
        :param operand2: second operand, may be omitted
        :param inst_position: position of the instruction to be inserted in the basic block (for while loop)
        :return: instruction node ID (either one seen previously or a newly generated one)
        """

        instID = self.FindPreviousInst(operation, operand1, operand2, bb_id)
        # if no instructions are found, create a new instruction
        if instID == -1 or operation == IRTokens.phiToken:
            if operation in self.operandAgnostic:
                instID = self.FindPreviousInst(operation, operand2, operand1, bb_id)
                if instID != -1:
                    return instID, True
            instID = self.GetNextInstID()
            if operation == IRTokens.constToken:
                instruction = InstructionNode(operation, operand1, operand2, instID, 0, firstVarPair=(var1, var2))
                print(f'Instruction made: ({instID}, {0}): {self.opDct[operation]} {operand1} {operand2}')
                self.instructionList.append(instruction)
                self.BBList[0].instructions.append(instID)
                self.BBList[0].opTables[operation].insert(0, (instID, operand1))
            else:
                instruction = InstructionNode(operation, operand1, operand2, instID, bb_id, firstVarPair=(var1, var2))
                print(f'Instruction made: ({instID}, {self.CurrentBasicBlock}): '
                      f'{self.opDct[operation]} {operand1} {operand2}')
                self.instructionList.append(instruction)
                if inst_position != -1:
                    self.BBList[bb_id].instructions.insert(inst_position, instID)
                else:
                    # insert phi instructions at the beginning, but in order of insertion
                    if operation == IRTokens.phiToken:
                        if len(self.BBList[bb_id].instructions) == 0:
                            self.BBList[bb_id].instructions.append(instID)
                        else:
                            for i in range(len(self.BBList[bb_id].instructions)):
                                inst = self.instructionList[self.BBList[bb_id].instructions[i]]
                                if inst.instruction != IRTokens.phiToken:
                                    self.BBList[bb_id].instructions.insert(i, instID)
                                    break
                            else:
                                self.BBList[bb_id].instructions.append(instID)
                    else:
                        self.BBList[bb_id].instructions.append(instID)
                self.BBList[bb_id].opTables[operation].insert(0, (instID, operand1, operand2))
        return instID, False

    def GetInstNode(self, instID):
        return self.instructionList[instID]

    def ChangeOperands(self, instID, op1=None, op2=None):
        self.instructionList[instID].setOperands(op1, op2)

    def ChangeVarPair(self, instID, tup):
        self.instructionList[instID].setFirstVarPair(tup)

    def ChangeInstruction(self, instID, instruction):
        self.instructionList[instID].setInstruction(instruction)

    def AddInstDependency(self, instID, var):
        self.instructionList[instID].addVarDependency(var)

    def FindPreviousInst(self, operation: IRTokens, operand1, operand2, bb_id):
        """
        Finds the previous instruction, if it exists
        Will look up the dominator path until it's found
        :param operation:
        :param operand1:
        :param operand2:
        :param bb_id:
        :return:
        """
        # essentially, these instructions are not assignable
        # each instance of it is unique
        # eg. the read at inst i is not going to be the same as read at inst j
        if operation in self.uncopyableInstruction:
            return -1

        if operation == IRTokens.constToken:
            for const in self.BBList[0].opTables[IRTokens.constToken]:
                if const[1] == operand1:
                    return const[0]
        else:
            dom_list = self.BBList[bb_id].dominators
            for dom_block in dom_list:
                op_list = self.BBList[dom_block].opTables[operation]
                for inst in op_list:
                    # entries are (instID, op1, op2)
                    if inst[1] == operand1 and inst[2] == operand2:
                        return inst[0]
        return -1

    def AssignVariable(self, varToken, instID, bb_id, operands=None):
        """
        Updates the value table in the current basic block
        If the variable has been assigned before, create a new version (maintains SSA)
        :param varToken: the variable token to be updated
        :param instID: the instruction assigned to the variable
        :param bb_id: the basic block ID
        :return: void
        """
        if operands is None:
            operands = []
        (n, inst, op) = self.GetVarVersion(varToken, bb_id)
        varSSAVal = (n, inst, op)
        if bb_id != 0:
            if n != -1 and inst != instID:
                if varToken in self.BBList[bb_id].valueTable:
                    varSSAVal = (n + 1, instID, operands)
                    self.BBList[bb_id].valueTable[varToken].insert(0, (n + 1, instID, operands))
                else:
                    varSSAVal = (n + 1, instID, operands)
                    self.BBList[bb_id].valueTable[varToken] = [(n + 1, instID, operands)]
            elif n == -1:
                varSSAVal = (0, instID, operands)
                self.BBList[bb_id].valueTable[varToken] = [(0, instID, operands)]
            return varSSAVal
        else:
            raise Exception("Basic block 0 has no variables")

    def GetVarInstNode(self, varToken, bb_id: int = -1):
        """
        Finds the latest SSA value of the program variable in a basic block.
        Will traverse through the dominator blocks if needed.

        If variable does not exist, it throws a warning and assigns it with value 0.

        :param varToken: variable token
        :param bb_id: the basic block to search through
        :return:
        """
        blockID = self.CurrentBasicBlock
        if bb_id != -1:
            blockID = bb_id
        dom_list = self.BBList[blockID].dominators
        for dom_block in dom_list:
            if varToken in self.BBList[dom_block].valueTable:
                # return first entry that is active
                for version in self.BBList[dom_block].valueTable[varToken]:
                    if self.instructionList[version[1]].active:
                        return self.BBList[dom_block].valueTable[varToken][0][1]
        # if we reached here, that means this variable does not have a value
        print("WARNING: variable not instantiated. Assigning variable with value 0.")
        instID, _ = self.DefineIR(IRTokens.constToken, self.CurrentBasicBlock, 0)
        self.AssignVariable(varToken, instID, self.CurrentBasicBlock)
        return instID

    def GetVarVersion(self, varToken, bb_id: int = -1, varVersion: int = -1, prevBB=False, phi=False):
        """
        Finds the SSA version of the program variable
        If variable does not exist in record, return (-1, -1, -1).
        :param varToken: variable token
        :param bb_id:
        :param varVersion: if specified, returns the first version specified
        :param prevBB: if specified, will not search from the current basic block
        :return:
        """
        blockID = self.CurrentBasicBlock
        if bb_id != -1:
            blockID = bb_id
        dom_list = self.BBList[blockID].dominators
        for dom_block in dom_list:
            if not prevBB or dom_block != bb_id:
                if varToken in self.BBList[dom_block].valueTable:
                    # if we're not looking for a particular version
                    # return first entry that contains active instruction
                    for version in self.BBList[dom_block].valueTable[varToken]:
                        if varVersion == -1:
                            if self.instructionList[version[1]].active or phi:
                                return version
                        if version[0] == varVersion:
                            return version
        return -1, -1, -1

    def CreateNewBasicBlock(self, dom_list, parent_list, idom_list, blockType="", joinType=0):
        """
        Creates a new block and sets current basic block to new block
        :param dom_list: list of blocks that dominate this block
        :param parent_list: list of parents for this block
        :return: ID of this block
        """
        BBID = self.GetNextBBID()
        block = BasicBlock(BBID, None, parent_list, dom_list, idom_list, blockType=blockType, joinType=joinType)
        self.BBList.append(block)
        self.CurrentBasicBlock = BBID
        return BBID

    def AddPhiNode(self, identToken, firstSSA, joinBlocks, currBB):
        # Adds a phi node to the iterated dominance frontier, aka the joinBlocks
        # Join block characteristics:
        #     if/else: phi nodes will always be the first ones inserted

        #     while:
        # Algorithm:
        #  Loop through the IDF, from the innermost block
        #      Three cases:
        #
        ssaVal = firstSSA
        ssaBB = currBB
        print(f'IN ADD PHI {self.t.GetTokenStr(identToken)}, {identToken}, joins: {joinBlocks}')
        whilePhi = []
        for opType, joinID, entryID in reversed(joinBlocks):
            phiInstVar = self.GetVarVersion(identToken, joinID, phi=True)
            entryInstVar = self.GetVarVersion(identToken, entryID)

            # if phi function does not exist in the join block yet
            #    create phi function
            if phiInstVar[1] == entryInstVar[1] and phiInstVar[1] != -1:
                if opType == 0:# or opType == 2:
                    op1 = ssaVal
                    op2 = entryInstVar[1]
                else:
                    op1 = entryInstVar[1]
                    op2 = ssaVal
                if op1 != op2:
                    ssaVal, _ = self.DefineIR(IRTokens.phiToken, joinID, op1, op2, var1=(1, (0, identToken)),
                                              var2=(1,(0, identToken)))
                    if opType == 2:
                        whilePhi.append((joinID, ssaVal))
                    self.AssignVariable(identToken, ssaVal, joinID)
                    print(f"INSERT PHI {op1} {op2}")
            # otherwise, some function exists
            #     this means that the identToken is a later assignment than the previous
            #     assignment and should be updated to this
            elif phiInstVar[1] != entryInstVar[1] and phiInstVar[1] != -1:
                phiInstNode = self.instructionList[phiInstVar[1]]
                if phiInstNode.instruction == IRTokens.phiToken:
                    if opType == 0:# or opType == 2:
                        op1 = ssaVal
                        op2 = phiInstNode.operand2
                    else:
                        op1 = phiInstNode.operand1
                        op2 = ssaVal
                    if opType == 2:
                        whilePhi.append((joinID, phiInstNode.instID))

                    phiInstNode.setOperands(op1, op2)
                    # we then check if the phi node is actually needed
                    # if it is, then we set it to active
                    if op1 != op2:
                        phiInstNode.setActiveStatus(True)
                        ssaVal = phiInstNode.instID
                    else:
                        phiInstNode.setActiveStatus(False)
                else:
                    # this occurs when there's an assignment in the join block
                    #  happens when we use uninitialized variables in relation
                    if opType == 0:# or opType == 2:
                        op1 = ssaVal
                        op2 = phiInstNode.instID
                    else:
                        op1 = phiInstNode.instID
                        op2 = ssaVal
                    ssaVal, _ = self.DefineIR(IRTokens.phiToken, joinID, op1, op2, var1=(1, (0, identToken)),
                                              var2=(1,(0, identToken)))
                    if opType == 2:
                        whilePhi.append((joinID, ssaVal))
                    self.AssignVariable(identToken, ssaVal, joinID)
            else:
                # if we're here, that means that the variable was initialized inside an inner block
                print("WARNING: Variable initialized inside inner scope.")
                zeroInstID, _ = self.DefineIR(IRTokens.constToken, joinID, 0)
                self.AssignVariable(identToken, zeroInstID, joinID)
                if opType == 0:# or opType == 2:
                    op1 = ssaVal
                    op2 = zeroInstID
                else:
                    op1 = zeroInstID
                    op2 = ssaVal
                ssaVal, _ = self.DefineIR(IRTokens.phiToken, joinID, op1, op2, var1=(1, (0, identToken)),
                                              var2=(1,(0, identToken)))
                if opType == 2:
                    whilePhi.append((joinID, ssaVal))
                self.AssignVariable(identToken, ssaVal, joinID)

        # iterate through join stack in reverse
        # update the entry ssa
        # rule: if the outer join is while, then entrySSA should be whileSSA value
        #       if the outer join is if/else, then entrySSA should stay as is
        for joinID, instID in whilePhi:
            op1 = self.GetVarVersion(identToken, joinID, prevBB=True)[1]
            print(self.instructionList[instID])
            if op1 != -1:
                phiInstNode = self.instructionList[instID].setOperands(operand1=op1)

    def whilePhi(self, joinID, latestDoID, varEntries):
        print(f"IN WHILE PHI! Parameters: {joinID} {latestDoID}")
        print(varEntries)
        # need to update CMP and other operands in the doblock
        # main items:
        #     if a later variable needs the unmodified instruction,
        #       that is up to the later variable to make in their basic block
        exploreStack = []
        explored = []
        currID = joinID
        explored.append(joinID)
        for child in self.BBList[currID].children:
            exploreStack.append(child)
        self.whilePhiBBHelper1(currID, joinID)
        # then we go down the DO nodes
        currID = -1

        while currID != joinID and len(exploreStack) != 0:
            currID = exploreStack.pop(0)
            print(currID, exploreStack)
            if currID not in explored:
                explored.append(currID)
                for child in self.BBList[currID].children:
                    exploreStack.append(child)

                self.whilePhiBBHelper1(currID, joinID)
                self.whilePhiBBHelper2(currID, joinID)

        print('EXITING PHI')

    def whilePhiBBHelper1(self, bbID, joinID):
        # this function first resets the SSA operands in the basic block
        currInstList = self.BBList[bbID].instructions.copy()
        phiInst = {}
        # if bbID != joinID:
        #     # the phi instructions replaces the previous version of variable
        #     for k, v in self.BBList[joinID].valueTable.items():
        #         phiInst[(v[0][0] - 1, k)] = v[0][1]

        for i in range(len(currInstList)):
            currNode = self.instructionList[currInstList[i]]
            if currNode.instruction in [IRTokens.addToken, IRTokens.subToken, IRTokens.mulToken,
                                        IRTokens.divToken, IRTokens.cmpToken]:
                oldOp1 = currNode.operand1
                oldOp2 = currNode.operand2
                nodeVar1 = currNode.firstVarPair[0]
                nodeVar2 = currNode.firstVarPair[1]
                op1 = self.whilePhiGetNodeInstID(nodeVar1, currNode.instID, bbID, joinID)
                op2 = self.whilePhiGetNodeInstID(nodeVar2, currNode.instID, bbID, joinID)

                currNode.setOperands(op1, op2)
                # replace the entry in the basic block's operation table
                for opIdx in range(len(self.BBList[bbID].opTables[currNode.instruction])):
                    if self.BBList[bbID].opTables[currNode.instruction][opIdx] == (currNode.instID, oldOp1, oldOp2):
                        self.BBList[bbID].opTables[currNode.instruction][opIdx] = (currNode.instID, op1, op2)
                        break
            elif currNode.instruction == IRTokens.phiToken:
                if self.BBList[bbID].joinType == 1:
                    ident = currNode.firstVarPair[0][1][1]
                    op1 = self.GetVarVersion(ident, bbID, prevBB=True)[1]
                    if op1 != -1:
                        self.ChangeOperands(currNode.instID, op1=op1)


                # oldOp1 = currNode.operand1
                # oldOp2 = currNode.operand2
                # nodeVar1 = currNode.firstVarPair[0]
                # nodeVar2 = currNode.firstVarPair[1]
                # op1 = self.whilePhiGetNodeInstID(nodeVar1, currNode.instID, bbID, joinID)
                # op2 = self.whilePhiGetNodeInstID(nodeVar2, currNode.instID, bbID, joinID)
                #
                # currNode.setOperands(op1, op2)
    def whilePhiBBHelper2(self, bbID, joinID):
        # now we go through each variable's history.
        # history is in chronological order of creation.
        # we go through each one by one, generating a new SSA instruction if needed

        if bbID != joinID:
            for k, v in self.BBList[bbID].valueTable.items():
                newSSA = []
                for i, ssaVersion in reversed(list(enumerate(v))):
                    phiInstID = self.GetVarInstNode(k, joinID)
                    ver = ssaVersion[0]
                    ssaInstID = ssaVersion[1] # self.instructionList[phiInstID].operand1
                    instChanges = {}
                    newHist = []
                    # print(self.t.GetTokenStr(k), v)

                    for hist in ssaVersion[2]:
                        # gather both current and previous instruction operand for comparison
                        instID = hist[0]

                        nodeVar1 = hist[1]
                        nodeVar2 = hist[2]

                        newSSAOp1 = self.whilePhiGetNodeInstID(nodeVar1, instID, bbID, joinID)
                        if newSSAOp1 in instChanges:
                            newSSAOp1 = instChanges[newSSAOp1]

                        newSSAOp2 = self.whilePhiGetNodeInstID(nodeVar2, instID, bbID, joinID)
                        if newSSAOp2 in instChanges:
                            newSSAOp2 = instChanges[newSSAOp2]

                        instNode = self.instructionList[instID]
                        op1 = instNode.operand1
                        op2 = instNode.operand2

                        # operands have been changed, so either
                        #    1. some intermediate SSA values have been changed
                        #       but the original variables are the same
                        #    2. or we need to create a new SSA instruction
                        if op1 != newSSAOp1 or op2 != newSSAOp2:
                            node1TF = False
                            node2Tf = False
                            instBBID = self.FindInstBlock(instID)
                            if nodeVar1[0] == 1 and instNode.firstVarPair[0] == nodeVar1:
                                varVers = self.GetVarVersion(nodeVar1[1][1], instBBID)[1]
                                if varVers != op1 and instBBID != bbID:
                                    node1TF = True
                            if nodeVar2[0] == 1 and instNode.firstVarPair[1] == nodeVar2:
                                varVers = self.GetVarVersion(nodeVar2[1][1], instBBID)[1]
                                if varVers != op2 and instBBID != bbID:
                                    node2TF = True

                            if node1TF and node2TF:
                                instNode.setOperands(newSSAOp1, newSSAOp2)
                            else:
                                newNodeVar1 = nodeVar1
                                if nodeVar1[0] != 1:
                                    newNodeVar1 = (nodeVar1[0], newSSAOp1)
                                newNodeVar2 = nodeVar2
                                if nodeVar2[0] != 1:
                                    newNodeVar2 = (nodeVar2[0], newSSAOp2)

                                bbFirstInst = self.GetFirstInstInBlock(bbID)
                                flip = False
                                if self.instructionList[bbFirstInst].instruction == IRTokens.emptyToken:
                                    self.ChangeOperands(bbFirstInst, newSSAOp1, newSSAOp2)
                                    self.ChangeInstruction(bbFirstInst, instNode.instruction)
                                    self.ChangeVarPair(bbFirstInst, (newNodeVar1, newNodeVar2))
                                    newInstID = bbFirstInst
                                else:
                                    instPos = self.GetInstPosInBB(instID, bbID)
                                    instPos += 1
                                    newInstID, flip = self.DefineIR(instNode.instruction, bb_id=bbID,
                                                                    operand1=newSSAOp1, operand2=newSSAOp2,
                                                                    inst_position=instPos, var1=newNodeVar1,
                                                                    var2=newNodeVar2)
                                instChanges[instID] = newInstID
                                instID = newInstID
                                if flip:
                                    nodeVar1 = newNodeVar2
                                    nodeVar2 = newNodeVar1
                                else:
                                    nodeVar1 = newNodeVar1
                                    nodeVar2 = newNodeVar2

                        newHist.append((instID, nodeVar1, nodeVar2))
                    # print(newHist)
                    if len(newHist) != 0:
                        ssaInstID = newHist[-1][0]
                    self.BBList[bbID].valueTable[k][i] = (ver, ssaInstID, newHist)
                    self.whilePhiBBHelper1(bbID, joinID)



    def whilePhiGetNodeInstID(self, nodeVar, currInstID, bbID, joinID):
        # this function selects the correct ssa value for the variable
        #     it looks inside the joinID provided
        op = None
        currInstPos = self.GetInstPosInBB(currInstID, bbID)
        if nodeVar is not None:
            op = nodeVar[1]
            if nodeVar[0] == 1:
                if bbID != joinID:
                    # if nodeVar[1] in phiInst:
                    #     op = phiInst[nodeVar[1]]
                    # else:
                    print(f'FIND NODE HISTORY: {nodeVar} {bbID} {joinID}')
                    if nodeVar[1][1] in self.BBList[bbID].valueTable:
                        versionHistory = self.BBList[bbID].valueTable[nodeVar[1][1]]
                    else:
                        versionHistory = []
                    pos = 0
                    prevPos = -2
                    for i in range(len(versionHistory)):
                        version = versionHistory[i]
                        pos = self.GetInstPosInBB(version[1], bbID)

                        # passes whileCSERelations
                        if pos < currInstPos:
                            op = version[1]
                            break
                        prevPos = pos
                    else:
                        bbDom = self.BBList[bbID].dominators[1]
                        op = self.GetVarVersion(nodeVar[1][1], bbDom)[1]
                        # last resort, this variable was initialized inside this join block
                        if op == -1:
                            op = self.BBList[joinID].valueTable[nodeVar[1][1]][0][1]
                    print(f'Node history is {op}')
                else:
                    op = self.GetVarVersion(nodeVar[1][1], bbID)[1]
        return op

    def FindInstBlock(self, instID):
        for block in self.BBList:
            for inst in block.instructions:
                if self.instructionList[inst].instID == instID:
                    return block.bbID
        return -1

    def GetCurrBasicBlock(self):
        return self.CurrentBasicBlock

    def SetCurrBasicBlock(self, bbID):
        self.CurrentBasicBlock = bbID

    def GetFirstInstInBlock(self, bbID):
        if len(self.BBList[bbID].instructions) > 0:
            return self.BBList[bbID].instructions[0]
        return -1

    def AddBlockChild(self, parentBBID, childBBID):
        if parentBBID > len(self.BBList):
            raise Exception("Invalid basic block")
        else:
            self.BBList[parentBBID].AddChild(childBBID)

    def AddBlockParent(self, childBBID, parentBBID):
        if childBBID > len(self.BBList) or parentBBID > len(self.BBList):
            raise Exception("Invalid basic block")
        else:
            self.BBList[childBBID].AddParent(parentBBID)

    def GetDomList(self, BBID):
        return self.BBList[BBID].dominators

    def GetBlockInsts(self, BBID):
        return self.BBList[BBID].instructions

    def GetValueTable(self, BBID):
        return self.BBList[BBID].valueTable

    def PrintInstructions(self):

        print(self.BBList[self.CurrentBasicBlock].valueTable)
        for inst in self.instructionList:
            op1 = inst.operand1
            if inst.operand1 is None:
                op1 = ""
            op2 = inst.operand2
            if inst.operand2 is None:
                op2 = ""
            op = inst.instruction
            instID = inst.instID
            print(f'({instID}, {inst.BB}): {self.opDct[op]} {op1} {op2}, variable pair: {inst.firstVarPair}, '
                  f'dependency: {inst.dependency}')

    def PrintBlocks(self):
        for block in self.BBList:
            print(block.bbID)
            print(f'    Dominators: {block.dominators}')
            print(f'    Parents: {block.parents}')
            print(f'    Children: {block.children}')
            print(f'    Instructions: {block.instructions}')

            values = ''
            first = True
            for k, v in block.valueTable.items():
                if first:
                    values += f'({self.t.GetTokenStr(k)}, {k}): {v}, \n'
                else:
                    values += " " * 13 + f'({self.t.GetTokenStr(k)}, {k}): {v}, \n'
                first = False
            values = '{' + values[:-2] + '}'
            print(f'    Values: {values}')
            optables = ''
            first = True
            for k, v in block.opTables.items():
                if len(v) > 0:
                    if first:
                        optables += f'{self.opDct[k]}: {v}, \n'
                    else:
                        optables += f'         {self.opDct[k]}: {v}, \n'
                    first = False
            print(f'    Ops: {optables}')

    def GenerateDot(self, tokenizer, varMode=False, debugMode=False):
        blockSect = []
        dagSect = []
        domSect = []

        color = ['blue', 'red', 'green',
                 'cyan3', 'purple', 'darkgreen',
                 'gold', 'orange', 'limegreen']

        for block in self.BBList:
            blockInfo = f"\tbb{block.bbID}[shape=record, label=\"<b>{block.blockType}BB{block.bbID}|{{"
            lenInst = len(block.instructions)
            for i in range(lenInst):
                inst = self.instructionList[block.instructions[i]]
                if not inst.active:
                    continue
                op1 = ""
                op2 = ""
                if inst.operand1 is not None:
                    if inst.instruction == IRTokens.constToken:
                        op1 = f' #{inst.operand1}'
                    else:
                        op1 = f' ({inst.operand1})'
                if inst.operand2 is not None:
                    if type(inst.operand2) == str:
                        op2 = f' ({self.GetFirstInstInBlock(int(inst.operand2[2:]))})'
                    else:
                        op2 = f' ({inst.operand2})'
                if debugMode:
                    instInfo = f"{inst.instID}: {self.opDct[inst.instruction]}{op1}{op2}, "
                    var1 = inst.firstVarPair[0]
                    var2 = inst.firstVarPair[1]
                    s1 = ''
                    s2 = ''
                    if var1 is None:
                        s1 = 'None'
                    else:
                        if var1[0] == 1:
                            s1 = f'({var1[1][0]}, {tokenizer.GetTokenStr(var1[1][1])})'
                        else:
                            s1 = f'({var1[1]})'

                    if var2 is None:
                        s2 = 'None'
                    else:
                        if var2[0] == 1:
                            s2 = f'({var2[1][0]}, {tokenizer.GetTokenStr(var2[1][1])})'
                        else:
                            s2 = f'({var2[1]})'

                    instInfo += f'({s1}, {s2})'

                else:
                    instInfo = f"{inst.instID}: {self.opDct[inst.instruction]}{op1}{op2}"
                if i < len(block.instructions) - 1:
                    instInfo += "|"
                blockInfo += instInfo
            if varMode and len(block.valueTable) != 0:
                blockInfo += "}|{"
                for k in block.valueTable:
                    valueInfo = ''
                    for v in block.valueTable[k]:
                        if debugMode:
                            versionString = f'({v[0]}, {v[1]}, ['
                            for vrsn in v[2]:
                                op1 = f'{vrsn[1][1]}'
                                if vrsn[1][0] == 1:
                                    op1 = f'({vrsn[1][1][0]}, {self.t.GetTokenStr(vrsn[1][1][1])})'
                                op2 = f'{vrsn[2][1]}'
                                if vrsn[2][0] == 1:
                                    op2 = f'({vrsn[2][1][0]}, {self.t.GetTokenStr(vrsn[2][1][1])})'
                                versionString += f'({vrsn[0]}, {op1}, {op2})'
                            valueVerInfo = f'{tokenizer.GetTokenStr(k)}: {versionString}])|'
                        else:
                            valueVerInfo = f'{tokenizer.GetTokenStr(k)}: ({v[0]}, {v[1]})|'
                        valueInfo += valueVerInfo
                    blockInfo += valueInfo
                blockInfo = blockInfo[:-1]

            blockInfo += "}\"];"
            blockSect.append(blockInfo)

            for parent in block.parents:
                edgeInfo = f"\tbb{parent}:s -> bb{block.bbID}:n"
                parentBlock = self.BBList[parent]
                parentLastInst = -1
                if len(parentBlock.instructions) > 0:
                    parentLastInst = self.instructionList[parentBlock.instructions[-1]]
                blockFirstInst = -1
                if len(block.instructions) > 0:
                    blockFirstInst = self.instructionList[block.instructions[0]]

                if type(parentLastInst) != int and type(blockFirstInst) != int:
                    if parentLastInst.instruction == 40:
                        if parentLastInst.operand1 == blockFirstInst.instID:
                            edgeInfo += "[label=\"branch\"]"#, constraint=false]"
                    elif 40 < parentLastInst.instruction < 47:
                        if parentLastInst.operand2 == blockFirstInst.instID:
                            edgeInfo += "[label=\"branch\"]"
                        else:
                            if type(parentLastInst.operand2) == str and int(parentLastInst.operand2[2:]) == block.bbID:
                                edgeInfo += "[label=\"branch\"]"
                            else:
                                edgeInfo += "[label=\"fall-through\"]"
                    else:
                        if parentBlock.bbID > 1:
                            edgeInfo += "[label=\"fall-through\"]"
                edgeInfo += ";"
                dagSect.append(edgeInfo)
            for domID in block.idominators:
                if domID != block.bbID and domID > 0:
                    domInfo = f"\tbb{domID}:b -> bb{block.bbID}:b [color=\"{color[domID % len(color)]}\", " \
                              f"style=dashed, label=\"dom\"];"
                    domSect.append(domInfo)

        separator = "\n"
        dot = f'digraph G {{\n{separator.join(blockSect)}\n\n{separator.join(dagSect)}\n{separator.join(domSect)} \n}}'
        print(dot)
        return dot
