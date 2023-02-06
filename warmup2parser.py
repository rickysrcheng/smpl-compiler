import tokenizer
from tokens import Tokens

class Parser:
	def __init__(self, filepath, debug=False, tokenDebug=False):
		self.t = tokenizer.Tokenizer(filepath, tokenDebug)
		self.sym = None
		self.debug = debug

		self.identTable = {}
		self.level = 0
		self.spacing = 2
		self.maxGlobalId = max([t.value for t in Tokens])

	def next(self):
		self.sym = self.t.GetNext()

	def close(self):
		self.t.close()

	def CheckFor(self, token):
		if self.sym == token:
			self.next()
		else:
			raise SyntaxError(f'Expected {token}, got {self.sym}')

	def computation(self):
		# warmup 2:
		# computation = “computation” 
		#				{“var” identifier “<-” expression “;”} 
		#				expression { “;” expression } “.”
		self.next()
		self.CheckFor(Tokens.mainToken)
		if self.debug:
			print(f'{" "*self.level*self.spacing}In C{self.level}')

		while self.sym == Tokens.varToken:
			self.next()
			ident = self.sym
			if ident < 256:
				self.t.close()
				raise SyntaxError('Keyword used as variable name')
			elif ident in self.identTable:
				self.t.close()
				raise SyntaxError('Variable instance exists already')

			self.next()
			self.CheckFor(Tokens.becomesToken)

			result = self.expression()
			self.identTable[ident] = result

			self.CheckFor(Tokens.semiToken)



		while True:
			print(self.expression())
			if self.sym == Tokens.periodToken:
				break
			self.CheckFor(Tokens.semiToken)
		if self.debug:
			print(f'{" "*self.level*self.spacing}Exit C{self.level}')

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
		elif self.sym > self.maxGlobalId:
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
	comp = Parser("./example.txt")
	comp.computation()
	comp.close()
