from tokens import *


class InstructionNode:
    def __init__(self, instruction: str = None, operand1: int = None, operand2: int = None,
                 inst_id: int = None, bb_id: int = None):
        """
        Initializes an instruction node. Most private variables should not be changed after initializing.
        :param instruction:
        :param operand1:
        :param operand2:
        :param inst_id:
        :param bb_id:
        """
        self.instruction = instruction
        self.operand1 = operand1
        self.operand2 = operand2
        self.instID = inst_id
        self.BB = bb_id

    def setOperands(self, operand1: int = None, operand2: int = None):
        """
        Used mainly for branch instructions, since the jump distance is unknown when first generated
        :param operand1:
        :param operand2:
        :return: nothing
        """
        if operand1:
            self.operand1 = operand1
        if operand2:
            self.operand2 = operand2

    def PrintInstruction(self):
        print(f'{self.instID} {self.instruction} {self.operand1} {self.operand2} {self.BB}')


class BasicBlock:
    def __init__(self, bbID: int, valueTable: dict = None, parents: list = None, dominators: list = None, type = None):

        # tables needed for SSA tracking
        if valueTable is None:
            self.valueTable = {}
        else:
            self.valueTable = valueTable

        # optable
        # entry format (instID, op1, op2)
        #     both op1 and op2 can be None
        # entries are reverse chronologically ordered
        self.opTables = {token: [] for token in IRTokens}
        # self.opTables = {IRTokens.constToken: [],
        #                  IRTokens.addToken: [], IRTokens.subToken: [], IRTokens.mulToken: [],
        #                  IRTokens.divToken: [], IRTokens.cmpToken: [], IRTokens.phiToken: []}


        # for control flow graph
        self.children = set()
        if parents is None:
            self.parents = []
        else:
            self.parents = parents

        # by definition, a basic block dominates itself
        self.dominators = [bbID]
        if dominators is not None:
            self.dominators += dominators

        self.bbID = bbID

        # bookkeeping
        self.type = type
        self.instructions = []

    def AddChild(self, blockID):
        self.children.add(blockID)

    def AddParent(self, blockID):
        if blockID not in self.parents:
            self.parents.append(blockID)

    def AddDominator(self, block):
        self.dominators.append(block)

    def AddNewOp(self, op, operand1, operand2, instID):
        self.opTables[op].insert(0, (instID, operand1, operand2))
