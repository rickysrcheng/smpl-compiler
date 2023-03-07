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
            IRTokens.bltToken: 'blt', # bacon lettuce tomato
            IRTokens.bgeToken: 'bge',
            IRTokens.bgtToken: 'bgt',

            IRTokens.nopToken: 'nop',
            IRTokens.emptyToken: '\\<empty\\>',

            IRTokens.readToken: 'read',
            IRTokens.writeToken: 'write',
            IRTokens.writeNLToken: 'writeNL'
        }

        self.unassignableInstruction = [
            IRTokens.endToken,

            IRTokens.braToken,
            IRTokens.bneToken,
            IRTokens.beqToken,
            IRTokens.bleToken,
            IRTokens.bltToken,
            IRTokens.bgeToken,
            IRTokens.bgtToken,

            IRTokens.writeToken,
            IRTokens.writeNLToken,

            IRTokens.nopToken,
            IRTokens.emptyToken
        ]

        self.instructionCount = 0 # always incrementing
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
        self.BBList.append(block1)
        self.CurrentBasicBlock = 1
        self.t = tokenizer

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
            instID = self.GetNextInstID()
            if operation == IRTokens.constToken:
                instruction = InstructionNode(operation, operand1, operand2, instID, 0, firstVarPair=(var1, var2))
                print(f'Instruction made: ({instID}, {0}): {self.opDct[operation]} {operand1} {operand2}')
                self.instructionList.append(instruction)
                self.BBList[0].instructions.append(instID)
                self.BBList[0].opTables[operation].insert(0, (instID, operand1))
            else:
                instruction = InstructionNode(operation, operand1, operand2, instID, bb_id, firstVarPair=(var1, var2))
                print(f'Instruction made: ({instID}, {self.CurrentBasicBlock}): {self.opDct[operation]} {operand1} {operand2}')
                self.instructionList.append(instruction)
                if inst_position != -1:
                    self.BBList[bb_id].instructions.insert(inst_position, instID)
                else:
                    self.BBList[bb_id].instructions.append(instID)
                self.BBList[bb_id].opTables[operation].insert(0, (instID, operand1, operand2))
        return instID

    def ChangeOperands(self, instID, op1, op2=None):
        self.instructionList[instID].setOperands(op1, op2)

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
        if operation in self.unassignableInstruction:
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
                # return first entry
                return self.BBList[dom_block].valueTable[varToken][0][1]
        # if we reached here, that means this variable does not have a value
        print("WARNING: variable not instantiated. Assigning variable with value 0.")
        instID = self.DefineIR(IRTokens.constToken, self.CurrentBasicBlock, 0)
        self.AssignVariable(varToken, instID, self.CurrentBasicBlock)
        return instID

    def GetVarVersion(self, varToken, bb_id: int = -1, varVersion: int = -1):
        """
        Finds the SSA version of the program variable
        If variable does not exist in record, return (-1, -1, -1).
        :param varToken: variable token
        :param bb_id:
        :param varVersion: if specified, returns the first version specified
        :return:
        """
        blockID = self.CurrentBasicBlock
        if bb_id != -1:
            blockID = bb_id
        dom_list = self.BBList[blockID].dominators
        for dom_block in dom_list:
            if varToken in self.BBList[dom_block].valueTable:
                # return first entry
                if varVersion == -1:
                    return self.BBList[dom_block].valueTable[varToken][0]
                else:
                    for version in self.BBList[dom_block].valueTable[varToken]:
                        if version[0] == varVersion:
                            return version
        return -1, -1, -1

    def CreateNewBasicBlock(self, dom_list, parent_list):
        """
        Creates a new block and sets current basic block to new block
        :param dom_list: list of blocks that dominate this block
        :param parent_list: list of parents for this block
        :return: ID of this block
        """
        BBID = self.GetNextBBID()
        block = BasicBlock(BBID, None, parent_list, dom_list)
        self.BBList.append(block)
        self.CurrentBasicBlock = BBID
        return BBID

    def AddPhiNode(self, identToken, firstSSA, joinBlocks):
        ssaVal = firstSSA
        for opType, joinID, entryID in joinBlocks:
            print(opType, joinID, entryID)
            phiInstNode = self.GetVarVersion(identToken, joinID)
            if phiInstNode == (-1, -1, -1):
                if opType == 0:
                    op1 = ssaVal
                    op2 = self.GetVarInstNode(identToken, entryID)
                else:
                    op1 = self.GetVarInstNode(identToken, entryID)
                    op2 = ssaVal
                print(f"INSERT PHI {op1} {op2}")
            print(phiInstNode)


    def ifElsePhi(self, thenID, joinID, entryID, varEntries, elseID=-1):
        phiInsts = {}
        thenValTable = self.BBList[thenID].valueTable
        print(f"IN PHI! Parameters: {entryID} {thenID} {elseID} {joinID}")
        print(varEntries)
        # first reconcile ifs with dominating blocks
        # then we loop through else blocks, if it exists
        for var in varEntries:
            entrySSA = self.GetVarVersion(var, entryID)
            thenSSA = self.GetVarVersion(var, thenID)
            elseSSA = (-1, -1)
            if elseID != -1:
                elseSSA = self.GetVarVersion(var, elseID)
            print(var, entrySSA, thenSSA, elseSSA)
            # if then path modifies a variable
            if entrySSA != thenSSA:
                if elseSSA != (-1, -1):
                    phiInsts[var] = (thenSSA[1], elseSSA[1])
                else:
                    phiInsts[var] = (thenSSA[1], entrySSA[1])
            elif entrySSA != elseSSA:
                if elseSSA != (-1, -1):
                    print('here')
                    phiInsts[var] = (entrySSA[1], elseSSA[1])

        for k, v in thenValTable.items():
            prevSSA = self.GetVarInstNode(k, self.BBList[thenID].dominators[1])
            print(k, v, prevSSA)
            phiInsts[k] = (v[0][1], prevSSA)

        print(phiInsts, thenID, elseID)
        for k, v in phiInsts.items():
            print(v)
            instID = self.DefineIR(IRTokens.phiToken, joinID, v[0], v[1])
            self.AssignVariable(k, instID, joinID)
        print('EXITING PHI')

    def whilePhi(self, joinID, latestDoID, varEntries):
        phiInsts = {}
        thenValTable = self.BBList[latestDoID].valueTable
        print(f"IN WHILE PHI! Parameters: {joinID} {latestDoID}")
        print(varEntries)
        # first reconcile ifs with dominating blocks
        # then we loop through else blocks, if it exists
        for var in varEntries:
            entrySSA = self.GetVarVersion(var, joinID)
            doSSA = self.GetVarVersion(var, latestDoID)
            # if do path modifies a variable
            if entrySSA != doSSA:
                phiInsts[var] = (doSSA[1], entrySSA[1])

        idx = 0
        for k, v in phiInsts.items():
            instID = self.DefineIR(IRTokens.phiToken, joinID, v[0], v[1], idx)
            idx += 1
            self.AssignVariable(k, instID, joinID)

        # then need to update CMP and other operands in the doblock
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
                self.whilePhiBBHelper2(currID, joinID)

        # there should only be phi nodes assignments in join block
        # ^not true, case with uninitialized variables
        # but latest version should only be phi nodes
        for k, v in self.BBList[joinID].valueTable.items():
            instID = v[0][1]
            doSSA = self.GetVarVersion(k, latestDoID)

            instNode = self.instructionList[instID]
            if instNode.instruction == IRTokens.phiToken:
                instNode.setOperands(doSSA[1], instNode.operand2)

        print('EXITING PHI')

    def whilePhiBBHelper1(self, bbID, joinID):
        currInstList = self.BBList[bbID].instructions.copy()
        phiInst = {}
        if bbID != joinID:
            # the phi instructions replaces the previous version of variable
            for k, v in self.BBList[joinID].valueTable.items():
                phiInst[(v[0][0] - 1, k)] = v[0][1]
        for i in range(len(currInstList)):
            currNode = self.instructionList[currInstList[i]]
            if currNode.instruction in [IRTokens.addToken, IRTokens.subToken, IRTokens.mulToken,
                                        IRTokens.divToken, IRTokens.cmpToken]:
                oldOp1 = currNode.operand1
                oldOp2 = currNode.operand2
                nodeVar1 = currNode.firstVarPair[0]
                nodeVar2 = currNode.firstVarPair[1]
                op1 = self.whilePhiGetNodeInstID(nodeVar1, phiInst, bbID, joinID)
                op2 = self.whilePhiGetNodeInstID(nodeVar2, phiInst, bbID, joinID)

                currNode.setOperands(op1, op2)
                # replace the entry in the basic block's operation table
                for opIdx in range(len(self.BBList[bbID].opTables[currNode.instruction])):
                    if self.BBList[bbID].opTables[currNode.instruction][opIdx] == (currNode.instID, oldOp1, oldOp2):
                        self.BBList[bbID].opTables[currNode.instruction][opIdx] = (currNode.instID, op1, op2)
                        break

    def whilePhiBBHelper2(self, bbID, joinID):
        phiInst = {}
        if bbID != joinID:
            # the phi instructions replaces the previous version of variable
            for k, v in self.BBList[joinID].valueTable.items():
                phiInst[(v[0][0]-1, k)] = v[0][1]

        # now we go through each variable's history.
        # history is in chronological order of creation.
        # we go through each one by one, generating a new SSA instruction if needed

        if bbID != joinID:
            for k, v in self.BBList[bbID].valueTable.items():
                newSSA = []
                for i, ssaVersion in reversed(list(enumerate(v))):
                    ver = ssaVersion[0]
                    ssaInstID = ssaVersion[1]
                    instChanges = {}
                    newHist = []
                    #print(self.t.GetTokenStr(k), v)

                    for hist in ssaVersion[2]:
                        # gather both current and previous instruction operand for comparison
                        instID = hist[0]

                        nodeVar1 = hist[1]
                        nodeVar2 = hist[2]

                        histOp1 = self.whilePhiGetNodeInstID(nodeVar1, phiInst, bbID, joinID)
                        if histOp1 in instChanges:
                            histOp1 = instChanges[histOp1]

                        histOp2 = self.whilePhiGetNodeInstID(nodeVar2, phiInst, bbID, joinID)
                        if histOp2 in instChanges:
                            histOp2 = instChanges[histOp2]

                        instNode = self.instructionList[instID]
                        op1 = instNode.operand1
                        op2 = instNode.operand2
                        #print(instID, histOp1, histOp2, op1, op2)
                        # operands have been changed, so we need to create a new instruction
                        if op1 != histOp1 or op2 != histOp2:
                            newNodeVar1 = nodeVar1
                            if nodeVar1[0] != 1:
                                newNodeVar1 = (nodeVar1[0], histOp1)
                            newNodeVar2 = nodeVar2
                            if nodeVar2[0] != 1:
                                newNodeVar2 = (nodeVar2[0], histOp2)

                            instPos = self.GetInstPosInBB(instID, bbID)
                            instPos += 1
                            newInstID = self.DefineIR(instNode.instruction, bb_id=bbID,
                                                      operand1=histOp1, operand2=histOp2,
                                                      inst_position=instPos, var1=newNodeVar1, var2=newNodeVar2)
                            instChanges[instID] = newInstID
                            instID = newInstID
                            nodeVar1 = newNodeVar1
                            nodeVar2 = newNodeVar2

                        newHist.append((instID, nodeVar1, nodeVar2))
                    #print(newHist)
                    if len(newHist) != 0:
                        ssaInstID = newHist[-1][0]
                    self.BBList[bbID].valueTable[k][i] = (ver, ssaInstID, newHist)
                    self.whilePhiBBHelper1(bbID, joinID)
                    newSSA.insert(0, (ver, ssaInstID, newHist))
                #print(self.t.GetTokenStr(k), "NEW SSA")
                #print(v)
                #print(newSSA)
                #self.BBList[bbID].valueTable[k] = newSSA

    def whilePhiGetNodeInstID(self, nodeVar, phiInst, bbID, joinID):
        op = None
        if nodeVar is not None:
            op = nodeVar[1]
            if nodeVar[0] == 1:
                if bbID != joinID:
                    if nodeVar[1] in phiInst:
                        op = phiInst[nodeVar[1]]
                    else:
                        op = self.GetVarVersion(nodeVar[1][1], bbID, nodeVar[1][0])[1]
                else:
                    op = self.GetVarVersion(nodeVar[1][1], bbID)[1]
        return op

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
                    values += " "*13 + f'({self.t.GetTokenStr(k)}, {k}): {v}, \n'
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

    def GenerateDot(self, tokenizer, varMode = False, debugMode = False):
        blockSect = []
        dagSect = []
        domSect = []

        color = ['blue', 'red', 'green',
                 'cyan3', 'purple', 'darkgreen',
                 'gold', 'orange', 'limegreen']

        for block in self.BBList:
            blockInfo = f"\tbb{block.bbID}[shape=record, label=\"<b>BB{block.bbID}|{{"
            lenInst = len(block.instructions)
            for i in range(lenInst):
                inst = self.instructionList[block.instructions[i]]
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
                            valueVerInfo = f'{tokenizer.GetTokenStr(k)}: {v}|'
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
                            edgeInfo += "[label=\"branch\", constraint=false]"
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
            for domID in block.dominators:
                if domID != block.bbID and domID > 0:
                    domInfo = f"\tbb{domID}:b -> bb{block.bbID}:b [color=\"{color[domID%len(color)]}\", " \
                              f"style=dashed, label=\"dom\"];"
                    domSect.append(domInfo)

        separator = "\n"
        dot = f'digraph G {{\n{separator.join(blockSect)}\n\n{separator.join(dagSect)}\n{separator.join(domSect)} \n}}'
        print(dot)
        return dot
