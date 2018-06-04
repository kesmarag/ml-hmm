from setuptools import setup

setup(name='kesmarag-ml-hmm',
      version='0.0.9',
      description='An implementation of the Gaussian Hidden Markov Model on top of TensorFlow',
      author='Costas Smaragdakis',
      author_email='kesmarag@gmail.com',
      url='https://github.com/kesmarag/ml-hmm',
      packages=['kesmarag.ml.hmm'],
      package_dir={'kesmarag.ml.hmm': './'},
      install_requires=['tensorflow==1.5.0',
                        'numpy>=1.12.1',
                        'scikit-learn>=0.18.1',
                        'kesmarag-ml-utils'], )
