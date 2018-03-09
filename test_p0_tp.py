import numpy as np


def init_p0_tp(hmm_type):
  _num_states = 4
  tp = np.ones([_num_states, _num_states], dtype=np.float64) / _num_states
  p0 = np.ones([1, _num_states], dtype=np.float64) / _num_states
  if hmm_type == 'left-to-right' or hmm_type == 'left-to-right-to-first':
    p0[0, 0] = 1.0
    for i in range(1, _num_states):
      p0[0, i] = 0.0
      for j in range(i):
        tp[i, j] = 0.0
      for j in range(i, _num_states):
        tp[i, j] = 1.0 / (_num_states - i)
  if hmm_type == 'left-to-right-to-first':
    tp[-1, 0] = 0.5
    tp[-1, -1] = 0.5
    p0 = np.ones([1, _num_states], dtype=np.float64) / _num_states
  return p0, tp


p0, tp = init_p0_tp('left-to-right')
print(p0)
print(tp)
