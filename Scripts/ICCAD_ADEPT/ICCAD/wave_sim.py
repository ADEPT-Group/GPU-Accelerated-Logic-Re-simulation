import numpy as np
import importlib.util
import math
if importlib.util.find_spec('numba') is not None:
    import numba
else:
    from . import numba
    print('Numba unavailable. Falling back to pure python')


TMAX = np.float32(2**127)  # almost np.PINF for 32-bit floating point values
TMIN = np.float32(-2**127)  # almost np.NINF for 32-bit floating point values


class WaveSim:
    def __init__(self, circuit, line_times, sdim=8, tdim=16):
        self.line_times = line_times.copy()
        self.circuit = circuit
        self.sdim = sdim
        self.overflows = 0

        # map line indices to self.state memory locations
        self.lmap = np.zeros(len(circuit.lines), dtype='int')
        if type(tdim) is int:
            self.lsize = len(circuit.lines) * tdim
            self.tdim = np.zeros(len(circuit.lines), dtype='int') + tdim
            for lidx in range(len(circuit.lines)):
                self.lmap[lidx] = lidx * tdim
        else:
            self.lsize = 0
            self.tdim = np.asarray(tdim, dtype='int')
            for lidx, cap in enumerate(self.tdim):
                self.lmap[lidx] = self.lsize
                self.lsize += cap
        
        # allocate self.state
        interface_tdim = 4  # sufficient for storing only 1 transition.
        self.interface = list(circuit.interface) + [n for n in circuit.nodes if 'dff' in n.kind.lower()]
        interface_dict = dict([(n, i) for i, n in enumerate(self.interface)])
        self.state = np.zeros((self.lsize + (2 + len(self.interface)) * interface_tdim, sdim), dtype='float32') + TMAX
        self.zero = self.lsize
        self.tmp = self.zero + interface_tdim
        self.inputs_offset = self.tmp + interface_tdim
        
        # store waveform capacities in self.state
        for lidx in range(len(circuit.lines)):
            self.state[self.lmap[lidx]] = self.tdim[lidx]
        self.state[self.zero] = interface_tdim
        self.state[self.tmp] = interface_tdim
        for iidx in range(len(self.interface)):
            self.state[self.inputs_offset + iidx * interface_tdim] = interface_tdim

        # map test pattern and response indices to self.state memory locations
        self.tmap = np.asarray([self.inputs_offset + interface_dict[n] * interface_tdim if len(n.o_lines) > 0 else -1
                                for n in self.interface], dtype='int')
        self.cmap = np.asarray([self.lmap[n.i_lines[0].index] if len(n.i_lines) > 0 else -1 for n in self.interface],
                               dtype='int')
        
        # generate self.ops
        ops = []
        for n in circuit.topological_order():
            if n in interface_dict:
                inp = self.inputs_offset + interface_dict[n] * interface_tdim
                if len(n.o) > 0 and n.o_lines[0] is not None:
                    ops.append((0b1010, self.lmap[n.o_lines[0].index], inp, self.zero, n.o_lines[0].index, 0, 0))
                if 'dff' in n.kind.lower():
                    if len(n.o) > 1 and n.o_lines[1] is not None:
                        ops.append((0b0101, self.lmap[n.o_lines[1].index], inp, self.zero, n.o_lines[1].index, 0, 0))
                else:
                    for o_line in n.o_lines[1:]:
                        if o_line is not None:
                            ops.append((0b1010, self.lmap[o_line.index], inp, self.zero, o_line.index, 0, 0))
            else:
                if len(n.o_lines) > 0 and n.o_lines[0] is not None:
                    o0_idx = n.o_lines[0].index
                    o0_mem = self.lmap[o0_idx]
                else:
                    print(f'no outputs for {n}')
                    o0_idx = 0
                    o0_mem = self.tmp
                if len(n.i_lines) > 0 and n.i_lines[0] is not None:
                    i0_idx = n.i_lines[0].index
                    i0_mem = self.lmap[i0_idx]
                else:
                    i0_idx = 0
                    i0_mem = self.zero
                if len(n.i_lines) > 1 and n.i_lines[1] is not None:
                    i1_idx = n.i_lines[1].index
                    i1_mem = self.lmap[i1_idx]
                else:
                    i1_idx = 0
                    i1_mem = self.zero
                kind = n.kind.lower()
                if kind == '__fork__':
                    for o_line in n.o_lines:
                        ops.append((0b1010, self.lmap[o_line.index], i0_mem, self.zero, o_line.index, i0_idx, i1_idx))
                elif kind.startswith('nand'):
                    ops.append((0b0111, o0_mem, i0_mem, i1_mem, o0_idx, i0_idx, i1_idx))
                elif kind.startswith('nor'):
                    ops.append((0b0001, o0_mem, i0_mem, i1_mem, o0_idx, i0_idx, i1_idx))
                elif kind.startswith('and'):
                    ops.append((0b1000, o0_mem, i0_mem, i1_mem, o0_idx, i0_idx, i1_idx))
                elif kind.startswith('or'):
                    ops.append((0b1110, o0_mem, i0_mem, i1_mem, o0_idx, i0_idx, i1_idx))
                elif kind.startswith('xor'):
                    ops.append((0b0110, o0_mem, i0_mem, i1_mem, o0_idx, i0_idx, i1_idx))
                elif kind.startswith('xnor'):
                    ops.append((0b1001, o0_mem, i0_mem, i1_mem, o0_idx, i0_idx, i1_idx))
                elif kind.startswith('not') or kind.startswith('inv'):
                    ops.append((0b0101, o0_mem, i0_mem, self.zero, o0_idx, i0_idx, i1_idx))
                elif kind.startswith('buf') or kind.startswith('nbuf'):
                    ops.append((0b1010, o0_mem, i0_mem, self.zero, o0_idx, i0_idx, i1_idx))
                elif kind.startswith('__const1__') or kind.startswith('tieh'):
                    ops.append((0b0101, o0_mem, self.zero, self.zero, o0_idx, i0_idx, i1_idx))
                elif kind.startswith('__const0__') or kind.startswith('tiel'):
                    ops.append((0b1010, o0_mem, self.zero, self.zero, o0_idx, i0_idx, i1_idx))
                else:
                    print('unknown gate type', kind)
        self.ops = np.asarray(ops, dtype='int32')
        
        # generate level data
        levels = np.zeros(len(self.state), dtype='int32')
        level_starts = [0]
        current_level = 1
        for i, op in enumerate(self.ops):
            if levels[op[2]] >= current_level or levels[op[3]] >= current_level:
                current_level += 1
                level_starts.append(i)
            levels[op[1]] = current_level
        self.level_starts = np.asarray(level_starts, dtype='int32')
        self.level_stops = np.asarray(level_starts[1:] + [len(self.ops)], dtype='int32')
        
        m1 = np.array([2 ** x for x in range(7, -1, -1)], dtype='uint8')
        m0 = ~m1
        self.mask = np.rollaxis(np.vstack((m0, m1)), 1)
        
    def get_line_delay(self, line, polarity):
        return self.line_times[line, 0, polarity]
    
    def set_line_delay(self, line, polarity, delay):
        self.line_times[line, 0, polarity] = delay

    def assign(self, vectors, time=0.0, offset=0):
        nvectors = min(vectors.nvectors - offset, self.sdim)
        for i, node in enumerate(self.interface):
            iidx = self.tmap[i]
            if iidx < 0: continue
            for p in range(nvectors):
                vector = p + offset
                a = vectors.bits[i, :, vector // 8]
                m = self.mask[vector % 8]
                toggle = 0
                if a[0] & m[1]:
                    self.state[iidx + 1, p] = TMIN
                    toggle += 1
                if (len(a) > 2) and (a[2] & m[1]) and ((a[0] & m[1]) == (a[1] & m[1])):
                    self.state[iidx + 1 + toggle, p] = time
                    toggle += 1
                self.state[iidx + 1 + toggle, p] = TMAX

    def propagate(self, sdim=None):
        if sdim is None:
            sdim = self.sdim
        else:
            sdim = min(sdim, self.sdim)
        for op_start, op_stop in zip(self.level_starts, self.level_stops):
            self.overflows += level_eval(self.ops, op_start, op_stop, self.state, 0, sdim,
                                         self.line_times)

    def _wave(self, mem, vector):
        if mem < 0:
            return None
        wcap = int(self.state[mem, vector])
        return self.state[mem+1:mem+wcap, vector]

    def wave(self, line, vector):
        return self._wave(self.lmap[line], vector)

    def wave_ppi(self, i, vector):
        return self._wave(self.tmap[i], vector)

    def wave_ppo(self, o, vector):
        return self._wave(self.cmap[o], vector)

    def eat(self, line, vector):
        eat = TMAX
        for t in self.wave(line, vector):
            if t >= TMAX: break
            if t <= TMIN: continue
            eat = min(eat, t)
        return eat

    def _lst(self, mem, vector):
        lst = TMIN
        for t in self._wave(mem, vector):
            if t >= TMAX: break
            if t <= TMIN: continue
            lst = max(lst, t)
        return lst

    def lst_ppo(self, o, vector):
        return self._lst(self.cmap[o], vector)

    def toggles(self, line, vector):
        tog = 0
        for t in self.wave(line, vector):
            if t >= TMAX: break
            if t <= TMIN: continue
            tog += 1
        return tog
    
    def _vals(self, mem, vector, times, sigma=0.0):
        s_sqrt2 = sigma * math.sqrt(2)
        m = 0.5
        accs = [0.0] * len(times)
        values = [0] * len(times)
        for t in self._wave(mem, vector):
            if t >= TMAX: break
            for idx, time in enumerate(times):
                if t < time:
                    values[idx] = values[idx] ^ 1
            m = -m
            if t <= TMIN: continue
            if s_sqrt2 > 0:
                for idx, time in enumerate(times):
                    accs[idx] += m * (1 + math.erf((t - time) / s_sqrt2))
        if (m < 0) and (s_sqrt2 > 0):
            for idx, time in enumerate(times):
                accs[idx] += 1
        if s_sqrt2 == 0:
            return values
        else:
            return accs
    
    def vals(self, line, vector, times, sigma=0):
        return self._vals(self.lmap[line], vector, times, sigma)

    def val(self, line, vector, time=TMAX, sigma=0):
        return self._vals(self.lmap[line], vector, [time], sigma)[0]
    
    def vals_ppo(self, o, vector, times, sigma=0):
        return self._vals(self.cmap[o], vector, times, sigma)

    def val_ppo(self, o, vector, time=TMAX, sigma=0):
        return self._vals(self.cmap[o], vector, [time], sigma)[0]
    
    def capture(self, captures, times, offset=0, sigma=0):
        nvectors = min(captures.shape[1] - offset, self.sdim)
        for i, node in enumerate(self.interface):
            if len(node.i) == 0: continue
            line = node.i_lines[0].index
            for p in range(nvectors):
                captures[i, p + offset] = self.vals(line, p, times, sigma)


@numba.njit
def level_eval(ops, op_start, op_stop, state, st_start, st_stop, line_times):
    overflows = 0
    for op_idx in range(op_start, op_stop):
        op = ops[op_idx]
        for st_idx in range(st_start, st_stop):
            overflows += wave_eval(op, state, st_idx, line_times)
    return overflows


@numba.njit
def wave_eval(op, state, st_idx, line_times):
    lut, z_mem, a_mem, b_mem, z_idx, a_idx, b_idx = op
    overflows = int(0)
    
    z_cap = int(state[z_mem, st_idx])

    a_cur = int(0)
    b_cur = int(0)
    z_cur = lut & 1
    if z_cur == 1:
        state[z_mem + 1, st_idx] = TMIN

    a = state[a_mem + 1, st_idx] + line_times[a_idx, 0, z_cur]
    b = state[b_mem + 1, st_idx] + line_times[b_idx, 0, z_cur]
    
    previous_t = TMIN

    current_t = min(a, b)
    inputs = int(0)

    while current_t < TMAX:
        z_val = z_cur & 1
        if b < a:
            b_cur += 1
            b = state[b_mem + 1 + b_cur, st_idx] 
            b += line_times[b_idx, 0, z_val ^ 1]
            thresh = line_times[b_idx, 1, z_val]
            inputs ^= 2
            next_t = b
        else:
            a_cur += 1
            a = state[a_mem + 1 + a_cur, st_idx] 
            a += line_times[a_idx, 0, z_val ^ 1]
            thresh = line_times[a_idx, 1, z_val]
            inputs ^= 1
            next_t = a

        if (z_cur & 1) != ((lut >> inputs) & 1):

            # we generate a toggle in z_mem, if:
            #   enough space in z_mem -and-
            #   ( it is the first toggle in z_mem -or-
            #   following toggle is earlier -or-
            #   pulse is wide enough ).
            if z_cur >= (z_cap - 2):
                z_cur -= 1
                overflows += 1
                if z_cur > 0:
                    previous_t = state[z_mem + 1 + z_cur - 1, st_idx]
                else:
                    previous_t = TMIN
            elif z_cur == 0 or next_t < current_t or (current_t - previous_t) > thresh:
                state[z_mem + 1 + z_cur, st_idx] = current_t
                previous_t = current_t
                z_cur += 1
            else:
                z_cur -= 1
                if z_cur > 0:
                    previous_t = state[z_mem + 1 + z_cur - 1, st_idx]
                else:
                    previous_t = TMIN
        current_t = min(a, b)

    state[z_mem + 1 + z_cur, st_idx] = TMAX
    return overflows
