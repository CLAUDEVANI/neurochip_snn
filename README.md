# NeuroChip SNN

Núcleo neuromórfico baseado em **Spiking Neural Networks (SNN)** implementado em Verilog RTL sintetizável, com neurônios **LIF** (*Leaky Integrate-and-Fire*), plasticidade sináptica **STDP** (*Spike-Timing-Dependent Plasticity*), roteamento **AER** (*Address-Event Representation*), telemetria de spikes em hardware e fluxos para **Tiny Tapeout (ASIC Sky130)** e **FPGAs Lattice (iCE40 / ECP5)**.

## Arquitetura RTL (`rtl/`)

| Módulo | Descrição |
| :--- | :--- |
| `lif_neuron.v` | Neurônio LIF de 8 bits com vazamento por deslocamento (`LEAK_SHIFT = 3`), limiar configurável (`V_TH = 100`) e reset assíncrono. |
| `stdp_synapse.v` | Sinapse com aprendizado local STDP (LTP/LTD), traços pré/pós-sinápticos e saturação segura em `MAX_W = 127`. |
| `snn_layer.v` | Camada totalmente conectada (2 entradas x 4 neurônios LIF + 8 sinapses STDP). |
| `snn_multilayer.v` | Rede multicamada em cascata (`L1` oculta -> `L2` saída). |
| `aer_top.v` | Codificador/decodificador AER com fila de eventos pendentes. |
| `tt_um_neurochip_snn.v` | Top-level compatível com o Tiny Tapeout (`50 MHz`, tile `1x1`) com contador de telemetria (`spike_cnt[3:0]`) e status `core_en`. |

## Mapa de Pinos (`tt_um_neurochip_snn`)

| Pino | Direção | Função |
| :--- | :--- | :--- |
| `ui_in[0]` | Entrada | `en` — Habilitação do núcleo (combinada com `ena`) |
| `ui_in[1]` | Entrada | `aer_in_valid` — Pulso de evento AER de entrada |
| `ui_in[2]` | Entrada | `aer_in_addr` — Endereço do canal de entrada (`0` ou `1`) |
| `uo_out[0]` | Saída | `aer_out_valid` — Indica disparo AER de saída |
| `uo_out[2:1]` | Saída | `aer_out_addr[1:0]` — Endereço do neurônio que disparou |
| `uo_out[6:3]` | Saída | `spike_cnt[3:0]` — Contador de telemetria de spikes (módulo 16) |
| `uo_out[7]` | Saída | `core_en` — Status de operação do núcleo |
| `uio[7:0]` | Bidirecional | Mantidos em entrada / alta impedância (`uio_oe = 8'h00`, `uio_out = 8'h00`) |

## Resumo de Síntese e Place & Route

| Alvo / Ferramenta | Top Module | Recursos / Ocupação | Frequência Máx. | Artefatos |
| :--- | :--- | :--- | :--- | :--- |
| **ASIC (Yosys)** | `tt_um_neurochip_snn` | 1689 células, 172 FFs | 50 MHz (nominal) | `build/synth_tt.rpt` |
| **ASIC (Yosys)** | `snn_multilayer` | 3302 células, 328 FFs | — | `build/synth_multi.rpt` |
| **FPGA iCE40-HX1K** | `tt_um_neurochip_snn` | 572 `SB_LUT4`, 286 `SB_CARRY`, 759/1280 LC (`59%`) | 95.05 MHz (pós-PnR) | `build/neurochip_ice40.json`, `build/neurochip_ice40.bin`, `build/pnr_ice40.rpt` |
| **FPGA ECP5-25F** | `tt_um_neurochip_snn` | 408 `LUT4`, 164 `CCU2C`, 172 `TRELLIS_FF`, 902 `TRELLIS_COMB` (`3%`) | 102.52 MHz (pós-PnR) | `build/neurochip_ecp5.json`, `build/neurochip_ecp5.bit`, `build/pnr_ecp5.rpt` |

## Execução Unificada (`./neurochip_snn.sh`)

    ./neurochip_snn.sh help          # Lista todos os comandos disponíveis
    ./neurochip_snn.sh sim-all       # Roda pytest + sim-top, sim-real, sim-multi, sim-corner e sim-tt
    ./neurochip_snn.sh synth-fpga    # Sintetiza para Lattice iCE40 e ECP5 no Yosys
    ./neurochip_snn.sh synth-all     # Executa sínteses ASIC + FPGA e salva build/*.rpt
    ./neurochip_snn.sh pnr-ice40     # Place & Route (iCE40-HX1K) + gera build/neurochip_ice40.bin
    ./neurochip_snn.sh pnr-ecp5      # Place & Route (ECP5-25F) + gera build/neurochip_ecp5.bit
    ./neurochip_snn.sh pnr-all       # Executa Place & Route + bitstreams para iCE40 e ECP5
    ./neurochip_snn.sh ci            # Pipeline completo (sim-all + synth-all)
    ./neurochip_snn.sh dashboard     # Abre o painel interativo em Streamlit (tema escuro)
    ./neurochip_snn.sh clean         # Limpa artefatos temporários em build/

## Dashboard Interativo (`sim/dashboard_snn.py`)

Configurado com tema escuro técnico em `.streamlit/config.toml` e barra lateral de controle, organizado em **5 abas**:
1. **Sinal Elétrico & Spikes AER:** Sinal de referência (60 Hz + janela sombreada de surto nos ciclos 80-120), *raster plot* de spikes AER e distribuição por neurônio.
2. **Rede Multicamada (L1 vs L2):** Propagação de disparos entre camada oculta (`L1`) e saída (`L2`) com gráfico de barras e *heatmap* binário.
3. **Síntese ASIC & FPGA (Yosys):** Comparativo de células/fios, barras de ocupação em placas FPGA reais (`iCE40-HX1K`, `iCE40-UP5K`, `ECP5-25F`) e relatórios brutos.
4. **Hardware & Produção Externa:** Alternância entre visualização de hardware em placa Tiny Tapeout (`docs/hardware_render.png`) e diagrama de pinos/*floorplan*, tabela de ocupação em placas FPGAs e download dos arquivos de configuração/netlists.
5. **Prototipagem (FPGA & Tiny Tapeout):** Métricas de `Fmax` pós-PnR, diagrama esquemático de montagem em bancada, lista de componentes (BOM), passo a passo de validação física, checklist de artefatos e download direto dos bitstreams.

## Pinagem Física FPGA (`fpga/`)

- `fpga/constraints_ice40.pcf`: mapeamento de referência para **Lattice iCE40-HX1K (TQ144 / iCEstick)**.
- `fpga/constraints_ecp5.lpf`: mapeamento de referência para **Lattice ECP5-25F (CABGA381 / ULX3S)**.

## Tiny Tapeout & CI/CD

- **Metadados e documentação:** `info.yaml` e `docs/info.md`.
- **Configuração física (OpenLane / Sky130):** `rtl/config.json` (`161.0 x 111.52 µm`, `50 MHz`).
- **Workflows do GitHub Actions:**
  - `.github/workflows/ci.yml`: executa `./neurochip_snn.sh sim-all` e `./neurochip_snn.sh synth-all` em pushes/PRs na `main` e publica os relatórios do Yosys.
  - `.github/workflows/gds.yml`: workflow manual (`workflow_dispatch`) para geração de GDSII via OpenLane/Docker.
