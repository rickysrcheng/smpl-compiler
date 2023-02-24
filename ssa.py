from __future__ import annotations
from cfg import *
from tokens import *


class SSA:
    """
    Maintains control flow graphs, basic blocks, value tables
    """
    def __init__(self, debug=False):
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

    def GetNextBBID(self):
        # Gets the next BBID and increments BBID count
        ID = self.basicBlockCount
        self.basicBlockCount += 1
        return ID

    def GetNextInstID(self):
        ID = self.instructionCount
        self.instructionCount += 1
        return ID

    def DefineIR(self, operation, bb_id, operand1=None, operand2=None, inst_position=-1):
        """
        Called by parser to generate an IR code
        :param operation: the operation {add, sub, mul, div, cmp, phi, and others}
        :param operand1: first operand, may be omitted (in case of read and end)
        :param operand2: second operand, may be omitted
        :param inst_position: position of the instruction to be inserted in the basic block (for while loop)
        :return: an instruction node (either one seen previously or a newly generated one)
        """

        instID = self.FindPreviousInst(operation, operand1, operand2, bb_id)
        # if no instructions are found, create a new instruction
        if instID == -1:
            instID = self.GetNextInstID()
            if operation == IRTokens.constToken:
                instruction = InstructionNode(operation, operand1, operand2, instID, 0)
                print(f'Instruction made: ({instID}, {0}): {self.opDct[operation]} {operand1} {operand2}')
                self.instructionList.append(instruction)
                self.BBList[0].instructions.append(instID)
                self.BBList[0].opTables[operation].insert(0, (instID, operand1))
            else:
                instruction = InstructionNode(operation, operand1, operand2, instID, bb_id)
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

    def AssignVariable(self, varToken, instID, bb_id):
        """
        Updates the value table in the current basic block
        If the variable has been assigned before, create a new version (maintains SSA)
        :param varToken: the variable token to be updated
        :param instID: the instruction assigned to the variable
        :param bb_id: the basic block ID
        :return: void
        """
        (n, inst) = self.GetVarVersion(varToken, bb_id)
        if bb_id != 0:
            if n != -1 and inst != instID:
                if varToken in self.BBList[bb_id].valueTable:
                    self.BBList[bb_id].valueTable[varToken].insert(0, (n + 1, instID))
                else:
                    self.BBList[bb_id].valueTable[varToken] = [(n + 1, instID)]
            elif n == -1:
                self.BBList[bb_id].valueTable[varToken] = [(0, instID)]
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

    def GetVarVersion(self, varToken, bb_id: int = -1):
        """
        Finds the current SSA version of the program variable
        If variable does not exist in record, return 0.
        :param varToken: variable token
        :param bb_id:
        :return:
        """
        blockID = self.CurrentBasicBlock
        if bb_id != -1:
            blockID = bb_id
        dom_list = self.BBList[blockID].dominators
        for dom_block in dom_list:
            if varToken in self.BBList[dom_block].valueTable:
                # return first entry
                #print(self.BBList[dom_block].valueTable[varToken][0])
                return self.BBList[dom_block].valueTable[varToken][0]
        return -1, -1

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

        # for k, v in thenValTable.items():
        #     prevSSA = self.GetVarInstNode(k, self.BBList[thenID].dominators[1])
        #     print(k, v, prevSSA)
        #     phiInsts[k] = (v[0][1], prevSSA)

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
            print(var, entrySSA, doSSA)
            # if then path modifies a variable
            if entrySSA != doSSA:
                phiInsts[var] = (doSSA[1], entrySSA[1])

        # for k, v in thenValTable.items():
        #     prevSSA = self.GetVarInstNode(k, self.BBList[thenID].dominators[1])
        #     print(k, v, prevSSA)
        #     phiInsts[k] = (v[0][1], prevSSA)

        print(phiInsts, joinID, latestDoID)
        for k, v in phiInsts.items():
            print(v)
            instID = self.DefineIR(IRTokens.phiToken, joinID, v[0], v[1], 0)
            self.AssignVariable(k, instID, joinID)

        # then need to update CMP and other operands in the doblock
        print('EXITING PHI')

    def GetCurrBasicBlock(self):
        return self.CurrentBasicBlock

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
            print(f'({instID}, {inst.BB}): {self.opDct[op]} {op1} {op2}')

    def PrintBlocks(self, tokenizer):
        for block in self.BBList:
            print(block.bbID)
            print(f'    Dominators: {block.dominators}')
            print(f'    Parents: {block.parents}')
            print(f'    Children: {block.children}')
            print(f'    Instructions: {block.instructions}')

            values = ''
            for k, v in block.valueTable.items():
                values += f'({tokenizer.GetTokenStr(k)}, {k}): {v}, '
            values = '{' + values[:-2] + '}'
            print(f'    Values: {values}')

    def GenerateDot(self, tokenizer):
        blockSect = []
        dagSect = []
        domSect = []

        color = ['blue', 'red', 'green',
                 'cyan3', 'purple', 'darkgreen',
                 'gold', 'orange', 'limegreen']
        varMode = True
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

                instInfo = f"{inst.instID}: {self.opDct[inst.instruction]}{op1}{op2}"
                if i < len(block.instructions) - 1:
                    instInfo += "|"
                blockInfo += instInfo
            if varMode and len(block.valueTable) != 0:
                blockInfo += "}|{"
                for k in block.valueTable:
                    valueInfo = ''
                    for v in block.valueTable[k]:
                        valueVerInfo = f'{tokenizer.GetTokenStr(k)}: {v}|'
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
