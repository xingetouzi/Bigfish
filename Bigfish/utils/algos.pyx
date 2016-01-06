from numpy cimport *
cimport numpy as np
import numpy as np

cimport cython

cdef double NaN = <double> np.NaN
cdef double nan = NaN

cdef inline int int_max(int a, int b): return a if a >= b else b
cdef inline int int_min(int a, int b): return a if a <= b else b

#-------------------------------------------------------------------------------
# Rolling sum
@cython.boundscheck(False)
@cython.wraparound(False)
def roll_sum(ndarray[double_t] input, int win, int minp):
    cdef double val, prev, sum_x = 0
    cdef int nobs = 0, i
    cdef int N = len(input)

    cdef ndarray[double_t] output = np.empty(N, dtype=float)

    minp = _check_minp(win, minp, N)
    with nogil:
        for i from 0 <= i < minp - 1:
            val = input[i]

            # Not NaN
            if val == val:
                nobs += 1
                sum_x += val

            output[i] = NaN

        for i from minp - 1 <= i < N:
            val = input[i]

            if val == val:
                nobs += 1
                sum_x += val

            if i > win - 1:
                prev = input[i - win]
                if prev == prev:
                    sum_x -= prev
                    nobs -= 1

            if nobs >= minp:
                output[i] = sum_x
            else:
                output[i] = NaN

    return output

#-------------------------------------------------------------------------------
# Rolling sum
def _check_minp(win, minp, N, floor=1):
    if minp > win:
        raise ValueError('min_periods (%d) must be <= window (%d)'
                        % (minp, win))
    elif minp > N:
        minp = N + 1
    elif minp < 0:
        raise ValueError('min_periods must be >= 0')
    return max(minp, floor)

def roll_generic_2d(ndarray[float64_t, ndim=2] input,
                    int win, int minp, int offset, 
                    object func, object args, object kwargs):
    cdef ndarray[double_t, ndim=2] output, bufarr
    cdef ndarray[double_t] counts
    cdef Py_ssize_t i, j, n, m
    cdef float64_t *buf
    cdef float64_t *oldbuf
    
    if not input.flags.c_contiguous:
        input = input.copy('C')
        
    n = input.shape[0]
    m = input.shape[1]
    if n == 0:
        return input
    
    minp = _check_minp(win, minp, n, floor=0)
    output = np.empty([n , m], dtype = float)
    counts = np.empty(n , dtype = float)
    for j from 0 <= j < m:
        counts = np.maximum(counts, roll_sum(np.concatenate((np.isfinite(input[:,j]).astype(float), np.array([0.] * offset))), win, minp)[offset:])
    
    # truncated windows at the beginning, through first full-length window        
    for i from 0 <= i < (int_min(win, n) - offset):
        if counts[i] >= minp:
            output[i] = func(input[0:(i + offset + 1)], *args, **kwargs)
        else:
            output[i] = NaN

    # remaining full-length windows
    buf = <float64_t*> input.data
    bufarr = np.empty([win, m], dtype=float)
    oldbuf = <float64_t*> bufarr.data
    for i from (win - offset) <= i < (n-offset):
        buf = buf + m
        bufarr.data = <char*> buf
        if counts[i] >= minp:
            output[i] = func(bufarr, *args, **kwargs)
        else:
            output[i] = NaN            
    bufarr.data = <char*> oldbuf
    
    # truncated windows at the end
    for i from int_max(n - offset, 0) <= i < n:
        if counts[i] >= minp:
            output[i] = func(input[int_max(i + offset - win + 1, 0) : n ], *args, **kwargs)
        else:
            output[i] = NaN
    
    return output