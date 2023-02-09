from __future__ import annotations
from cfg import *


class SSA:
    """
    Maintains control flow graphs, basic blocks, value tables
    """
    def __init__(self):
        self.instructionCount = 0 # always incrementing
        self.instructionList = []

        self.basicBlockCount = 1 # always incrementing
        self.BasicBlocksRoot = BasicBlock(0)
        block1 = BasicBlock(self.GetNextBBID())
        self.BasicBlocksRoot.AddChild(block1)
        block1.AddParent(self.BasicBlocksRoot)

        self.CurrentBasicBlock = block1

    def GetNextBBID(self):
        # Gets the next BBID and increments BBID count
        ID = self.basicBlockCount
        self.basicBlockCount += 1
        return ID

    def DefineIR(self, operation, operand1=None, operand2=None, bb_id=0):
        """
        Called by parser to generate an IR code
        :param operation: the operation {add, sub, mul, div, cmp, phi, and others}
        :param operand1: first operand, may be omitted (in case of read and end)
        :param operand2: second operand, may be omitted
        :return: an instruction node (either one seen previously or a newly generated one)
        """
        instruction = InstructionNode(operation, operand1, operand2, self.instructionCount, bb_id)

    def AssignVariable(self, varToken, instructionNode):
        """
        Updates the value table in the current basic block
        If the variable has been assigned before, create a new version (maintains SSA)
        :param varToken: the variable token to be updated
        :param instructionNode: the instruction assigned to the variable
        :return:
        """

        pass

    def GetVarInstNode(self):
        pass

    def CreateNewBasicBlock(self):
        pass

    def GetCurrBasicBlock(self):
        pass
