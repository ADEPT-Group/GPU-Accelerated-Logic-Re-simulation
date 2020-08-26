import numpy as np
import importlib.util
if importlib.util.find_spec('numba') is not None:
    import numba
else:
    from . import numba
    print('Numba unavailable. Falling back to pure python')


_pop_count_lut = np.asarray([bin(x).count('1') for x in range(256)])


def popcount(a):
    return np.sum(_pop_count_lut[a])


_bit_in_lut = np.array([2 ** x for x in range(7, -1, -1)], dtype='uint8')


@numba.njit
def bit_in(a, pos):
    return a[pos >> 3] & _bit_in_lut[pos & 7]


def make_count_into_lut():
    lut = np.zeros((256, 8), dtype='int')
    for i, l in enumerate(lut):
        for p in range(8):
            if i & (1 << (7-p)):
                l[p] = 1
    return lut


_count_into_lut = make_count_into_lut()


@numba.njit
def count_into(bits, counts):
    for pidx in range(len(bits)):
        p = bits[pidx]
        for i, byte in enumerate(p):
            if byte == 0: continue
            mx = min(8, len(counts)-i*8)
            if mx > 0:
                counts[i*8:(i+1)*8] += _count_into_lut[byte, :mx]


@numba.njit
def or_reduce(bits, out):
    for bidx in range(len(bits)):
        out |= bits[bidx]
    return out


@numba.njit
def sum_where_set(summands, bits):
    sm = 0
    for i, s in enumerate(summands):
        if bit_in(bits, i):
            sm += s
    return sm
