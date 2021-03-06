#!/usr/bin/env python3.6
# -*- coding: utf-8 -*-


from scipy.linalg import sqrtm
import numpy as np
from cmath import sqrt

DIM = 3


def get_state(a, *, dim=None):
    """
    :return: np.array that has length is equal to dim
    >>> np.array_equal(get_state(1, dim=3), np.array([[0], [1], [0]]))
    True
    """
    if dim is None:
        dim = DIM
    vals = [[0] for i in range(dim)]
    vals[a][0] = 1
    return np.array(vals)


def get_density_matrix_from_state(state):
    """
    >>> np.array_equal(
    ...     get_density_matrix_from_state(get_state(0, dim=2)),
    ...     np.array([[1, 0], [0, 0]])
    ... )
    True
    """
    return state@np.transpose(np.conj(state))


def get_qutrit_density_matrix_basis():
    basis_states = np.array(
        [get_state(a) for a in [0b00, 0b01, 0b10]] +
        [(get_state(a) + get_state(b)) / np.sqrt(2) for a, b in [(0b00, 0b01), (0b00, 0b10), (0b01, 0b10)]] +
        [(get_state(a) + 1j * get_state(b)) / np.sqrt(2) for a, b in [(0b00, 0b01), (0b00, 0b10), (0b01, 0b10)]]
    )
    return np.array(
        [state@np.transpose(np.conj(state)) for state in basis_states]
    )


def fidelity(rho1, rho2):
    """
    R. Jozsa, Fidelity for mixed quantum states. J. Modern Opt. 41, 2315–2323 (1994)
    https://arxiv.org/pdf/quant-ph/0408063.pdf
    >>> rho = get_density_matrix_from_state(get_state(1, dim=2))
    >>> fidelity(rho, rho) > 0.999
    True
    """
    return np.trace(sqrtm(
        sqrtm(rho1)@rho2@sqrtm(rho1)
    ))**2


def create_choi_matrix_from_channel(channel, dim=DIM):
    """
    Building choi matrix C = (Id * Channel) (|psi+><psi+|)
    https://journals.aps.org/pra/abstract/10.1103/PhysRevA.87.022310
    :param channel: function
    >>> identity_channel = lambda rho: rho
    >>> np.array_equal(
    ...     create_choi_matrix_from_channel(identity_channel, dim=2),
    ...     np.array([
    ...         [1, 0, 0, 1],
    ...         [0, 0, 0, 0],
    ...         [0, 0, 0, 0],
    ...         [1, 0, 0, 1]
    ...     ])/2
    ... )
    True
    """
    blocks = [[None for i in range(dim)] for j in range(dim)]
    for i in range(dim):
        for j in range(dim):
            rho = np.zeros((dim, dim), dtype=complex)
            rho[i,j] = 1
            blocks[i][j] = np.copy(channel(rho))
    return np.block(blocks)/dim


def get_kraus_operators_from_choi(choi):
    """
    https://quantumcomputing.stackexchange.com/questions/5804/vectorization-map-to-dynamical-map

    :param choi:
    :return:
    """
    dim = int(np.sqrt(choi.shape[0]))

    # TODO Workaround
    if np.abs(np.trace(choi) - 1) < 10**(-2):
        choi *= dim

    eigenvalues, eigenvects = np.linalg.eig(choi)
    if (np.imag(eigenvalues) > 10**(-3)*np.max(np.abs(eigenvalues))).any():
        raise Exception('The Choi matrix has to be hermitian')
    eigenvalues = np.real(eigenvalues)

    for i, a in enumerate(eigenvects.T):
        for j, b in enumerate(eigenvects.T):
            if np.abs(np.conj(a.T)@b - (1 if i == j else 0)) > 10**(-3):
                raise NotImplementedError('Numpy returned non-orthogonal vectors')

    kraus_operators = []
    if int(np.sqrt(choi.shape[0])) != np.sqrt(choi.shape[0]):
        raise TypeError('The Choi matrix must have dimension that equal to n**2 x n**2')

    max_abs_eigenvalue = np.max(np.abs(eigenvalues))
    for i, value in enumerate(eigenvalues):
        if np.abs(value) < 10**(-3)*max_abs_eigenvalue:
            continue

        matrix = sqrt(value)*eigenvects.T[i].reshape((dim, dim))
        if not np.allclose(matrix, np.conj(matrix.T), atol=1e-3):
            # Try to make hermitian
            exit = False
            for i in range(matrix.shape[0]):
                if exit:
                    break

                for j in range(i + 1, matrix.shape[0]):
                    if (np.abs(matrix[i, j]) < 1e-3 < np.abs(matrix[j, i])) or \
                            (np.abs(matrix[i, j]) > 1e-3 > np.abs(matrix[j, i])):
                        exit = True; break
                    elif np.abs(matrix[i, j]) < 1e-3 and np.abs(matrix[j, i]) < 1e-3:
                        continue
                    else:
                        matrix *= -sqrt(np.conj(matrix[j, i])/matrix[i, j])
                        exit = True; break

        kraus_operators.append(matrix)
    return kraus_operators if len(kraus_operators) > 0 else [np.eye(dim)]


