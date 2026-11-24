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
st.title("NeuroChip SNN — Monitor de Spikes, Síntese ASIC/FPGA e Produção de Hardware")


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


def parse_yosys_report(path: Path):
    if not path.exists():
        return None
    txt = path.read_text(errors="ignore")
    cells_m = re.findall(r"Number of cells:\s+(\d+)", txt)
    wires_m = re.findall(r"Number of wires:\s+(\d+)", txt)

    def count_prim(name: str):
        matches = re.findall(rf"^\s+{re.escape(name)}\s+(\d+)\s*$", txt, re.MULTILINE)
        return int(matches[-1]) if matches else 0

    return {
        "cells": int(cells_m[-1]) if cells_m else 0,
        "wires": int(wires_m[-1]) if wires_m else 0,
        "SB_LUT4": count_prim("SB_LUT4"),
        "SB_CARRY": count_prim("SB_CARRY"),
        "SB_DFF": count_prim("SB_DFFER") + count_prim("SB_DFFES") + count_prim("SB_DFFR") + count_prim("SB_DFF"),
        "LUT4": count_prim("LUT4"),
        "CCU2C": count_prim("CCU2C"),
        "PFUMX": count_prim("PFUMX"),
        "TRELLIS_FF": count_prim("TRELLIS_FF"),
        "raw": txt,
    }


