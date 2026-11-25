#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

VENV_DIR="$PROJECT_DIR/.venv"
PYTHON_BIN="python3"
STREAMLIT_BIN="streamlit"
PYTEST_BIN="pytest"

if [ -x "$VENV_DIR/bin/python" ]; then
    PYTHON_BIN="$VENV_DIR/bin/python"
fi

if [ -x "$VENV_DIR/bin/streamlit" ]; then
    STREAMLIT_BIN="$VENV_DIR/bin/streamlit"
fi

if [ -x "$VENV_DIR/bin/pytest" ]; then
    PYTEST_BIN="$VENV_DIR/bin/pytest"
fi

show_help() {
    cat << 'USAGE'
Uso: ./neurochip_snn.sh <comando>

Comandos disponíveis:
  py          Valida o modelo Python / simulação STDP
  pytest      Executa a suíte de testes Python (pytest)
  sim-top     Simula o chip completo (AER + STDP)
  sim-real    Codifica sinal real e roda simulação Verilog
  sim-multi   Simula a rede neural multicamada (2 camadas)
  sim-corner  Executa testbench auto-verificável de corner cases
  sim-tt      Valida o wrapper Tiny Tapeout (pinout + telemetria)
  sim-all     Executa todas as validações Python e simulações RTL
  synth-tt    Sintetiza tt_um_neurochip_snn no Yosys e salva relatório
  synth-multi Sintetiza snn_multilayer no Yosys e salva relatório
  synth-ice40 Sintetiza tt_um_neurochip_snn para FPGA Lattice iCE40
  synth-ecp5  Sintetiza tt_um_neurochip_snn para FPGA Lattice ECP5
  synth-fpga  Executa sínteses FPGA (iCE40 + ECP5)
  synth-all   Executa todas as sínteses (ASIC + FPGA) no Yosys
  pnr-ice40   Place & Route (iCE40-HX1K) + bitstream .bin
  pnr-ecp5    Place & Route (ECP5-25F) + bitstream .bit
  pnr-all     Executa Place & Route + bitstreams (iCE40 + ECP5)
  ci          Executa o pipeline completo (sim-all + synth-all)
  dashboard   Abre o painel Streamlit (usa .venv se existir)
  clean       Limpa artefatos temporários em build/
  help        Exibe esta ajuda
USAGE
}

cmd="${1:-help}"

case "$cmd" in
    py)
        "$PYTHON_BIN" sim/sim_snn_stdp.py
        ;;
    pytest)
        if command -v "$PYTEST_BIN" >/dev/null 2>&1 || [ -x "$PYTEST_BIN" ]; then
            "$PYTEST_BIN" -v tests/
        else
            "$PYTHON_BIN" -m pytest -v tests/
        fi
        ;;
    sim-top)
        mkdir -p build
        iverilog -o build/sim_top rtl/*.v tb/tb_aer_top.v
        vvp build/sim_top
        ;;
    sim-real)
        mkdir -p build
        "$PYTHON_BIN" sim/encode_signal_aer.py
        iverilog -o build/sim_real rtl/*.v tb/tb_aer_real_signal.v
        vvp build/sim_real
        ;;
    sim-multi)
        mkdir -p build
        iverilog -o build/sim_multi rtl/lif_neuron.v rtl/stdp_synapse.v rtl/snn_layer.v rtl/snn_multilayer.v tb/tb_snn_multilayer.v
        vvp build/sim_multi
        ;;
    sim-corner)
        mkdir -p build
        iverilog -o build/sim_corner rtl/lif_neuron.v rtl/stdp_synapse.v rtl/snn_layer.v rtl/snn_multilayer.v tb/tb_corner_cases.v
        vvp build/sim_corner
        ;;
    sim-tt)
        mkdir -p build
        iverilog -o build/sim_tt rtl/lif_neuron.v rtl/stdp_synapse.v rtl/snn_layer.v rtl/aer_top.v rtl/tt_um_neurochip_snn.v tb/tb_tt_um_neurochip_snn.v
        vvp build/sim_tt
        ;;
    sim-all)
        "$0" pytest
        "$0" sim-top
        "$0" sim-real
        "$0" sim-multi
        "$0" sim-corner
        "$0" sim-tt
        ;;
    synth-tt)
        mkdir -p build
        yosys -p "read_verilog rtl/lif_neuron.v rtl/stdp_synapse.v rtl/snn_layer.v rtl/aer_top.v rtl/tt_um_neurochip_snn.v; synth -top tt_um_neurochip_snn; stat" | tee build/synth_tt.rpt
        ;;
    synth-multi)
        mkdir -p build
        yosys -p "read_verilog rtl/lif_neuron.v rtl/stdp_synapse.v rtl/snn_layer.v rtl/snn_multilayer.v; synth -top snn_multilayer; stat" | tee build/synth_multi.rpt
        ;;
    synth-ice40)
        mkdir -p build
        yosys -p "read_verilog rtl/lif_neuron.v rtl/stdp_synapse.v rtl/snn_layer.v rtl/aer_top.v rtl/tt_um_neurochip_snn.v; synth_ice40 -top tt_um_neurochip_snn -json build/neurochip_ice40.json; stat" | tee build/synth_ice40.rpt
        ;;
    synth-ecp5)
        mkdir -p build
        yosys -p "read_verilog rtl/lif_neuron.v rtl/stdp_synapse.v rtl/snn_layer.v rtl/aer_top.v rtl/tt_um_neurochip_snn.v; synth_ecp5 -top tt_um_neurochip_snn -json build/neurochip_ecp5.json; stat" | tee build/synth_ecp5.rpt
        ;;
    synth-fpga)
        "$0" synth-ice40
        "$0" synth-ecp5
        ;;
    synth-all)
        "$0" synth-tt
        "$0" synth-multi
        "$0" synth-fpga
        ;;
    ci)
        "$0" sim-all
        "$0" synth-all
        ;;
    dashboard)
        "$STREAMLIT_BIN" run sim/dashboard_snn.py
        ;;
    clean)
        rm -rf build/*
        echo "Diretório build/ limpo."
        ;;
    help|-h|--help)
        show_help
        ;;
    pnr-ice40)
        "$0" synth-ice40
        PCF_ARG=""
        [ -f "fpga/constraints_ice40.pcf" ] && PCF_ARG="--pcf fpga/constraints_ice40.pcf --pcf-allow-unconstrained"
        nextpnr-ice40 --hx1k --package tq144 --json build/neurochip_ice40.json $PCF_ARG --asc build/neurochip_ice40.asc 2>&1 | tee build/pnr_ice40.rpt
        icepack build/neurochip_ice40.asc build/neurochip_ice40.bin
        echo "Bitstream gerado em build/neurochip_ice40.bin"
        ;;
    pnr-ecp5)
        "$0" synth-ecp5
        LPF_ARG=""
        [ -f "fpga/constraints_ecp5.lpf" ] && LPF_ARG="--lpf fpga/constraints_ecp5.lpf --lpf-allow-unconstrained"
        nextpnr-ecp5 --25k --package CABGA381 --json build/neurochip_ecp5.json $LPF_ARG --textcfg build/neurochip_ecp5.config 2>&1 | tee build/pnr_ecp5.rpt
        ecppack --compress build/neurochip_ecp5.config build/neurochip_ecp5.bit
        echo "Bitstream gerado em build/neurochip_ecp5.bit"
        ;;
    pnr-all)
        "$0" pnr-ice40
        "$0" pnr-ecp5
        ;;
    *)
        echo "Comando desconhecido: $cmd"
        echo ""
        show_help
        exit 1
        ;;
esac
