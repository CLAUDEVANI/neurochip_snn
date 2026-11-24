# NeuroChip SNN — Núcleo Neuromórfico em Verilog (LIF + STDP + AER)

Projeto de hardware digital sintetizável de um núcleo neuromórfico (*Spiking Neural Network*) em aritmética inteira de 8 bits, com aprendizado local em silício (**STDP**), interface orientada a eventos (**AER** com fila sem perda) e encapsulamento compatível com fabricação ASIC **Tiny Tapeout**.

## Arquitetura

- **Neurônio LIF (`rtl/lif_neuron.v`):** Modelo *Leaky Integrate-and-Fire* em ponto fixo (8 bits) com decaimento exponencial implementado via *bit-shift* (`V_mem >> 3`), eliminando multiplicadores.
- **Sinapse STDP (`rtl/stdp_synapse.v`):** Aprendizado local *Spike-Timing-Dependent Plasticity* em hardware com janelas temporais (`pre_trace`, `post_trace`), potenciação (LTP) e depressão (LTD) saturadas.
- **Camada SNN (`rtl/snn_layer.v`):** 4 neurônios LIF em paralelo com 8 sinapses STDP e soma saturada.
- **Rede Multicamada (`rtl/snn_multilayer.v`):** Cascata de 2 camadas SNN (8 neurônios, 16 sinapses STDP).
- **Interface AER (`rtl/aer_top.v`):** Decodificador de entrada e árbitro de saída com fila de eventos pendentes (`pending_spikes`) para evitar perda de disparos simultâneos.
- **Wrapper ASIC (`rtl/tt_um_neurochip_snn.v`):** Mapeamento de pinos no padrão oficial do Tiny Tapeout (`ui_in`, `uo_out`, `uio_*`, `ena`, `clk`, `rst_n`).

## Resultados de Síntese (Yosys 0.52)

| Top Module | Células Lógicas | Flip-Flops | Status |
| :--- | :---: | :---: | :---: |
| `aer_top` | 1.677 | 168 bits | 0 erros / 0 latches |
| `tt_um_neurochip_snn` | 1.678 | 168 bits | Pronto para Tiny Tapeout |

## Estrutura do Projeto

```text
neurochip_snn/
├── rtl/          # Verilog sintetizável (LIF, STDP, Camada, Multicamada, AER, Tiny Tapeout)
├── tb/           # Testbenches em Verilog e verificação Cocotb
├── sim/          # Modelo dourado Python, codificador de sinal 60 Hz e dashboard Streamlit
├── build/        # Binários compilados, ondas (.vcd) e esquemáticos (.svg)
└── Makefile      # Automação de simulação, síntese e visualização