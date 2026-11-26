import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer

@cocotb.test()
async def test_neurochip_aer_spikes(dut):
    """Injeta rajada de eventos AER e valida ativação do núcleo e geração de spikes."""
    cocotb.start_soon(Clock(dut.clk, 20, unit="ns").start())  # 50 MHz

    dut.ena.value = 1
    dut.rst_n.value = 0
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    await Timer(100, unit="ns")

    dut.rst_n.value = 1
    await RisingEdge(dut.clk)

    spikes_detectados = 0
    for ciclo in range(80):
        # bit0=core_en(1), bit1=aer_in_valid(1), bit2=aer_in_addr(alternando 0/1)
        addr = (ciclo // 4) & 1
        dut.ui_in.value = (addr << 2) | (1 << 1) | 1
        await RisingEdge(dut.clk)
        uo = int(dut.uo_out.value)
        if uo & 0x01:
            spikes_detectados += 1

    uo_final = int(dut.uo_out.value)
    assert (uo_final >> 7) & 1 == 1, "Status core_en (uo_out[7]) deveria estar ativo"
    assert spikes_detectados > 0, f"Esperava spikes > 0, obtido {spikes_detectados}"
    dut._log.info(f"OK: {spikes_detectados} spikes AER validados em 80 ciclos (uo_out=0x{uo_final:02x})")
