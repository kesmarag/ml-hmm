# hmm

## HMM
```python
HMM(self, num_states, data_dim, hmm_type='fully-connected')
```
A Hidden Markov Model class on top of the Tensorflow library.
At the moment, the class supports only Gaussian emission distributions.
The class will also support discrete multivariate and Gaussian Mixture Models
as emission distributions.
The class is licensed under the MIT License.

### posterior
```python
HMM.posterior(self, data)
```
Runs the forward-backward algorithm in order to calculate
the log-scale posterior probabilities.

Args:
data: A numpy array with rank two or three.

Returns:
A numpy array that contains the log-scale posterior probabilities of
each time serie in data.


### fit
```python
HMM.fit(self, data, max_steps=100, batch_size=None, TOL=0.01, min_var=0.1, num_runs=1)
```
Implements the Baum-Welch fitting algorithm.

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


### run_viterbi
```python
HMM.run_viterbi(self, data)
```
Implements the viterbi decoding algorithm.

Args:
  data: A numpy array of rank two or three represents the observed data.

Returns:
  A numpy array contains he most probable hidden state paths.

### generate
```python
HMM.generate(self, num_samples)
```
Generate simulated data from the model.

Args:
  num_samples: The number of samples of the generated data.

Returns:
  The numpy array of the generated sequence of observations.

### save_model
```python
HMM.save_model(self, filename)
```
Saves the model parameters to a numpy file

Args:
  filename: The path to a numppy .npz file where the model parameters will be saved.

### load_model
```python
HMM.load_model(self, filename)
```
Loads the model parameters from a numpy file

Args:
  filename: The path to a numpy .npz file where the model parameters have been stored.

