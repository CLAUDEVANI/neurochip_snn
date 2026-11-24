import math
import re
import subprocess
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = str(ROOT / "neurochip_snn.sh")

st.set_page_config(page_title="NeuroChip SNN — Monitor Neuromórfico", layout="wide")
st.title("NeuroChip SNN — Monitor de Spikes, Multicamada e Síntese ASIC")


def run_cmd(arg: str):
    return subprocess.run(
        [SCRIPT, arg],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def run_real_sim():
    proc = run_cmd("sim-real")
    spikes = []
    pattern = re.compile(r"ciclo=\s*(\d+)\s*\|\s*t=(\d+)\s*\|\s*SPIKE AER OUT -> Neuronio\s*(\d+)")
    for line in proc.stdout.splitlines():
        m = pattern.search(line)
        if m:
            spikes.append({
                "ciclo": int(m.group(1)),
                "tempo_ps": int(m.group(2)),
                "neuronio": int(m.group(3)),
            })
    return pd.DataFrame(spikes), proc.stdout, proc.stderr


def run_multi_sim():
    proc = run_cmd("sim-multi")
    rows = []
    pattern = re.compile(r"t=(\d+)\s*\|\s*L1\(oculta\)=([01]{4})\s*\|\s*L2\(saida\)=([01]{4})")
    for line in proc.stdout.splitlines():
        m = pattern.search(line)
        if m:
            l1, l2 = m.group(2), m.group(3)
            rows.append({
                "tempo_ps": int(m.group(1)),
                "L1_bits": l1,
                "L2_bits": l2,
                "L1_spikes": l1.count("1"),
                "L2_spikes": l2.count("1"),
            })
    return pd.DataFrame(rows), proc.stdout, proc.stderr


def build_reference_signal(num_samples=200):
    rows = []
    for n in range(num_samples):
        val = math.sin(2 * math.pi * n / 40.0)
        if 80 <= n <= 120:
            val += 0.9 * math.sin(2 * math.pi * n / 6.0)
        rows.append({"ciclo": n, "tensao_pu": val})
    return pd.DataFrame(rows)


tab1, tab2, tab3 = st.tabs([
    "Sinal Elétrico & Spikes AER",
    "Rede Multicamada (L1 vs L2)",
    "Síntese ASIC (Yosys)",
])

with tab1:
    if st.button("Executar Simulação AER (sim-real)", type="primary") or "real_df" not in st.session_state:
        df_s, out_s, err_s = run_real_sim()
        st.session_state["real_df"] = df_s
        st.session_state["real_log"] = out_s + ("\n" + err_s if err_s else "")

    df_spikes = st.session_state["real_df"]
    df_sig = build_reference_signal()

    c1, c2, c3 = st.columns(3)
    c1.metric("Total de Spikes AER", len(df_spikes))
    c2.metric("Neurônios Ativos", df_spikes["neuronio"].nunique() if not df_spikes.empty else 0)
    c3.metric("Taxa Média (spikes/200 ciclos)", f"{len(df_spikes)/200:.2f}")

    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.1,
        subplot_titles=("Sinal Elétrico de Referência (60 Hz + Surto)", "Raster Plot de Spikes AER"),
    )
    fig.add_trace(go.Scatter(x=df_sig["ciclo"], y=df_sig["tensao_pu"], mode="lines", name="Tensão (pu)"), row=1, col=1)
    if not df_spikes.empty:
        fig.add_trace(
            go.Scatter(
                x=df_spikes["ciclo"], y=df_spikes["neuronio"],
                mode="markers", marker=dict(size=9, symbol="line-ns-open", line=dict(width=2)),
                name="Spikes AER",
            ),
            row=2, col=1,
        )
    fig.update_yaxes(title_text="pu", row=1, col=1)
    fig.update_yaxes(title_text="Neurônio", dtick=1, row=2, col=1)
    fig.update_xaxes(title_text="Ciclo", row=2, col=1)
    fig.update_layout(height=520)
    st.plotly_chart(fig, use_container_width=True)

    if not df_spikes.empty:
        counts = df_spikes["neuronio"].value_counts().sort_index()
        st.bar_chart(counts)

    with st.expander("Log bruto da simulação AER"):
        st.code(st.session_state["real_log"], language="text")

with tab2:
    if st.button("Executar Simulação Multicamada (sim-multi)", type="primary") or "multi_df" not in st.session_state:
        df_m, out_m, err_m = run_multi_sim()
        st.session_state["multi_df"] = df_m
        st.session_state["multi_log"] = out_m + ("\n" + err_m if err_m else "")

    df_m = st.session_state["multi_df"]
    m1, m2 = st.columns(2)
    m1.metric("Disparos na Camada Oculta (L1)", int(df_m["L1_spikes"].sum()) if not df_m.empty else 0)
    m2.metric("Disparos na Camada de Saída (L2)", int(df_m["L2_spikes"].sum()) if not df_m.empty else 0)

    if not df_m.empty:
        fig_m = go.Figure()
        fig_m.add_trace(go.Bar(x=df_m["tempo_ps"], y=df_m["L1_spikes"], name="L1 (Oculta)"))
        fig_m.add_trace(go.Bar(x=df_m["tempo_ps"], y=df_m["L2_spikes"], name="L2 (Saída)"))
        fig_m.update_layout(
            barmode="group",
            title="Propagação de Spikes: L1 (Oculta) vs L2 (Saída)",
            xaxis_title="Tempo (ps)",
            yaxis_title="Quantidade de Neurônios Disparando",
            height=420,
        )
        st.plotly_chart(fig_m, use_container_width=True)

    with st.expander("Log bruto da simulação Multicamada"):
        st.code(st.session_state["multi_log"], language="text")

with tab3:
    if st.button("Rodar Síntese Yosys (synth-all)"):
        run_cmd("synth-all")

    for label, fname in [("Tiny Tapeout (tt_um_neurochip_snn)", "synth_tt.rpt"), ("Multicamada (snn_multilayer)", "synth_multi.rpt")]:
        rpt = ROOT / "build" / fname
        st.subheader(label)
        if rpt.exists():
            txt = rpt.read_text(errors="ignore")
            m_cells = re.findall(r"Number of cells:\s+(\d+)", txt)
            m_wires = re.findall(r"Number of wires:\s+(\d+)", txt)
            if m_cells and m_wires:
                col_a, col_b = st.columns(2)
                col_a.metric("Total de Células Lógicas", m_cells[-1])
                col_b.metric("Total de Fios (Wires)", m_wires[-1])
            with st.expander(f"Ver relatório completo ({fname})"):
                st.code(txt[-4000:], language="text")
        else:
            st.info(f"Relatório `build/{fname}` ainda não gerado. Clique no botão acima ou rode `./neurochip_snn.sh synth-all`.")
