import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge

@cocotb.test()
async def test_lif_bit_exact(dut):
    """Compara o módulo lif_neuron.v contra o modelo matemático bit a bit."""
    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())

    dut.rst_n.value = 0
    dut.en.value = 0
    dut.syn_in.value = 0
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)

    dut.rst_n.value = 1
    dut.en.value = 1

    v_ref = 0
    v_th = 100

    for cycle in range(15):
        syn = 35 if cycle < 10 else 0
        dut.syn_in.value = syn
        await RisingEdge(dut.clk)

        # Modelo de referência em Python
        leak = v_ref >> 3
        v_next = (v_ref - leak) + syn
        if v_next >= v_th:
            spike_ref = 1
            v_ref = 0
        else:
            spike_ref = 0
            v_ref = v_next

        # Aguarda estabilização da saída registrada
        await RisingEdge(dut.clk)
        assert int(dut.v_mem.value) == v_ref, f"Ciclo {cycle}: v_mem={int(dut.v_mem.value)} != {v_ref}"
        assert int(dut.spike_out.value) == spike_ref, f"Ciclo {cycle}: spike={int(dut.spike_out.value)} != {spike_ref}"