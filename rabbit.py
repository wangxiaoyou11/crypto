b_to_int = lambda x: (x[3] << 24) | (x[2] << 16) | (x[1] << 8) | x[0]

def setint32(b, i, v):
	b[i] = v & 0xFF
	b[i+1] = (v >> 8) & 0xFF
	b[i+2] = (v >> 16) & 0xFF
	b[i+3] = (v >> 24) & 0xFF

class Rabbit(object):
	def __init__(self):
		self.x = [0,0,0,0,0,0,0,0]
		self.c = [0,0,0,0,0,0,0,0]
		self.carry = 0
		self.old_x = None
		self.old_c = None
		self.old_carry = None

	def gfunc(self, x):
		a = x&0xFFFF
		b = (x&0xFFFFFFFF)>>16
		h = ((((a*a)>>17) + (a*b))>>15) + b*b
		l = (a*a+((a*b)<<17)) & 0xFFFFFFFF
		return h^l

	def savestate(self):
		self.old_x = self.x[:]
		self.old_c = self.c[:]
		self.old_carry = self.carry

	def restorestate(self):
		if None not in (self.old_x, self.old_c, self.old_carry):
			self.x = self.old_x[:]
			self.c = self.old_c[:]
			self.carry = self.old_carry

	def keysetup(self, key):
		if len(key) < 16:
			raise RuntimeError("Key must be 16 bytes")

		self.x[0] = k0 = b_to_int(key[0:4])
		self.x[2] = k1 = b_to_int(key[4:8])
		self.x[4] = k2 = b_to_int(key[8:12])
		self.x[6] = k3 = b_to_int(key[12:16])
		self.x[1] = (k3<<16) | (k2>>16)
		self.x[3] = (k0<<16) | (k3>>16)
		self.x[5] = (k1<<16) | (k0>>16)
		self.x[7] = (k2<<16) | (k1>>16)

		self.c[0] = (k2<<16) | (k2>>16)
		self.c[2] = (k3<<16) | (k3>>16)
		self.c[4] = (k0<<16) | (k0>>16)
		self.c[6] = (k1<<16) | (k1>>16)
		self.c[1] = ((k0&0xFFFF0000) | (k1&0xFFFF))
		self.c[3] = ((k1&0xFFFF0000) | (k2&0xFFFF))
		self.c[5] = ((k2&0xFFFF0000) | (k3&0xFFFF))
		self.c[7] = ((k3&0xFFFF0000) | (k0&0xFFFF))

		self.carry = 0

		for i in range(4):
			self.nextstate()

		for i in range(8):
			self.c[i] ^= self.x[(i + 4) % 8]

	def ivsetup(self, iv):
		if len(iv) < 8:
			raise RuntimeError("IV must be 8 bytes")

		i0 = b_to_int(iv[0:4])
		i2 = b_to_int(iv[4:8])
		i1 = (((i0>>16) | (i2&0xFFFF0000))&0xFFFFFFFF)
		i3 = (((i2<<16) | (i0&0x0000FFFF))&0xFFFFFFFF)

		self.c[0] ^= i0
		self.c[1] ^= i1
		self.c[2] ^= i2
		self.c[3] ^= i3
		self.c[4] ^= i0
		self.c[5] ^= i1
		self.c[6] ^= i2
		self.c[7] ^= i3

		for i in range(4):
			self.nextstate()

	def nextstate(self):
		g = [0,0,0,0,0,0,0,0]

		self.c[0] = (self.c[0] + 0x4d34d34d + self.carry) & 0xFFFFFFFF;
		self.c[1] = (self.c[1] + 0xd34d34d3 + (self.c[0] < 0x4d34d34d)) & 0xFFFFFFFF;
		self.c[2] = (self.c[2] + 0x34d34d34 + (self.c[1] < 0xd34d34d3)) & 0xFFFFFFFF;
		self.c[3] = (self.c[3] + 0x4d34d34d + (self.c[2] < 0x34d34d34)) & 0xFFFFFFFF;
		self.c[4] = (self.c[4] + 0xd34d34d3 + (self.c[3] < 0x4d34d34d)) & 0xFFFFFFFF;
		self.c[5] = (self.c[5] + 0x34d34d34 + (self.c[4] < 0xd34d34d3)) & 0xFFFFFFFF;
		self.c[6] = (self.c[6] + 0x4d34d34d + (self.c[5] < 0x34d34d34)) & 0xFFFFFFFF;
		self.c[7] = (self.c[7] + 0xd34d34d3 + (self.c[6] < 0x4d34d34d)) & 0xFFFFFFFF;
		self.carry = self.c[7] < 0xd34d34d3;

		for i in range(8):
			g[i] = self.gfunc(self.x[i] + self.c[i]) & 0xFFFFFFFF

		self.x[0] = (g[0] + ((g[7] << 16) | (g[7] >> 16)) + ((g[6] << 16) | (g[6] >> 16))) & 0xFFFFFFFF;
		self.x[1] = (g[1] + ((g[0] << 8)  | (g[0] >> 24)) + g[7]) & 0xFFFFFFFF;
		self.x[2] = (g[2] + ((g[1] << 16) | (g[1] >> 16)) + ((g[0] << 16) | (g[0] >> 16))) & 0xFFFFFFFF;
		self.x[3] = (g[3] + ((g[2] << 8)  | (g[2] >> 24)) + g[1]) & 0xFFFFFFFF;
		self.x[4] = (g[4] + ((g[3] << 16) | (g[3] >> 16)) + ((g[2] << 16) | (g[2] >> 16))) & 0xFFFFFFFF;
		self.x[5] = (g[5] + ((g[4] << 8)  | (g[4] >> 24)) + g[3]) & 0xFFFFFFFF;
		self.x[6] = (g[6] + ((g[5] << 16) | (g[5] >> 16)) + ((g[4] << 16) | (g[4] >> 16))) & 0xFFFFFFFF;
		self.x[7] = (g[7] + ((g[6] << 8)  | (g[6] >> 24)) + g[5]) & 0xFFFFFFFF;

	def extract(self, dst):
		setint32(dst, 0, self.x[0] ^ (self.x[5]>>16) ^ (self.x[3]<<16))
		setint32(dst, 4, self.x[2] ^ (self.x[7]>>16) ^ (self.x[5]<<16))
		setint32(dst, 8, self.x[4] ^ (self.x[1]>>16) ^ (self.x[7]<<16))
		setint32(dst, 12, self.x[6] ^ (self.x[3]>>16) ^ (self.x[1]<<16))

	def encrypt(self, src):
		extracted = bytearray(16)
		dst = bytearray(len(src))

		i = 0
		while i < len(src):
			self.nextstate()
			self.extract(extracted)
			j = i
			while j < len(src) and j<i+16:
				dst[j] = src[j] ^ extracted[j-i]
				j+=1
			i+=16
		return dst

	def prng(self, length):
		extracted = bytearray(16)
		dst = bytearray(length)

		i = 0
		while i < length:
			self.nextstate()
			self.extract(extracted)
			j = i
			while j < length and j < i+16:
				dst[j] = extracted[j-i]
				j+=1
			i+=16
		return dst

if __name__ == '__main__':
	r = Rabbit()
	iv = bytearray([0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00])
	key = bytearray([0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00])
	inp = bytearray(b'Testing')

	r.keysetup(key)
	r.ivsetup(iv)
	r.savestate()

	a = r.encrypt(inp)
	r.restorestate()
	b = r.encrypt(a)
	print b
