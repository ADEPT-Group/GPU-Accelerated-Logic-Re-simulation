import numpy as np
import math
from .wave_sim import WaveSim
from numba import cuda

TMAX = np.float32(2 ** 127)  # almost np.PINF for 32-bit floating point values
TMIN = np.float32(-2 ** 127)  # almost np.NINF for 32-bit floating point values


class WaveSimCuda(WaveSim):
    def __init__(self, circuit, line_times, sdim=8, tdim=16):
        super().__init__(circuit, line_times, sdim, tdim)

        self.tdata = np.zeros((len(self.interface), 3, (sdim - 1) // 8 + 1), dtype='uint8')
        self.cdata = np.zeros((len(self.interface), sdim), dtype='float32')

        self.d_state = cuda.to_device(self.state)
        self.d_ops = cuda.to_device(self.ops)
        self.d_line_times = cuda.to_device(self.line_times)
        self.d_tdata = cuda.to_device(self.tdata)
        self.d_tmap = cuda.to_device(self.tmap)
        self.d_cdata = cuda.to_device(self.cdata)
        self.d_cmap = cuda.to_device(self.cmap)

        self._block_dim = (32, 16)

    def get_line_delay(self, line, polarity):
        return self.d_line_times[line, 0, polarity]

    def set_line_delay(self, line, polarity, delay):
        self.d_line_times[line, 0, polarity] = delay

    def assign(self, vectors, time=0.0, offset=0):
        assert (offset % 8) == 0
        byte_offset = offset // 8
        assert byte_offset < vectors.bits.shape[-1]
        pdim = min(vectors.bits.shape[-1] - byte_offset, self.tdata.shape[-1])

        self.tdata[..., 0:pdim] = vectors.bits[..., byte_offset:pdim + byte_offset]
        if vectors.vdim == 1:
            self.tdata[:, 1, 0:pdim] = ~self.tdata[:, 1, 0:pdim]
            self.tdata[:, 2, 0:pdim] = 0
        cuda.to_device(self.tdata, to=self.d_tdata)

        grid_dim = self._grid_dim(self.sdim, len(self.d_tmap))
        assign_kernel[grid_dim, self._block_dim](self.d_state, self.d_tmap, self.d_tdata, time)

    def _grid_dim(self, x, y):
        gx = math.ceil(x / self._block_dim[0])
        gy = math.ceil(y / self._block_dim[1])
        return gx, gy

    def propagate(self, sdim=None):
        if sdim is None:
            sdim = self.sdim
        else:
            sdim = min(sdim, self.sdim)
        for op_start, op_stop in zip(self.level_starts, self.level_stops):
            grid_dim = self._grid_dim(sdim, op_stop - op_start)
            wave_kernel[grid_dim, self._block_dim](self.d_ops, op_start, op_stop, self.d_state, int(0),
                                                   sdim, self.d_line_times)
        cuda.synchronize()

    def _wave(self, mem, vector):
        if mem < 0:
            return None
        wcap = int(self.d_state[mem, vector])
        return self.d_state[mem + 1:mem + wcap, vector]

    def capture(self, captures, times, offset=0, sigma=0):
        assert offset < captures.shape[1]
        for tidx, time in enumerate(times):
            grid_dim = self._grid_dim(self.sdim, len(self.interface))
            capture_kernel[grid_dim, self._block_dim](self.d_state, self.d_cmap,
                                                      self.d_cdata, time, sigma * math.sqrt(2))
            cap_dim = min(captures.shape[1] - offset, self.sdim)
            captures[:, offset:cap_dim + offset, tidx] = self.d_cdata[:, 0:cap_dim]
        cuda.synchronize()


@cuda.jit
def capture_kernel(state, cmap, cdata, time, s_sqrt2):
    x, y = cuda.grid(2)
    if y >= len(cmap): return
    line = cmap[y]
    if line < 0: return
    if x >= state.shape[-1]: return
    vector = x
    tdim = int(state[line, vector])
    m = 0.5
    acc = 0.0
    eat = TMAX
    lst = TMIN
    tog = 0
    val = int(0)
    for tidx in range(tdim - 1):
        t = state[line + 1 + tidx, vector]
        if t >= TMAX: break
        m = -m
        if t < time:
            val ^= 1
        if t <= TMIN: continue
        if s_sqrt2 > 0:
            acc += m * (1 + math.erf((t - time) / s_sqrt2))
        eat = min(eat, t)
        lst = max(lst, t)
        tog += 1
    if s_sqrt2 > 0:
        if m < 0:
            acc += 1
        cdata[y, vector] = acc
    else:
        cdata[y, vector] = val


@cuda.jit
def assign_kernel(state, tmap, tdata, time):
    x, y = cuda.grid(2)
    if y >= len(tmap): return
    line = tmap[y]
    if line < 0: return
    sdim = state.shape[-1]
    if x >= sdim: return
    vector = x
    a0 = tdata[y, 0, vector // 8]
    a1 = tdata[y, 1, vector // 8]
    a2 = tdata[y, 2, vector // 8]
    m = np.uint8(1 << (7 - (vector % 8)))
    toggle = 0
    if a0 & m:
        state[line + 1 + toggle, x] = TMIN
        toggle += 1
    if (a2 & m) and ((a0 & m) == (a1 & m)):
        state[line + 1 + toggle, x] = time
        toggle += 1
    state[line + 1 + toggle, x] = TMAX


@cuda.jit
def wave_kernel(ops, op_start, op_stop, state, st_start, st_stop, line_times):
    x, y = cuda.grid(2)
    st_idx = st_start + x
    op_idx = op_start + y
    if st_idx >= st_stop: return
    if op_idx >= op_stop: return
    lut = ops[op_idx, 0]
    z_mem = ops[op_idx, 1]
    a_mem = ops[op_idx, 2]
    b_mem = ops[op_idx, 3]
    z_idx = ops[op_idx, 4]
    a_idx = ops[op_idx, 5]
    b_idx = ops[op_idx, 6]

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
                # overflows += 1
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
