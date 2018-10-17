#!/usr/bin/env python3.6
# -*- coding: utf-8 -*-

from Qconfig import config
from qiskit import QuantumRegister, ClassicalRegister, execute, IBMQ
from qiskit import QuantumCircuit
from qiskit.tools.qcvv.tomography import fit_tomography_data, tomography_set, create_tomography_circuits
from qiskit.tools.qcvv.tomography import tomography_data

import numpy as np
import argparse
from copy import copy
from collections import OrderedDict

from tools import chunks, MAX_JOBS_PER_ONE, SIMULATORS
from landau import LandauCircuit
from basis import QUTRIT_BASIS_FUNC
from theory import get_matrix_from_tomography_to_eij, fidelity, create_theory_choi_matrix
from theory import get_qutrit_density_matrix_basis, theory_landau_channel

parser = argparse.ArgumentParser(description='Run experiments on IBM computers')
parser.add_argument('-n', '--num-token', type=int, default=0, help='Number of token from Qconfig.py')
parser.add_argument('-t', '--token', default=None, help='Specific token')
parser.add_argument('-b', '--backend', type=str, default='ibmq_16_melbourne', help='Name of backend (default: %(default)s)')
parser.add_argument('-s', '--shots', type=int, default=8192, help='Number of shots in experiment')

args = parser.parse_args()
if args.token is not None:
    APItoken = args.token
else:
    from Qconfig import tokens
    APItoken = tokens[args.num_token]
IBMQ.enable_account(APItoken, **config)

backend = next(filter(lambda backend: backend.configuration().get('name') == args.backend, IBMQ.backends()))
shots = args.shots

if args.backend in SIMULATORS:
    MAX_JOBS_PER_ONE = 10**6  # approximately infinity :)

num_qubits = 5
circuit_name = 'landau'
np.set_printoptions(threshold=np.nan)
q = QuantumRegister(num_qubits)
c = ClassicalRegister(num_qubits)

measure_basis = [0, 3]
tomo_set = tomography_set(measure_basis)
number_measure_experiments = 3**len(measure_basis)

jobs = []
for rho_f in QUTRIT_BASIS_FUNC:
    qc = QuantumCircuit(q, c)
    rho_f(q, c, qc)
    qc += LandauCircuit(q, c, name=circuit_name,
                        coupling_map=backend.configuration()['coupling_map'])
    qc.name = circuit_name + '_' + qc.name
    circuits = create_tomography_circuits(qc, q, c, tomo_set)
    jobs.extend(circuits)

res = None
for i, part_jobs in enumerate(chunks(jobs, MAX_JOBS_PER_ONE)):
    print(f'chunk number: {i + 1}')
    execute_kwargs = {
        'circuits': part_jobs,
        'backend': backend,
        'shots': shots,
        'max_credits': 15
    }
    new_res = execute(**execute_kwargs).result()
    if res is None:
        res = new_res
    else:
        res += new_res

matrices = []
for i in range(int(len(res)/number_measure_experiments)):
    initial_state_circuit_name = 'rho_' + ['A', 'B', 'C'][i//3] + str(i % 3)
    res_matrix = copy(res)
    res_matrix.results = OrderedDict(zip(
        list(res_matrix.results.keys())[i*number_measure_experiments:(i+1)*number_measure_experiments],
        list(res_matrix.results.values())[i*number_measure_experiments:(i+1)*number_measure_experiments]
    ))
    matrices.append(fit_tomography_data(tomography_data(
        res_matrix, circuit_name + '_' + initial_state_circuit_name, tomo_set
    ))[:3,:3])


print('Fidelity of tomography')
for i, rho in enumerate(get_qutrit_density_matrix_basis()):
    print(fidelity(theory_landau_channel(rho), matrices[i]))
print('=======')

matrices = np.array(matrices)
tomo_to_eij = get_matrix_from_tomography_to_eij()
eij_matrices = [[None for i in range(3)] for j in range(3)]
for i in range(3):
    for j in range(3):
        eij_matrices[i][j] = np.tensordot(tomo_to_eij[:, 3*i+j], matrices, axes=(0, 0))
choi_exp = np.block(eij_matrices)/3
print(fidelity(choi_exp, create_theory_choi_matrix()))