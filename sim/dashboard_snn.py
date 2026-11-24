import math
import re
import subprocess
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

st.set_page_config(page_title="NeuroChip SNN — Monitor de Spikes", layout="wide")
st.title("NeuroChip SNN — Análise de Sinal Elétrico e Disparos AER")

col_ctrl1, col_ctrl2 = st.columns([1, 3])
with col_ctrl1:
    run_btn = st.button("Executar Simulação Verilog (make real_sim)", type="primary")

def run_verilog_sim():
    proc = subprocess.run(
        ["make", "real_sim"],
        capture_output=True,
        text=True,
        check=False
    )
    spikes = []
    pattern = re.compile(r"ciclo=\s*(\d+)\s*\|\s*t=(\d+)\s*\|\s*SPIKE AER OUT -> Neuronio\s*(\d+)")
    for line in proc.stdout.splitlines():
        m = pattern.search(line)
        if m:
            spikes.append({
                "ciclo": int(m.group(1)),
                "tempo_ps": int(m.group(2)),
                "neuronio": int(m.group(3))
            })
    return pd.DataFrame(spikes), proc.stdout, proc.stderr

def build_reference_signal(num_samples=200):
    rows = []
    for n in range(num_samples):
        val = math.sin(2 * math.pi * n / 40.0)
        if 80 <= n <= 120:
            val += 0.9 * math.sin(2 * math.pi * n / 6.0)
        rows.append({"ciclo": n, "tensao_pu": val})
    return pd.DataFrame(rows)

if run_btn or "sim_df" not in st.session_state:
    df_spikes, stdout_log, stderr_log = run_verilog_sim()
    st.session_state["sim_df"] = df_spikes
    st.session_state["stdout_log"] = stdout_log
    st.session_state["stderr_log"] = stderr_log

df_spikes = st.session_state["sim_df"]
df_sig = build_reference_signal(200)

# Métricas principais
m1, m2, m3 = st.columns(3)
total_spikes = len(df_spikes)
transiente_spikes = len(df_spikes[(df_spikes["ciclo"] >= 80) & (df_spikes["ciclo"] <= 120)]) if total_spikes else 0
m1.metric("Total de Spikes AER", total_spikes)
m2.metric("Spikes durante o Transiente (t=80..120)", transiente_spikes)
m3.metric("Neurônios Ativos", df_spikes["neuronio"].nunique() if total_spikes else 0)

# Gráficos sincronizados (Sinal Elétrico + Raster Plot de Spikes)
fig = make_subplots(
    rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.08,
    subplot_titles=("Sinal Elétrico de Entrada (60 Hz + Surto Transiente)", "Disparos AER do Chip (Raster Plot)")
)

fig.add_trace(
    go.Scatter(x=df_sig["ciclo"], y=df_sig["tensao_pu"], mode="lines", name="Sinal (pu)", line=dict(color="#1f77b4")),
    row=1, col=1
)
fig.add_vrect(x0=80, x1=120, fillcolor="red", opacity=0.12, line_width=0, row=1, col=1)

if total_spikes > 0:
    fig.add_trace(
        go.Scatter(
            x=df_spikes["ciclo"],
            y=df_spikes["neuronio"],
            mode="markers",
            name="Spike AER",
            marker=dict(size=9, symbol="line-ns-open", line=dict(width=2, color="#d62728"))
        ),
        row=2, col=1
    )

fig.update_yaxes(title_text="Amplitude (pu)", row=1, col=1)
fig.update_yaxes(title_text="ID do Neurônio", tickvals=[0, 1, 2, 3], row=2, col=1)
fig.update_xaxes(title_text="Ciclo de Clock", row=2, col=1)
fig.update_layout(height=580, template="plotly_white", showlegend=False)

st.plotly_chart(fig, use_container_width=True)

with st.expander("Log bruto da simulação (Icarus Verilog)"):
    st.code(st.session_state["stdout_log"], language="text")