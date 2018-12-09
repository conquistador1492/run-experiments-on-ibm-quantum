from setuptools import setup, find_packages

setup(name='qchannels',
      version='0.1',
      description='More comfortable interface for IBM Quantum Experience',
      author='Alexey Pakhomchik',
      author_email='aleksey.pakhomchik@gmail.com',
      license='MIT',  # TODO
      packages=find_packages(exclude=['test*']),
      install_requires=[
          'tqdm>=4.25.0',
          'qiskit==0.6.1',
          'jsonschema>=2.6.0',
          'psutil>=5.4.7'
      ],
      zip_safe=False)