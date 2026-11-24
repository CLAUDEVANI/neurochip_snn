# NeuroChip SNN

Núcleo neuromórfico baseado em **Spiking Neural Networks (SNN)** implementado em Verilog RTL sintetizável, com neurônios **LIF** (*Leaky Integrate-and-Fire*), plasticidade sináptica **STDP** (*Spike-Timing-Dependent Plasticity*), roteamento **AER** (*Address-Event Representation*) e wrapper compatível com **Tiny Tapeout**.

## Arquitetura RTL (`rtl/`)

| Módulo | Descrição |
| :--- | :--- |
| `lif_neuron.v` | Neurônio LIF de 8 bits com vazamento por deslocamento (`LEAK_SHIFT`), limiar configurável (`V_TH`) e reset assíncrono. |
| `stdp_synapse.v` | Sinapse com aprendizado local STDP (LTP/LTD), traços pré/pós-sinápticos e saturação segura em `MAX_W`. |
| `snn_layer.v` | Camada totalmente conectada (2 entradas x 4 neurônios LIF + 8 sinapses STDP). |
| `snn_multilayer.v` | Rede multicamada em cascata (`L1` oculta -> `L2` saída). |
| `aer_top.v` | Codificador/decodificador AER com fila de eventos pendentes. |
| `tt_um_neurochip_snn.v` | Top-level compatível com o barramento padrão do Tiny Tapeout com telemetria de spikes. |

## Mapa de Pinos (`tt_um_neurochip_snn`)

| Pino | Direção | Função |
| :--- | :--- | :--- |
| `ui_in[0]` | Entrada | `en` — Habilitação do núcleo (combinada com `ena`) |
| `ui_in[1]` | Entrada | `aer_in_valid` — Pulso de evento AER de entrada |
| `ui_in[2]` | Entrada | `aer_in_addr` — Endereço do canal de entrada (`0` ou `1`) |
| `uo_out[0]` | Saída | `aer_out_valid` — Indica disparo AER de saída |
| `uo_out[2:1]` | Saída | `aer_out_addr[1:0]` — Endereço do neurônio que disparou |
| `uo_out[6:3]` | Saída | `spike_cnt[3:0]` — Contador de telemetria de spikes |
| `uo_out[7]` | Saída | `core_en` — Status de operação do núcleo |

## Execução Unificada (`./neurochip_snn.sh`)

    ./neurochip_snn.sh help        # Lista todos os comandos
    ./neurochip_snn.sh sim-all     # Roda pytest + simulações RTL + corner cases
    ./neurochip_snn.sh synth-all   # Roda síntese ASIC no Yosys e salva build/*.rpt
    ./neurochip_snn.sh ci          # Pipeline completo (sim-all + synth-all)
    ./neurochip_snn.sh dashboard   # Abre o monitor interativo no Streamlit
    ./neurochip_snn.sh clean       # Limpa artefatos temporários em build/

## Integração Contínua (CI)

O workflow `.github/workflows/ci.yml` executa `./neurochip_snn.sh sim-all` e `./neurochip_snn.sh synth-all` em cada push/PR na branch `main`, publicando os relatórios de síntese do Yosys como artefatos do GitHub Actions.
