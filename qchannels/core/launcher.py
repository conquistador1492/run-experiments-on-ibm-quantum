from collections import OrderedDict
from copy import copy

from qiskit import execute, QuantumCircuit
from qiskit.tools.qcvv.tomography import fit_tomography_data, tomography_set
from qiskit.tools.qcvv.tomography import tomography_data, create_tomography_circuits

from qchannels.core.tools import MAX_JOBS_PER_ONE, SIMULATORS, BACKENDS, chunks


class Launcher:
    def __init__(self, token=None, backend_name='ibmq_16_melbourne',
                 shots=8192):
        self.shots = shots
        self.token = token

        self.backend = next(filter(lambda x: x.name() == backend_name, BACKENDS))

        if backend_name in SIMULATORS:
            self.max_jobs_per_one = 10**6  # approximately infinity :)
        else:
            self.max_jobs_per_one = MAX_JOBS_PER_ONE

    def run(self, circuits, meas_qubits=None, measure=None):
        """
        :param circuits: list of QuantumCircuit or QuantumCircuit
        :param meas_qubits: list of qubits that will be measured.
        :param measure: optional. By default after channel transformation we do tomography.
        Not implemented now
        :return: depend on measure parameter. By default, it's list of density matrix
        """
        if measure is not None:
            raise NotImplementedError

        if isinstance(circuits, QuantumCircuit):
            circuits = [circuits]

        tomo_set = tomography_set(meas_qubits)
        number_measure_experiments = 3**len(meas_qubits)

        jobs = []
        for qc in circuits:
            q, c = list(qc.get_qregs().values())[0], list(qc.get_cregs().values())[0]
            tomo_circuits = create_tomography_circuits(qc, q, c, tomo_set)
            jobs.extend(tomo_circuits)

        res = None
        for i, chunk_jobs in enumerate(chunks(jobs, self.max_jobs_per_one)):
            print(f'chunk number: {i + 1}')
            execute_kwargs = {
                'circuits': chunk_jobs,
                'backend': self.backend,
                'shots': self.shots,
                'max_credits': 15
            }
            new_res = execute(**execute_kwargs).result()
            if res is None:
                res = new_res
            else:
                res += new_res

        matrices = []
        for i in range(int(len(res) / number_measure_experiments)):
            res_matrix = copy(res)
            res_matrix.results = OrderedDict(zip(
                list(res_matrix.results.keys())[
                    i*number_measure_experiments:(i + 1)*number_measure_experiments
                ],
                list(res_matrix.results.values())[
                    i*number_measure_experiments:(i + 1)*number_measure_experiments
                ]
            ))
            tomo_data = tomography_data(
                res_matrix, circuits[i].name, tomo_set
            )
            rho = fit_tomography_data(tomo_data)
            matrices.append(rho)
        return matrices


