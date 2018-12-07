from channels.abstract import AbstractChannelCircuit


class IdentityCircuit(AbstractChannelCircuit):
    @staticmethod
    def get_theory_channel():
        return lambda rho: rho

    def create_circuit(self):
        pass
