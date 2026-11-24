#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

VENV_DIR="$PROJECT_DIR/.venv"
PYTHON_BIN="python3"
STREAMLIT_BIN="streamlit"

if [ -x "$VENV_DIR/bin/python" ]; then
    PYTHON_BIN="$VENV_DIR/bin/python"
fi

if [ -x "$VENV_DIR/bin/streamlit" ]; then
    STREAMLIT_BIN="$VENV_DIR/bin/streamlit"
fi

show_help() {
    cat << 'USAGE'
Uso: ./neurochip_snn.sh <comando>

Comandos disponíveis:
  py          Valida o modelo Python / simulação STDP
  sim-top     Simula o chip completo (AER + STDP)
  sim-real    Codifica sinal real e roda simulação Verilog
  sim-multi   Simula a rede neural multicamada (2 camadas)
  sim-all     Executa todas as validações e simulações
  synth-tt    Sintetiza tt_um_neurochip_snn no Yosys
  synth-multi Sintetiza snn_multilayer no Yosys
  synth-all   Executa todas as sínteses no Yosys
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
    sim-all)
        "$0" py
        "$0" sim-top
        "$0" sim-real
        "$0" sim-multi
        ;;
    synth-tt)
        mkdir -p build
        yosys -p "read_verilog rtl/lif_neuron.v rtl/stdp_synapse.v rtl/snn_layer.v rtl/aer_top.v rtl/tt_um_neurochip_snn.v; synth -top tt_um_neurochip_snn; stat"
        ;;
    synth-multi)
        mkdir -p build
        yosys -p "read_verilog rtl/lif_neuron.v rtl/stdp_synapse.v rtl/snn_layer.v rtl/snn_multilayer.v; synth -top snn_multilayer; stat"
        ;;
    synth-all)
        "$0" synth-tt
        "$0" synth-multi
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
    *)
        echo "Comando desconhecido: $cmd"
        echo ""
        show_help
        exit 1
        ;;
esac
