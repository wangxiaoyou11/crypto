import random

class DiffieHellman(object):
	def __init__(self, g, p):
		self.private_local = None
		self.public_local = None
		self.g = g
		self.p = p
		self.k = None

	def genprivate(self, rand_func=random.getrandbits):
		keysize = len(bin(self.p))-2
		while True:
			while True:
				self.private_local = rand_func(keysize)

				if self.private_local > 0 and self.private_local < self.p:
					break

			self.public_local = pow(self.g, self.private_local, self.p)
			if self.public_local > 0:
				break

	def gensecret(self, public_remote):
		self.k = pow(remote, self.private_local, self.p)
