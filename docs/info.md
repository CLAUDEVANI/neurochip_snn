## Como funciona

O **NeuroChip SNN** implementa um núcleo neuromórfico digital em Verilog sintetizável composto por:
- **Neurônios LIF** (`lif_neuron.v`) de 8 bits com vazamento por deslocamento (`LEAK_SHIFT = 3`) e limiar configurável (`V_TH = 100`).
- **Sinapses STDP** (`stdp_synapse.v`) com plasticidade local (LTP/LTD) e saturação segura em `MAX_W = 127`.
- **Roteamento AER** (`aer_top.v`) para entrada e saída serializada de eventos de disparo.
- **Telemetria em hardware** (`tt_um_neurochip_snn.v`) expondo um contador de 4 bits (`uo_out[6:3]`) e o sinal de status `core_en` (`uo_out[7]`).

## Como testar

1. Aplique reset (`rst_n = 0` por alguns ciclos, depois `rst_n = 1`) e habilite o chip (`ena = 1`, `ui_in[0] = 1`).
2. Envie pulsos AER em `ui_in[1]` (`aer_in_valid = 1`) selecionando o canal em `ui_in[2]` (`0` ou `1`).
3. Monitore `uo_out[0]` (`aer_out_valid`), o endereço do neurônio em `uo_out[2:1]` e o incremento do contador de telemetria em `uo_out[6:3]`.