tab1, tab2, tab3, tab4 = st.tabs([
    "Sinal Elétrico & Spikes AER",
    "Rede Multicamada (L1 vs L2)",
    "Síntese ASIC & FPGA (Yosys)",
    "Hardware & Produção Externa",
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
    col_b1, col_b2 = st.columns(2)
    with col_b1:
        if st.button("Rodar Todas as Sínteses (ASIC + FPGA)", type="primary"):
            run_cmd("synth-all")
    with col_b2:
        if st.button("Rodar Apenas Sínteses FPGA (iCE40 + ECP5)"):
            run_cmd("synth-fpga")

    r_tt = parse_yosys_report(ROOT / "build" / "synth_tt.rpt")
    r_multi = parse_yosys_report(ROOT / "build" / "synth_multi.rpt")
    r_ice40 = parse_yosys_report(ROOT / "build" / "synth_ice40.rpt")
    r_ecp5 = parse_yosys_report(ROOT / "build" / "synth_ecp5.rpt")

    summary_rows = []
    if r_tt:
        summary_rows.append({"Alvo": "ASIC — tt_um_neurochip_snn", "Células": r_tt["cells"], "Wires": r_tt["wires"]})
    if r_multi:
        summary_rows.append({"Alvo": "ASIC — snn_multilayer", "Células": r_multi["cells"], "Wires": r_multi["wires"]})
    if r_ice40:
        summary_rows.append({"Alvo": "FPGA — Lattice iCE40", "Células": r_ice40["cells"], "Wires": r_ice40["wires"]})
    if r_ecp5:
        summary_rows.append({"Alvo": "FPGA — Lattice ECP5", "Células": r_ecp5["cells"], "Wires": r_ecp5["wires"]})

    if summary_rows:
        df_sum = pd.DataFrame(summary_rows)
        fig_cmp = go.Figure()
        fig_cmp.add_trace(go.Bar(x=df_sum["Alvo"], y=df_sum["Células"], name="Células"))
        fig_cmp.add_trace(go.Bar(x=df_sum["Alvo"], y=df_sum["Wires"], name="Wires"))
        fig_cmp.update_layout(
            barmode="group",
            title="Comparativo Geral de Síntese (ASIC vs. FPGA)",
            yaxis_title="Quantidade",
            height=380,
        )
        st.plotly_chart(fig_cmp, use_container_width=True)

    st.subheader("Recursos Detalhados em FPGA")
    fpga_col1, fpga_col2 = st.columns(2)

    with fpga_col1:
        st.markdown("**Lattice iCE40 (`tt_um_neurochip_snn`)**")
        if r_ice40:
            i1, i2, i3 = st.columns(3)
            i1.metric("SB_LUT4", r_ice40["SB_LUT4"])
            i2.metric("Flip-Flops", r_ice40["SB_DFF"])
            i3.metric("SB_CARRY", r_ice40["SB_CARRY"])
            fig_i = go.Figure(go.Bar(
                x=["SB_LUT4", "SB_CARRY", "Flip-Flops"],
                y=[r_ice40["SB_LUT4"], r_ice40["SB_CARRY"], r_ice40["SB_DFF"]],
                text=[r_ice40["SB_LUT4"], r_ice40["SB_CARRY"], r_ice40["SB_DFF"]],
                textposition="auto",
            ))
            fig_i.update_layout(title="Distribuição de Primitivas — iCE40", height=320)
            st.plotly_chart(fig_i, use_container_width=True)
        else:
            st.info("Rode `./neurochip_snn.sh synth-ice40` para gerar as métricas.")

    with fpga_col2:
        st.markdown("**Lattice ECP5 (`tt_um_neurochip_snn`)**")
        if r_ecp5:
            e1, e2, e3 = st.columns(3)
            e1.metric("LUT4", r_ecp5["LUT4"])
            e2.metric("TRELLIS_FF", r_ecp5["TRELLIS_FF"])
            e3.metric("CCU2C + PFUMX", r_ecp5["CCU2C"] + r_ecp5["PFUMX"])
            fig_e = go.Figure(go.Bar(
                x=["LUT4", "TRELLIS_FF", "CCU2C", "PFUMX"],
                y=[r_ecp5["LUT4"], r_ecp5["TRELLIS_FF"], r_ecp5["CCU2C"], r_ecp5["PFUMX"]],
                text=[r_ecp5["LUT4"], r_ecp5["TRELLIS_FF"], r_ecp5["CCU2C"], r_ecp5["PFUMX"]],
                textposition="auto",
            ))
            fig_e.update_layout(title="Distribuição de Primitivas — ECP5", height=320)
            st.plotly_chart(fig_e, use_container_width=True)
        else:
            st.info("Rode `./neurochip_snn.sh synth-ecp5` para gerar as métricas.")

    for label, rpt_obj in [
        ("Relatório ASIC — tt_um_neurochip_snn", r_tt),
        ("Relatório ASIC — snn_multilayer", r_multi),
        ("Relatório FPGA — Lattice iCE40", r_ice40),
        ("Relatório FPGA — Lattice ECP5", r_ecp5),
    ]:
        if rpt_obj:
            with st.expander(label):
                st.code(rpt_obj["raw"][-3500:], language="text")

with tab4:
    st.subheader("Visualização do Chip — `tt_um_neurochip_snn` (Tiny Tapeout 1x1)")

    h1, h2, h3, h4 = st.columns(4)
    h1.metric("Processo Alvo", "Sky130 (130 nm)")
    h2.metric("Área do Tile (1x1)", "161.0 × 111.52 µm")
    h3.metric("Clock Nominal", "50 MHz (20 ns)")
    h4.metric("Top Module", "tt_um_neurochip_snn")

    # Diagrama visual simplificado do chip e pinout
    fig_chip = go.Figure()
    fig_chip.add_shape(type="rect", x0=2, y0=1, x1=8, y1=9, line=dict(width=3), fillcolor="rgba(30, 136, 229, 0.12)")
    fig_chip.add_annotation(x=5, y=6.8, text="<b>tt_um_neurochip_snn</b>", showarrow=False, font=dict(size=16))
    fig_chip.add_annotation(x=5, y=5.4, text="aer_top → snn_layer<br>4× LIF Neuron + 8× STDP Synapse<br>+ Telemetria spike_cnt[3:0]", showarrow=False, font=dict(size=12))
    fig_chip.add_annotation(x=5, y=2.5, text="1689 células ASIC | 172 FFs | 50 MHz", showarrow=False, font=dict(size=11))

    left_pins = [
        (8.0, "clk (50 MHz)"),
        (7.0, "rst_n (ativo baixo)"),
        (6.0, "ena (chip select)"),
        (4.8, "ui_in[0]: en"),
        (3.8, "ui_in[1]: aer_in_valid"),
        (2.8, "ui_in[2]: aer_in_addr"),
    ]
    right_pins = [
        (8.0, "uo_out[0]: aer_out_valid"),
        (6.8, "uo_out[2:1]: aer_out_addr"),
        (5.4, "uo_out[6:3]: spike_cnt[3:0]"),
        (4.0, "uo_out[7]: core_en"),
        (2.4, "uio[7:0]: Hi-Z (oe=0)"),
    ]
    for y, lbl in left_pins:
        fig_chip.add_shape(type="line", x0=1.2, y0=y, x1=2.0, y1=y, line=dict(width=2))
        fig_chip.add_annotation(x=1.1, y=y, text=lbl, xanchor="right", showarrow=False, font=dict(size=11))
    for y, lbl in right_pins:
        fig_chip.add_shape(type="line", x0=8.0, y0=y, x1=8.8, y1=y, line=dict(width=2))
        fig_chip.add_annotation(x=8.9, y=y, text=lbl, xanchor="left", showarrow=False, font=dict(size=11))

    fig_chip.update_xaxes(range=[0, 10], visible=False)
    fig_chip.update_yaxes(range=[0, 10], visible=False)
    fig_chip.update_layout(height=420, margin=dict(l=10, r=10, t=20, b=10))
    st.plotly_chart(fig_chip, use_container_width=True)

    st.subheader("Estimativa de Ocupação em Placas FPGA Reais")
    ice_luts = r_ice40["SB_LUT4"] if r_ice40 else 572
    ecp_luts = r_ecp5["LUT4"] if r_ecp5 else 408
    df_boards = pd.DataFrame([
        {"Placa / FPGA": "Lattice iCE40-HX1K", "LUTs Disponíveis": 1280, "LUTs Usadas": ice_luts, "Ocupação (%)": round(100 * ice_luts / 1280, 1)},
        {"Placa / FPGA": "Lattice iCE40-UP5K (UPduino)", "LUTs Disponíveis": 5280, "LUTs Usadas": ice_luts, "Ocupação (%)": round(100 * ice_luts / 5280, 1)},
        {"Placa / FPGA": "Lattice ECP5-25F (ULX3S / OrangeCrab)", "LUTs Disponíveis": 24288, "LUTs Usadas": ecp_luts, "Ocupação (%)": round(100 * ecp_luts / 24288, 1)},
    ])
    st.dataframe(df_boards, use_container_width=True, hide_index=True)

    st.subheader("Produção Externa (Tiny Tapeout GDSII & Bitstream FPGA)")
    p1, p2 = st.columns(2)

    with p1:
        st.markdown("**1. Fabricação ASIC (Tiny Tapeout / Sky130)**")
        st.markdown(
            "- Metadados oficiais: `info.yaml` e `docs/info.md`\n"
            "- Configuração OpenLane: `rtl/config.json` (1×1 tile, 50 MHz)\n"
            "- Workflow GDSII: `.github/workflows/gds.yml` (disparo manual na aba *Actions*)"
        )
        for fname in ["info.yaml", "rtl/config.json", "docs/info.md"]:
            fpath = ROOT / fname
            if fpath.exists():
                st.download_button(
                    label=f"Baixar {fname}",
                    data=fpath.read_bytes(),
                    file_name=fpath.name,
                    key=f"dl_{fname}",
                )

    with p2:
        st.markdown("**2. Prototipagem Física em FPGA (Netlists JSON)**")
        st.markdown(
            "- Netlists prontos para Place & Route (`nextpnr-ice40` / `nextpnr-ecp5`)\n"
            "- Geração de bitstream com `icepack` (iCE40) ou `ecppack` (ECP5)"
        )
        for fname in ["build/neurochip_ice40.json", "build/neurochip_ecp5.json"]:
            fpath = ROOT / fname
            if fpath.exists():
                st.download_button(
                    label=f"Baixar {fpath.name}",
                    data=fpath.read_bytes(),
                    file_name=fpath.name,
                    key=f"dl_{fpath.name}",
                )
            else:
                st.caption(f"`{fname}` ainda não gerado (rode `./neurochip_snn.sh synth-fpga`).")
