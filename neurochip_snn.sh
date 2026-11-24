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
  sim-all     Executa todas as validações Python e simulações RTL
  synth-tt    Sintetiza tt_um_neurochip_snn no Yosys e salva relatório
  synth-multi Sintetiza snn_multilayer no Yosys e salva relatório
  synth-all   Executa todas as sínteses no Yosys
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
    sim-all)
        "$0" pytest
        "$0" sim-top
        "$0" sim-real
        "$0" sim-multi
        "$0" sim-corner
        ;;
    synth-tt)
        mkdir -p build
        yosys -p "read_verilog rtl/lif_neuron.v rtl/stdp_synapse.v rtl/snn_layer.v rtl/aer_top.v rtl/tt_um_neurochip_snn.v; synth -top tt_um_neurochip_snn; stat" | tee build/synth_tt.rpt
        ;;
    synth-multi)
        mkdir -p build
        yosys -p "read_verilog rtl/lif_neuron.v rtl/stdp_synapse.v rtl/snn_layer.v rtl/snn_multilayer.v; synth -top snn_multilayer; stat" | tee build/synth_multi.rpt
        ;;
    synth-all)
        "$0" synth-tt
        "$0" synth-multi
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
    *)
        echo "Comando desconhecido: $cmd"
        echo ""
        show_help
        exit 1
        ;;
esac
