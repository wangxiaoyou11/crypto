from rabbit import Rabbit

b_to_int = lambda x: ((x[3] << 24) | (x[2] << 16) | (x[1] << 8) | x[0]) & 0xFFFFFFFF
b_to_int2 = lambda x: ((x[0] << 24) | (x[1] << 16) | (x[2] << 8) | x[3]) & 0xFFFFFFFF
b_to_int64 = lambda x: ((x[7] << 56) | (x[6] << 48) | (x[5] << 40) | (x[4] << 32) | (x[3] << 24) | (x[2] << 16) | (x[1] << 8) | x[0]) & 0xFFFFFFFFFFFFFFFF
b_to_int642 = lambda x: ((x[0] << 56) | (x[1] << 48) | (x[2] << 40) | (x[3] << 32) | (x[4] << 24) | (x[5] << 16) | (x[6] << 8) | x[7]) & 0xFFFFFFFFFFFFFFFF
int_to_b = lambda x: bytearray([x & 0xFF, (x >> 8) & 0xFF, (x >> 16) & 0xFF, (x >> 24) & 0xFF])
int_to_b2 = lambda x: bytearray([(x >> 24) & 0xFF, (x >> 16) & 0xFF, (x >> 8) & 0xFF, x & 0xFF])

class Badger(object):
	def __init__(self):
		self.bitcount = 0
		self.bufferindex = 0
		self.finalprng = bytearray(16);
		self.finalkey = [[] for i in xrange(6)]
		self.levelkey = [[] for i in xrange(28)]
		self.treebuffer = [[[] for i in range(4)] for i in xrange(28)]
		self.buffer = bytearray(16)

	def keysetup(self, key):
		sparefinalkeyindex = 4
		sparefinalkey = bytearray(16)
		self.finalprng = key[0:16]

		rabbit = Rabbit()
		rabbit.keysetup(key)
		finalkeydata = rabbit.prng(4*6*4)

		for i in xrange(6):
			self.finalkey[i] = []
			for j in xrange(4):
				index = i*16 + j*4
				d = b_to_int(finalkeydata[index:index+4])

				while 0xFFFFFFFA < d:
					# UNTESTED
					if sparefinalkeyindex == 4:
						print "..."
						sparefinalkey = rabbit.prng(16)
						sparefinalkeyindex = 0
					k = bytearray(4)
					k[0] = sparefinalkey[4*sparefinalkeyindex]
					k[1] = 0
					k[2] = 0
					k[3] = 0
					d = b_to_int2(k)
					sparefinalkeyindex += 1

				self.finalkey[i].append(d)

		levelkeydata = rabbit.prng(8*28*4)
		for i in xrange(28):
			self.levelkey[i] = []
			for j in xrange(4):
				index = 8*(4*i + j)
				self.levelkey[i].append(b_to_int64(levelkeydata[index:index+8]))

	def process(self, src, length, srcoffset):
		if self.bufferindex > 0:
			while length > 0 and self.bufferindex < 16:
				self.buffer[self.bufferindex] = src[srcoffset]
				self.bufferindex += 1
				srcoffset += 1
				length -= 1

		if self.bufferindex == 16:
			localbuffer0 = b_to_int64(self.buffer[0:8])
			localbuffer1 = b_to_int64(self.buffer[8:16])
			for i in xrange(4):
				self.hashnode(self.levelkey, self.treebuffer, self.bitcount >> 7, localbuffer0, localbuffer1, i, 0)

			self.bitcount += 0x80
			self.bufferindex = 0

		while length >= 16:
			localdata0 = b_to_int64(src[srcoffset:srcoffset+8])
			localdata1 = b_to_int64(src[srcoffset+8:srcoffset+16])
			for i in xrange(4):
				self.hashnode(self.levelkey, self.treebuffer, self.bitcount >> 7, localdata0, localdata1, i, 0)

			self.bitcount += 0x80
			srcoffset += 16
			length -= 16

		while length > 0:
			self.buffer[self.bufferindex] = src[srcoffset]
			self.bufferindex += 1
			srcoffset += 1
			length -= 1

	def finalize(self, iv):
		right = [[] for i in xrange(4)]
		buffermask = self.bitcount >> 7
		counter = 0
		level = 0
		rightfilled = False

		print self.bitcount
		self.bitcount += 8 * self.bufferindex
		if self.bufferindex > 0:
			if self.bufferindex <= 8:
				while self.bufferindex < 8:
					self.buffer[self.bufferindex] = 0
					self.bufferindex += 1

				for i in xrange(4):
					right[i] = b_to_int(self.buffer[0:4])
			else:
				while self.bufferindex < 16:
					self.buffer[self.bufferindex] = 0
					self.bufferindex += 1

				bufpart0 = b_to_int(self.buffer[0:4])
				bufpart1 = b_to_int(self.buffer[4:8])
				bufpart2 = b_to_int(self.buffer[8:12])

				for i in xrange(4):
					lk = self.levelkey[0][i]
					t1 = (lk + bufpart0) & 0xFFFFFFFF
					t2 = ((lk >> 32) + bufpart1) & 0xFFFFFFFF
					right[i] = (t1 * t2) + bufpart2
					print hex(right[i])

			rightfilled = True


			# print i, ":", hex(y[0]), hex(y[1]), hex(y[2]), hex(y[3])

		if buffermask == 0 and not self.bufferindex:
			for i in xrange(4):
				right[i] = 0
		else:
			while not rightfilled:
				if buffermask & 1:
					for i in xrange(4):
						right[i] = self.treebuffer[level][counter+i]
					rightfilled = True
				level += 1
				buffermask >>= 1

			while buffermask:
				if buffermask & 1:
					for i in xrange(4):
						t1 = (self.levelkey[level+1][counter] & 0xFFFFFFFF) + (self.treebuffer[level][counter] & 0xFFFFFFFF) & 0xFFFFFFFF
						t2 = (self.levelkey[level+1][counter] & 0xFFFFFFFF00000000) + (self.treebuffer[level][counter] & 0xFFFFFFFF00000000) & 0xFFFFFFFF
						right[i] += t1 * t2
						counter += 1
						if counter >= 4:
							counter -= 4
							level += 1
				else:
					level += 1
				buffermask >>= 1


		mac = bytearray(16)
		for i in xrange(4):
			t  = self.finalkey[0][i] * (right[i] & 0x07FFFFFF)
			t += self.finalkey[1][i] * ((right[i] >> 27) & 0x07FFFFFF)
			t += self.finalkey[2][i] * ((right[i] >> 54) | ((0x0001FFFF & self.bitcount) << 10))
			t += self.finalkey[3][i] * ((self.bitcount >> 17) & 0x07FFFFFF)
			t += self.finalkey[4][i] * (self.bitcount >> 44)
			t += self.finalkey[5][i]

			low = t & 0xFFFFFFFF

			r = (low + (5 * (t >> 32))) & 0xFFFFFFFF

			if r < low or r > 0xFFFFFFFA:
				r -= 0xFFFFFFFB


			p = int_to_b(r & 0xFFFFFFFF)
			mac[4*i:4*i+4] = p

		r = Rabbit()
		r.keysetup(self.finalprng)
		r.ivsetup(iv)
		return r.encrypt(mac)

	def hashnode(self, mackey, macbuffer, buffermask, left, right, counter, level):
		while True:
			t0 = mackey[level][counter]
			t1 = (t0 + left) & 0xFFFFFFFF
			t2 = ((t0 >> 32) + (left >> 32)) & 0xFFFFFFFF
			right = t1 * t2 + right
			if not buffermask & 1:
				break

			left = macbuffer[level][counter]
			level += 1
			buffermask >> 1
		macbuffer[level][counter] = right


if __name__ == '__main__':
	import pprint
	a = Badger()
	a.keysetup(bytearray([ 0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x0E, 0x0F ]))
	# d = bytearray(b"Hello my good man - How art thou?!")
		# print level, counter, right, left,
	d = bytearray([0x0,0x1,0x2,0x3,0x4,0x5,0x6,0x7,0x8,0x9,0x0,0x1,0x2,0x3,0x4,0x5,0x6,0x7,0x8,0x9,0x0,0x1,0x2,0x3,0x4,0x5,0x6,0x7,0x8,0x9,0x0,0x1,0x2,0x3,0x4,0x5,0x6,0x7,0x8,0x9])
	# d = bytearray(b"Hello my good man - How art thou?!")
	a.process(d, 17, 0)
	c = bytearray([i for i in range(8)])
	h = bytearray(8)
	c = a.finalize(c)

	pprint.pprint(c)
