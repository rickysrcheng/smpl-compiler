import tokenizer
from tokens import Tokens

class Parser:
	def __init__(self, filepath: str, debug=False, tokenDebug=False):
		self.t = tokenizer.Tokenizer(filepath, tokenDebug)
		self.sym = None
		self.debug = debug

		self.identTable = {}
		self.level = 0
		self.spacing = 2
		self.ssaTable = {}
		self.relOp = [Tokens.eqlToken, Tokens.neqToken, 
					  Tokens.geqToken, Tokens.leqToken, 
					  Tokens.gtrToken, Tokens.lssToken]

	def next(self):
		self.sym = self.t.GetNext()

	def close(self):
		self.t.close()

	def CheckFor(self, token: EnumType)-> void:
		if self.sym == token:
			self.next()
		else:
			raise SyntaxError(f'Expected {token}, got {self.sym}')

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
		# warmup 2:
		# computation = “computation” 
		#				{“var” identifier “<-” expression “;”} 
		#				expression { “;” expression } “.”
		# 
		# computation = "main" { varDecl } { funcDecl } "{"" statSequence "}" ".".
		self.next()
		self.CheckFor(Tokens.mainToken)
		if self.debug:
			print(f'{" "*self.level*self.spacing}In C{self.level}')

		if self.sym == Tokens.varToken:

		if self.debug:
			print(f'{" "*self.level*self.spacing}Exit C{self.level}')

	def relation(self):
		self.level += 1
		if self.debug:
			print(f'{" "*self.level*self.spacing}In E{self.level}')

		ex1 = self.expression()
		self.next()
		if self.sym not in self.relOp:
			self.t.close()
			raise SyntaxError(f'Expected relOp, got {self.sym}')
		# TODO
		relOp = self.sym
		ex2 self.expression()
		if relOp == Tokens.eqlToken:
			continue
		elif relOp == Tokens.neqToken:
			continue
		elif relOp == Tokens.lssToken:
			continue
		elif relOp == Tokens.leqToken:
			continue
		elif relOp == Tokens.gtrToken:
			continue
		elif relOp == Tokens.geqToken:
			continue


	def expression(self):
		# expression = term {(“+” | “-”) term}
		self.level += 1
		if self.debug:
			print(f'{" "*self.level*self.spacing}In E{self.level}')
		result = self.term()
		if self.debug:
			print(f'{" "*self.level*self.spacing}E{self.level}: Term 1: {result}')
		while self.sym == Tokens.plusToken or self.sym == Tokens.minusToken:
			if self.sym == Tokens.plusToken:
				self.next()
				result += self.term()
			elif self.sym == Tokens.minusToken:
				self.next()
				result -= self.term()

			if self.debug:
				print(f'{" "*self.level*self.spacing}E{self.level}: Current expression: {result}')
		if self.debug:
			print(f'{" "*self.level*self.spacing}Exit E{self.level}: {result}')
		self.level -= 1
		return result

	def term(self):
		# term = factor { (“*” | “/”) factor}
		self.level += 1
		if self.debug:
			print(f'{" "*self.level*self.spacing}In T{self.level}')
		result = self.factor()
		if self.debug:
			print(f'{" "*self.level*self.spacing}T{self.level}: Factor 1: {result}')
		while self.sym == Tokens.timesToken or self.sym == Tokens.divToken:
			if self.sym == Tokens.timesToken:
				self.next()
				result *= self.factor()
			elif self.sym == Tokens.divToken:
				self.next()
				result /= self.factor()
			if self.debug:
				print(f'{" "*self.level*self.spacing}T{self.level}: Current term: {result}')
		if self.debug:
			print(f'{" "*self.level*self.spacing}Exit T{self.level}: {result}')
		self.level -= 1
		return result

	def factor(self):
		# factor = designator | number | “(“ expression “)” | funcCall
		# designator = ident{ "[" expression "]" }
		self.level += 1
		if self.debug:
			print(f'{" "*self.level*self.spacing}In F{self.level}')

		if self.sym == Tokens.number:
			result = self.t.lastNum
			self.next()
		elif type(self.sym) == int:
			result = self.identTable[self.sym]
			self.next()
		elif self.sym == Tokens.openparenToken:
			self.next()
			result = self.expression()
			self.CheckFor(Tokens.closeparenToken)

		if self.debug:
			print(f'{" "*self.level*self.spacing}Exit F{self.level}: {result}')
		self.level -= 1
		return result

if __name__ == '__main__':
	comp = Parser("./example.txt", True)
	comp.computation()
	comp.close()