class LIFNeuronSTDP:
    def __init__(self, num_synapses=2, v_th=100, leak_shift=3):
        self.v_mem = 0
        self.v_th = v_th
        self.leak_shift = leak_shift
        self.weights = [35 for _ in range(num_synapses)]
        self.pre_trace = [0 for _ in range(num_synapses)]
        self.post_trace = 0
        self.stdp_window = 5

    def step(self, spikes_in):
        # 1. Vazamento por bit-shift (V_mem / 2^k)
        leak = self.v_mem >> self.leak_shift
        self.v_mem -= leak

        # 2. Integração dos pesos das sinapses ativas
        for i, s in enumerate(spikes_in):
            if s == 1:
                self.v_mem += self.weights[i]
                self.pre_trace[i] = self.stdp_window
                if self.post_trace > 0:
                    self.weights[i] = max(0, self.weights[i] - 2)

        # 3. Comparador de disparo
        spike_out = 0
        if self.v_mem >= self.v_th:
            spike_out = 1
            self.v_mem = 0
            self.post_trace = self.stdp_window
            for i in range(len(self.weights)):
                if self.pre_trace[i] > 0:
                    self.weights[i] = min(127, self.weights[i] + 3)

        # 4. Decaimento dos traços STDP
        for i in range(len(self.pre_trace)):
            if self.pre_trace[i] > 0:
                self.pre_trace[i] -= 1
        if self.post_trace > 0:
            self.post_trace -= 1

        return spike_out, self.v_mem, list(self.weights)


if __name__ == "__main__":
    neuron = LIFNeuronSTDP(num_synapses=2, v_th=100, leak_shift=3)
    print(f"{'t':>3} | {'In':>6} | {'V_mem':>5} | {'Spike':>5} | {'Pesos [W0, W1]'}")
    print("-" * 46)

    for t in range(30):
        s0 = 1 if (t % 3 == 0) else 0
        s1 = 1 if (t % 7 == 0 and t > 0) else 0
        spike, v_mem, weights = neuron.step([s0, s1])
        print(f"{t:3d} | [{s0}, {s1}] | {v_mem:5d} | {spike:5d} | {weights}")