def partial_trace_with_halves(Rho, half):
    if np.sqrt(Rho.shape[0]) != int(np.sqrt(Rho.shape[0])):
        raise TypeError('Density matrix must have dimension that equal to n**2 x n**2')

    channel_dim = int(np.sqrt(Rho.shape[0]))

    from sympy import MatrixBase
    if isinstance(Rho, (np.ndarray, np.generic)):
        output_rho = np.zeros((channel_dim, channel_dim), dtype=complex)
    elif isinstance(Rho, MatrixBase):
        from sympy import zeros
        output_rho = zeros(channel_dim)
    else:
        raise TypeError('Unknown type of Rho')

    if half == 1:
        for i in range(channel_dim):
            for j in range(channel_dim):
                for k in range(channel_dim):
                    output_rho[i,j] += Rho[i*channel_dim + k, j*channel_dim + k]
    elif half == 2:
        for i in range(channel_dim):
            for j in range(channel_dim):
                for k in range(channel_dim):
                    output_rho[i,j] += Rho[i + k*channel_dim, j + k*channel_dim]
    return output_rho


def create_channel_from_choi_matrix(choi):
    if np.sqrt(choi.shape[0]) != int(np.sqrt(choi.shape[0])):
        raise TypeError('Choi matrix must have dimension that equal to n**2 x n**2')

    channel_dim = int(np.sqrt(choi.shape[0]))

    def _channel(rho):
        mat = channel_dim*np.kron(rho.transpose(), np.eye(channel_dim, dtype=complex))@choi
        return partial_trace_with_halves(mat, 2)
    return _channel


def get_matrix_from_tomography_to_eij(matrices=None):
    """
    Transformation matrix from matrices to eij(eij = |i><j|)
    >>> sigma0, sigmaz = np.eye(2), np.diag([1, -1])
    >>> sigmax, sigmay = np.array([[0, 1], [1, 0]]), np.array([[0, -1j], [1j, 0]])
    >>> np.array_equal(
    ...     get_matrix_from_tomography_to_eij([sigma0, sigmax, sigmay, sigmaz]),
    ...     np.array([
    ...         [1, 0, 0, 1],
    ...         [0, 1, 1j, 0],
    ...         [0, 1, -1j, 0],
    ...         [1, 0, 0, -1],
    ...     ])/2
    ... )
    True
    """
    if matrices is None:
        matrices = get_qutrit_density_matrix_basis()

    dim = matrices[0].shape[0]
    ER = np.zeros((dim**2, dim**2), dtype=complex)
    for k, matrix in enumerate(matrices):
        for i in range(dim):
            for j in range(dim):
                ER[dim * i + j, k] = matrix[i, j]
    return np.transpose(np.linalg.inv(ER))

if __name__ == '__main__':
    from importlib import import_module
    import doctest

    doctest.testmod()

    module = import_module('qchannels.channels')
    channel_class_names = filter(lambda x: 'Circuit' in x and 'AbstractChannel' not in x, dir(module))
    for class_name in channel_class_names:
        channelClass = getattr(import_module('qchannels.channels'), class_name)
        try:
            choi = create_choi_matrix_from_channel(channelClass.get_theory_channel())
        except NotImplementedError:
            pass
        assert(0.999 < fidelity(choi, choi) < 1.001)
