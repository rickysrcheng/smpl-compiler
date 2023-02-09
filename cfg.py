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

    def setOperands(self, operand1 : int = None, operand2 : int = None):
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

class BasicBlock:
    def __init__(self, bbID: int, valueTable : dict = None):

        # tables needed for SSA tracking
        self.valueTable = valueTable
        self.opTables = {"add": [], "sub": [], "mul": [], "div": [], "cmp": [], "phi": []}

        # for control flow graph
        self.children = []
        self.parents = []

        #
        self.bbID = bbID

        # bookkeeping
        self.instructions = []

    def AddChild(self, block):
        self.children.append(block)

    def AddParent(self, block):
        self.parents.append(block)