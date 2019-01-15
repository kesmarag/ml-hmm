import os
import shutil
import tempfile
import time
import numpy as np
import tensorflow as tf
from kesmarag.ml.utils import DataSet
from sklearn.cluster import KMeans
from tensorflow.contrib.distributions import MultivariateNormalFullCovariance

# disable the tensorflow's warnings
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'


class HMM(object):
  """A Hidden Markov Model class on top of the Tensorflow library.
     At the moment, the class supports only Gaussian emission distributions.
     The class will also support discrete multivariate and Gaussian Mixture Models
     as emission distributions. 
     The class is licensed under the MIT License.
  """

  def __init__(self, num_states, data_dim, hmm_type='fully-connected'):
    """Init method of the HMM class.
    Args:
      num_states: Number of the hidden states.
      data_dim: Dimensionality of the observed data.
      hmm_type: Type of HMM (fully-connected, left-to-right, cyclic).
    """
    self._dir = tempfile.mkdtemp()
    self._epoch = 0
    self._graph = tf.Graph()
    self._num_states = num_states
    self._data_dim = data_dim
    self._hmm_type = hmm_type
    self._em_probs = self._emission_probs_family()
    # numpy variables
    self._p0, self._tp = self._init_p0_tp()
    self._mu = np.random.rand(self._num_states, self._data_dim)
    self._sigma = np.array(
      [np.identity(self._data_dim, dtype=np.float64)] * self._num_states)
    # creation of the computation graph
    self._create_the_computational_graph()

  def __del__(self):
    # delete the tmp directory
    shutil.rmtree(self._dir)

  def __str__(self):
    frame_len = 35
    s = '-' * frame_len
    s += '\n' + '-' * frame_len + '\n'
    s += ' - kesmarag.ml.hmm.HMM'
    s += '\n' + '-' * frame_len + '\n'
    s += ' - number of states: ' + str(self._num_states) + '\n'
    s += ' - observation length: ' + str(self._data_dim) + '\n'
    s += ' - training epoch: ' + str(self._epoch)
    if self._epoch > 0:
      s += '\n' + '-' * frame_len + '\n'
      s += ' - initial probabilities'
      s += '\n' + '-' * frame_len + '\n'
      s += str(self._p0)
      s += '\n' + '-' * frame_len + '\n'
      s += ' - transition probabilities'
      s += '\n' + '-' * frame_len + '\n'
      s += str(self._tp)
      s += '\n' + '-' * frame_len + '\n'
      s += ' - mean values'
      s += '\n' + '-' * frame_len + '\n'
      s += str(self._mu)
      s += '\n' + '-' * frame_len + '\n'
      s += ' - covariances'
      s += '\n' + '-' * frame_len + '\n'
      s += str(self._sigma)
      s += '\n' + '-' * frame_len
    s += '\n' + '-' * frame_len + '\n'
    return s

  def posterior(self, data):
    """Runs the forward-backward algorithm in order to calculate
       the log-scale posterior probabilities.

    Args:
      data: A numpy array with rank two or three.

    Returns:
      A numpy array that contains the log-scale posterior probabilities of
      each time serie in data.

    """
    dataset = DataSet(data, shuffle=False)
    with tf.Session(graph=self._graph) as sess:
      sess.run(tf.global_variables_initializer())
      feed_dict = {
        self._dataset_tf: dataset.data, self._p0_tf: self._p0,
        self._tp_tf: self._tp, self._mu_tf: self._mu,
        self._sigma_tf: self._sigma}
      return np.squeeze(sess.run(self._posterior, feed_dict=feed_dict))

  def fit(self, data, max_steps=100, batch_size=None, TOL=0.01, min_var=0.1,
          num_runs=1):
    """Implements the Baum-Welch fitting algorithm.

    Args:
      data: A numpy array with rank two or three.             
      max_steps: Maximum number of steps.
      batch_size: None or the number of batch size.
      TOL: The tolerance for stoping the training process.
      min_var: Minimum variance
      num_runs: Number of training realizations. 
      The best of all model is to be kept.

    Returns:
      True if converged, False otherwise.

    """
    post_max = -1000000000
    tic = time.time()
    dataset = DataSet(data)
    KMEANS_NUM = 100
    kmeans_batch = np.concatenate(dataset.get_batch(
          min(KMEANS_NUM, dataset.num_examples)), axis=0)
    if self._hmm_type == 'left-to-right':
      N = kmeans_batch.shape[-2] // (self._num_states + 1)
      centers = []
      sigmas = []
      for k in range(self._num_states):
        centers.append(np.mean(kmeans_batch[range(k * N, (k + 1) * N)], axis=-2))
        sigmas.append(np.mean(kmeans_batch[range(k * N, (k + 1) * N)]**2, axis=-2) - centers[k]**2)
      # print(sigmas)
      self._sigma = np.array(
        [np.identity(self._data_dim, dtype=np.float64)] * self._num_states)
      for i in range(self._num_states):
        self._sigma[i] = np.diag(sigmas[i] * (1.0 + 0.3 * np.abs(np.random.randn(len(sigmas[i]),))) )
    else:
      kmeans = KMeans(n_clusters=self._num_states)
    for r in range(num_runs):
      converged = False
      if self._hmm_type == 'left-to-right':
        for i in range(self._num_states):
          centers[i] = np.multiply(centers[i], 1.0 + 0.05 * (np.random.randn(self._data_dim,)))
        self._mu = np.array(centers)
      else:
        kmeans = KMeans(
          n_clusters=self._num_states, random_state=r).fit(kmeans_batch)
        self._mu = kmeans.cluster_centers_
      self._p0, self._tp = self._init_p0_tp()
      if self._hmm_type != 'left-to-right':
        self._sigma = np.array(
          [np.identity(self._data_dim, dtype=np.float64)] * self._num_states)
      with tf.Session(graph=self._graph) as sess:
        sess.run(tf.global_variables_initializer())
        for step in range(max_steps):
          if batch_size is None:
            feed_dict = {
              self._dataset_tf: dataset.data, self._p0_tf: self._p0,
              self._tp_tf: self._tp, self._mu_tf: self._mu,
              self._sigma_tf: self._sigma, self._min_var_tf: min_var}
          else:
            batch = dataset.get_batch(batch_size)
            feed_dict = {
              self._dataset_tf: batch, self._p0_tf: self._p0,
              self._tp_tf: self._tp, self._mu_tf: self._mu,
              self._sigma_tf: self._sigma, self._min_var_tf: min_var}
          if step == 0:
            p0_prev = np.zeros((self._num_states,))
            tp_prev = np.zeros((self._num_states, self._num_states))
            mu_prev = np.zeros((self._num_states, self._data_dim,))
            sigma_prev = np.zeros((
              self._num_states, self._data_dim, self._data_dim))
          else:
            p0_prev = self._p0
            tp_prev = self._tp
            mu_prev = self._mu
            sigma_prev = self._sigma
          self._p0, self._tp, self._mu, self._sigma = sess.run(
            [self._p0_tf_new, self._tp_tf_new,
             self._mu_tf_new, self._sigma_tf_new],
            feed_dict=feed_dict)
          # check if the sigma is positive definite
          for k in range(self._num_states):
            j = 0
            while not self._is_pos_def(self._sigma[k]):
              j += 1
              # print('.. not positive definite ..')
              self._sigma[k] = self._sigma[k] + 0.05 * np.array(
                [np.identity(self._data_dim, dtype=np.float64)])*self._sigma[k]
          post = np.mean(
            np.squeeze(sess.run(
              self._posterior, feed_dict={
                self._dataset_tf: dataset.data, self._p0_tf: self._p0,
                self._tp_tf: self._tp, self._mu_tf: self._mu,
                self._sigma_tf: self._sigma})))
          if post > post_max:
            p0_max = self._p0
            tp_max = self._tp
            mu_max = self._mu
            sigma_max = self._sigma
          ch_p0 = np.max(np.abs(self._p0 - p0_prev))
          ch_tp = np.max(np.abs(self._tp - tp_prev))
          ch_mu = np.max(np.abs(self._mu - mu_prev))
          ch_sigma = np.max(np.abs(self._sigma - sigma_prev))
          # print('step = ', step, ' ', post)
          if ch_p0 < TOL and ch_tp < TOL and ch_mu < TOL and ch_sigma < TOL:
            converged = True
            break
        # print('steps = ', step, ' ', post)
    self._p0 = p0_max
    self._tp = tp_max
    self._mu = mu_max
    self._sigma = sigma_max
    self._epoch += 1
    toc = time.time()
    # print('training time : ', toc-tic, ' seconds.')
    return converged

  def run_viterbi(self, data):
    """Implements the viterbi decoding algorithm.

    Args:
      data: A numpy array of rank two or three represents the observed data.

    Returns:
      A numpy array contains he most probable hidden state paths.
    """
    dataset = DataSet(data)
    tic = time.time()
    with tf.Session(graph=self._graph) as sess:
      sess.run(tf.global_variables_initializer())
      feed_dict = feed_dict = {
        self._dataset_tf: dataset.data, self._p0_tf: self._p0,
        self._tp_tf: self._tp, self._mu_tf: self._mu,
        self._sigma_tf: self._sigma}
      toc = time.time()
      # print('inference time : ', toc-tic, ' seconds.')
      w, am = sess.run([self._w, self._am], feed_dict=feed_dict)
      w = (w[:, -1, :])
      argmax_w = np.argmax(w, axis=1)
      psi = np.concatenate((am[range(len(w)), 1::, argmax_w], np.expand_dims(argmax_w, 1)), -1)
      dec = []
      for i, p in enumerate(am):
        dec_p = [argmax_w[i]]
        c = p[::-1, :]
        l = argmax_w[i]
        for j in range(len(c) - 1):
          # print(c[j][l])
          dec_p.insert(0, c[j][l])
          l = c[j][l]
        dec_p.insert(0, l)
        dec.append(dec_p)
      return np.squeeze(np.array(dec, dtype='int16'))

  def generate(self, num_samples):
    """Generate simulated data from the model.

    Args:
      num_samples: The number of samples of the generated data.

    Returns:
      The numpy array of the generated sequence of observations.
    """
    with tf.Session(graph=self._graph) as sess:
      sess.run(tf.global_variables_initializer())
      feed_dict = {
        self._p0_tf: self._p0,
        self._tp_tf: self._tp, self._mu_tf: self._mu,
        self._sigma_tf: self._sigma, self._num_samples_tf: num_samples}
      states, samples = sess.run(
        [self._states, self._samples], feed_dict=feed_dict)
      return samples, states
  
  def save_model(self, filename):
    """Saves the model parameters to a numpy file
    
    Args:
      filename: The path to a numppy .npz file where the model parameters will be saved.
    """
    if self._epoch > 0:
      np.savez(filename, p0 = self._p0, tp = self._tp, mu = self._mu, sigma = self._sigma)
    else:
      print('Nothing to do. The model must have been trained first in order to run this method')

  def load_model(self, filename):
    """Loads the model parameters from a numpy file
    
    Args:
      filename: The path to a numpy .npz file where the model parameters have been stored.
    """
    if self._epoch == 0:
      z = np.load(filename)
      self._p0 = z['p0']
      self._tp = z['tp']
      self._mu = z['mu']
      self._sigma = z['sigma']
      self._epoch = 1
    else:
      print('ERROR: The model parameters did not load properly')

  @property
  def p0(self):
    return np.squeeze(self._p0)

  @property
  def tp(self):
    return self._tp

  @property
  def mu(self):
    return self._mu

  @property
  def sigma(self):
    return self._sigma

  def _create_the_computational_graph(self):
    with self._graph.as_default():
      self._dataset_tf = tf.placeholder(
        'float64', shape=[None, None, self._data_dim])
      self._num_samples_tf = tf.placeholder('int32')
      self._min_var_tf = tf.placeholder('float64')
      self._p0_tf = tf.placeholder(tf.float64, shape=[1, self._num_states])
      self._tp_tf = tf.placeholder(
        tf.float64, shape=[self._num_states, self._num_states])
      self._emissions_eval()
      self._forward()
      self._backward()
      self._expectation()
      self._maximization()
      self._simulate()
      self._viterbi()
      self._saver = tf.train.Saver()

  def _emission_probs_family(self):
    with self._graph.as_default():
      self._mu_tf = tf.placeholder(
          tf.float64, shape=[self._num_states, self._data_dim])
      self._sigma_tf = tf.placeholder(
          tf.float64, shape=[self._num_states, self._data_dim, self._data_dim])
      return MultivariateNormalFullCovariance(loc=self._mu_tf,
                                              covariance_matrix=self._sigma_tf)

  def _emissions_eval(self):
    with tf.variable_scope('emissions_eval'):
      dataset_expanded = tf.expand_dims(self._dataset_tf, -2)
      self._emissions = self._em_probs.prob(dataset_expanded)

  def _forward_step(self, n, alpha, c):
    # calculate alpha[n-1] tp
    alpha_tp = tf.matmul(alpha[n - 1], self._tp_tf)
    # calculate p(x|z) \sum_z alpha[n-1] tp
    a_n_tmp = tf.multiply(tf.squeeze(self._emissions[:, n, :]), alpha_tp)
    c_n_tmp = tf.expand_dims(tf.reduce_sum(a_n_tmp, axis=-1), -1)
    return [n + 1, tf.concat([alpha, tf.expand_dims(a_n_tmp / c_n_tmp, 0)], 0),
            tf.concat([c, tf.expand_dims(c_n_tmp, 0)], 0)]

  def _backward_step(self, n, betta, b_p):
    b_p_tmp = tf.multiply(betta[0],
                          tf.squeeze(self._emissions[:, -n, :]))
    b_n_tmp = tf.matmul(b_p_tmp, self._tp_tf, transpose_b=True) / self._c[-n]
    return [n + 1, tf.concat([tf.expand_dims(b_n_tmp, 0), betta], 0),
            tf.concat([tf.expand_dims(b_p_tmp, 0), b_p], 0)]

  def _simulate_step(self, n, states, samples):
    state = tf.expand_dims(
      tf.where(
        tf.squeeze(
          self._cum_tp_tf[
            tf.cast(states[n - 1, 0], dtype='int32')] > self._rand[n]))[0], 0)
    sample = tf.expand_dims(self._em_probs.sample()[tf.cast(
      state[0, 0], dtype='int32')], 0)
    return [n + 1, tf.concat(
      [states, state], 0), tf.concat([samples, sample], 0)]

  def _forward(self):
    with tf.variable_scope('forward'):
      n = tf.shape(self._dataset_tf)[1]
      # alpha shape : (N, I, states)
      # c shape : (N, I, 1)
      a_0_tmp = tf.expand_dims(
        tf.multiply(self._emissions[:, 0, :], tf.squeeze(self._p0_tf)), 0)
      c_0 = tf.expand_dims(tf.reduce_sum(a_0_tmp, axis=-1), -1)
      alpha_0 = a_0_tmp / c_0
      i0 = tf.constant(1)
      condition_forward = lambda i, alpha, c: tf.less(i, n)
      _, self._alpha, self._c = \
          tf.while_loop(
            condition_forward,
            self._forward_step,
            [i0, alpha_0, c_0],
            shape_invariants=[
              i0.get_shape(),
              tf.TensorShape(
                [None, None, self._num_states]),
              tf.TensorShape([None, None, 1])])
      self._posterior = tf.reduce_sum(tf.log(self._c), axis=0)

  def _backward(self):
    with tf.variable_scope('backward'):
      n = tf.shape(self._dataset_tf)[1]
      shape = tf.shape(self._dataset_tf)[0]
      dims = tf.stack([shape, self._num_states])
      b_tmp_ = tf.fill(dims, 1.0)
      betta_0 = tf.expand_dims(tf.ones_like(b_tmp_, dtype=tf.float64), 0)
      b_p_0 = tf.expand_dims(tf.ones_like(b_tmp_, dtype=tf.float64), 0)
      i0 = tf.constant(1)
      condition_backward = lambda i, betta, b_p: tf.less(i, n)
      _, self._betta, b_p_tmp = \
          tf.while_loop(
            condition_backward,
            self._backward_step,
            [i0, betta_0, b_p_0],
            shape_invariants=[
              i0.get_shape(),
              tf.TensorShape([None, None, self._num_states]),
              tf.TensorShape([None, None, self._num_states])])
      self._b_p = b_p_tmp[:-1, :, :]

  def _simulate(self):
    with self._graph.as_default():
      self._rand = tf.random_uniform(
        [self._num_samples_tf, 1], maxval=1.0, dtype='float64')
      self._cum_p0_tf = tf.cumsum(self._p0_tf, axis=1)
      self._cum_tp_tf = tf.cumsum(self._tp_tf, axis=1)
      # initial sample
      _init_sample_state = tf.expand_dims(
        tf.where(tf.squeeze(self._cum_p0_tf > self._rand[0]))[0], 0)
      _init_sample = tf.expand_dims(self._em_probs.sample()[tf.cast(
        _init_sample_state[0, 0], dtype='int32')], 0)
      i0 = tf.constant(1, dtype='int32')
      condition_sim = lambda i, states, samples: tf.less(
        i, self._num_samples_tf)
      _, self._states, self._samples = tf.while_loop(
        condition_sim, self._simulate_step,
        [i0, _init_sample_state, _init_sample],
        shape_invariants=[
          i0.get_shape(), tf.TensorShape(
            [None, 1]), tf.TensorShape([None, self._data_dim])])

  def _xi_calc(self, n, xi):
    a_b_p = tf.matmul(
      tf.expand_dims(self._alpha[n - 1] / self._c[n], -1),
      tf.expand_dims(self._b_p[n - 1], -1), transpose_b=True)
    xi_n_tmp = tf.multiply(a_b_p, self._tp_tf)
    return [n + 1, tf.concat([xi, tf.expand_dims(xi_n_tmp, 0)], 0)]

  def _expectation(self):
    with tf.variable_scope('expectation'):
      # gamma shape : (N, I, states)
      self._gamma = tf.multiply(self._alpha, self._betta, name='gamma')
      n = tf.shape(self._dataset_tf)[1]
      shape = tf.shape(self._dataset_tf)[0]
      dims = tf.stack([shape, self._num_states, self._num_states])
      xi_tmp_ = tf.fill(dims, 1.0)
      xi_0 = tf.expand_dims(tf.ones_like(xi_tmp_, dtype=tf.float64), 0)
      i0 = tf.constant(1)
      condition_xi = lambda i, xi: tf.less(i, n)
      _, xi_tmp = tf.while_loop(
        condition_xi, self._xi_calc, [i0, xi_0],
        shape_invariants=[i0.get_shape(), tf.TensorShape(
          [None, None, self._num_states, self._num_states])])
      self._xi = xi_tmp[1:, :, :]

  def _maximization(self):
    with tf.variable_scope('maximization'):
      max_var = 20.0
      gamma_mv = tf.reduce_mean(self._gamma, axis=1, name='gamma_mv')
      # self._gamma_mv = gamma_mv
      # print('gamma_mv shape : ', gamma_mv.get_shape())
      xi_mv = tf.reduce_mean(self._xi, axis=1, name='xi_mv')
      # update the initial state probabilities
      self._p0_tf_new = tf.transpose(tf.expand_dims(gamma_mv[0], -1))
      # update the transition matrix
      # first calculate sum_n=2^{N} xi_mean[n-1,k , n,l]
      sum_xi_mean = tf.squeeze(tf.reduce_sum(xi_mv, axis=0))
      self._tp_tf_new = sum_xi_mean / (tf.reduce_sum(sum_xi_mean,
                                                     axis=1,
                                                     keepdims=True))

      # emissions update
      x_t = tf.transpose(self._dataset_tf, perm=[1, 0, 2], name='x_transpose')
      gamma_x = tf.matmul(tf.expand_dims(self._gamma, -1),
                          tf.expand_dims(x_t, -1), transpose_b=True)
      sum_gamma_x = tf.reduce_sum(gamma_x, axis=[0, 1])
      mu_tmp_t = tf.transpose(sum_gamma_x) / tf.reduce_sum(
        self._gamma,
        axis=[0, 1])
      self._mu_tf_new = tf.transpose(mu_tmp_t)
      # update the covariances
      # gamma shape : (N, I, states)
      # x shape : (I, N, dim)
      # mu shape : (states, dim)
      x_expanded = tf.expand_dims(self._dataset_tf, -2)
      # calculate (x - mu) tensor : expected shape (I, N, states, dim)
      x_m_mu = tf.subtract(x_expanded, self._mu_tf)
      # calculate (x - mu)(x - mu)^T : expected shape (I, N, states, dim, dim)
      x_m_mu_2 = tf.matmul(tf.expand_dims(x_m_mu, -1),
                           tf.expand_dims(x_m_mu, -2))
      gamma_r = tf.transpose(self._gamma, perm=[1, 0, 2])
      gamma_x_m_mu_2 = tf.multiply(
                          x_m_mu_2,
                          tf.expand_dims(tf.expand_dims(gamma_r, -1), -1))
      _new_cov_tmp = tf.reduce_sum(
        gamma_x_m_mu_2,
        axis=[0, 1]) / tf.expand_dims(
        tf.expand_dims(
          tf.reduce_sum(
            gamma_r,
            axis=[0, 1]), -1), -1)
      lowest_var = (0.5 * max_var + self._min_var_tf) * \
          tf.tile(
            tf.expand_dims(
              tf.Variable(
                initial_value=np.identity(
                  self._data_dim,
                  dtype=np.float64),
                dtype=tf.float64), 0),
            [self._num_states, 1, 1])
      lowest_cov = -0.5 * max_var * tf.ones(
        [self._num_states, self._data_dim, self._data_dim], dtype=tf.float64)
      lowest_c = tf.add(lowest_cov, lowest_var)
      highest_var = (-0.5 * max_var + max_var) * \
          tf.tile(
            tf.expand_dims(
              tf.Variable(
                  initial_value=np.identity(
                    self._data_dim,
                    dtype=np.float64),
                  dtype=tf.float64), 0),
            [self._num_states, 1, 1])
      highest_cov = 0.5 * max_var * tf.ones(
        [self._num_states, self._data_dim, self._data_dim], dtype=tf.float64)
      highest_c = tf.add(highest_cov, highest_var)
      _new_cov_tmp2 = tf.maximum(lowest_c, _new_cov_tmp)
      self._sigma_tf_new = tf.minimum(highest_c, _new_cov_tmp2)

  def _viterbi_step(self, n, w, am):
    w_tmp = tf.expand_dims(tf.log(self._emissions[:, n]) + tf.reduce_max(
          tf.expand_dims(w[:, n - 1], -1) + tf.expand_dims((tf.log(self._tp_tf)), 0) , axis=-2), 1)
    am_tmp = tf.expand_dims(tf.argmax(tf.expand_dims(w[:, n - 1], -1) + tf.expand_dims((tf.log(self._tp_tf)), 0) , axis=-2), 1)
    return [n + 1, tf.concat([w, w_tmp], 1), tf.concat([am, am_tmp], 1)]

  def _viterbi(self):
    with self._graph.as_default():
      m = tf.shape(self._dataset_tf)[0]
      n = tf.shape(self._dataset_tf)[1]
      w1 = tf.expand_dims(
        tf.log(self._p0_tf) + tf.log(self._emissions[:, 0]), 1)
      am1 = tf.zeros_like(w1, dtype='int64')
      i0 = tf.constant(1)
      condition_viterbi = lambda i, w, am: tf.less(i, n)
      _, self._w, self._am = tf.while_loop(
        condition_viterbi, self._viterbi_step, [i0, w1, am1], shape_invariants=[
          i0.get_shape(), tf.TensorShape([None, None, self._num_states]), tf.TensorShape([None, None, self._num_states])])

  def _is_pos_def(self, sigma):
    return np.all(np.linalg.eigvals(sigma) > 0.02)

  def _init_p0_tp(self):
    tp = np.ones([self._num_states, self._num_states], dtype=np.float64) / self._num_states
    p0 = np.ones([1, self._num_states], dtype=np.float64) / self._num_states
    if self._hmm_type == 'left-to-right' or self._hmm_type == 'cyclic':
      p0[0, 0] = 1.0
      for i in range(self._num_states):
        p0[0, i] = 0.0
        for j in range(i):
          tp[i, j] = 0.0
        if self._hmm_type == 'left-to-right':
          tp[i, i] = 0.9
        else:
          tp[i, i] = 0.5
        if i < self._num_states - 1:
          if self._hmm_type == 'left-to-right':
            tp[i, i + 1] = 0.1
          else:
            tp[i, i + 1] = 0.5
        for j in range(i + 2, self._num_states):
          tp[i, j] = 0.0
      tp[-1, -1] = 1.0
      p0[0, 0] = 1.0
    if self._hmm_type == 'cyclic':
      tp[-1, 0] = 0.5
      tp[-1, -1] = 0.5
      p0 = np.ones([1, self._num_states], dtype=np.float64) / self._num_states
    return p0, tp
     
