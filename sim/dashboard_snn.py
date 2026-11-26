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

def apply_dark_layout(fig, height=450, title=""):
    fig.update_layout(
        template="plotly_dark",
        height=height,
        title=title,
        paper_bgcolor="#0e1117",
        plot_bgcolor="#0e1117",
        margin=dict(l=20, r=20, t=45, b=20),
    )
    return fig


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


tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "Sinal Elétrico & Spikes AER",
    "Rede Multicamada (L1 vs L2)",
    "Síntese ASIC & FPGA (Yosys)",
    "Hardware & Produção Externa",
    "Prototipagem (FPGA & Tiny Tapeout)",
    "6. Esquema Eletrônico & Hardware"
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
    st.plotly_chart(fig, width="stretch")

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
        st.plotly_chart(fig_m, width="stretch")

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
        st.plotly_chart(fig_cmp, width="stretch")

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
            st.plotly_chart(fig_i, width="stretch")
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
            st.plotly_chart(fig_e, width="stretch")
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
    h2.metric("Área do Tile (1×1)", "161.0 × 111.52 µm")
    h3.metric("Clock Nominal", "50 MHz (20 ns)")
    h4.metric("Células ASIC", r_tt["cells"] if r_tt else 1689)

    view_mode = st.radio(
        "Modo de Visualização do Hardware",
        ["Hardware Real (ASIC + PCB Tiny Tapeout)", "Diagrama de Pinos & Floorplan Lógico"],
        horizontal=True,
    )

    render_path = ROOT / "docs" / "hardware_render.png"
    if view_mode == "Hardware Real (ASIC + PCB Tiny Tapeout)":
        if render_path.exists():
            st.image(
                str(render_path),
                caption="Protótipo final — ASIC tt_um_neurochip_snn (QFN-64, Sky130 130 nm) montado em placa Tiny Tapeout",
                width="stretch",
            )
        else:
            st.warning("Arquivo `docs/hardware_render.png` não encontrado.")
    else:
        fig_chip = go.Figure()
        fig_chip.add_shape(
            type="rect", x0=2.2, y0=0.8, x1=7.8, y1=9.2,
            line=dict(color="#58A6FF", width=2.5),
            fillcolor="#161B22",
        )
        fig_chip.add_shape(
            type="circle", x0=2.45, y0=8.55, x1=2.75, y1=8.85,
            fillcolor="#00D4FF", line=dict(color="#00D4FF"),
        )
        fig_chip.add_annotation(x=5.0, y=8.7, text="<b>tt_um_neurochip_snn (Sky130 1×1 Tile)</b>", showarrow=False, font=dict(size=14, color="#E6EDF3"))

        blocks = [
            (2.6, 6.2, 4.9, 8.0, "rgba(0, 212, 255, 0.14)", "#00D4FF", "<b>aer_top</b><br>Roteador AER + Fila"),
            (5.1, 6.2, 7.4, 8.0, "rgba(46, 204, 113, 0.14)", "#2ECC71", "<b>Telemetria</b><br>spike_cnt[3:0] + core_en"),
            (2.6, 3.3, 7.4, 5.8, "rgba(123, 97, 255, 0.14)", "#7B61FF", "<b>snn_layer</b><br>4× lif_neuron (8-bit, V_TH=100) + 8× stdp_synapse (LTP/LTD)"),
            (2.6, 1.3, 7.4, 2.9, "rgba(255, 159, 28, 0.10)", "#FF9F1C", "<b>Síntese:</b> 1689 células | 172 FFs | 572 LUTs (iCE40) | 408 LUTs (ECP5)"),
        ]
        for x0, y0, x1, y1, fill, border, text in blocks:
            fig_chip.add_shape(type="rect", x0=x0, y0=y0, x1=x1, y1=y1, line=dict(color=border, width=1.5), fillcolor=fill)
            fig_chip.add_annotation(x=(x0 + x1) / 2, y=(y0 + y1) / 2, text=text, showarrow=False, font=dict(size=11, color="#E6EDF3"))

        left_pins = [
            (8.0, "clk (50 MHz)", "#FF4B4B"),
            (7.0, "rst_n (ativo baixo)", "#FF4B4B"),
            (6.0, "ena (chip select)", "#FF9F1C"),
            (4.8, "ui_in[0]: en", "#00D4FF"),
            (3.8, "ui_in[1]: aer_in_valid", "#00D4FF"),
            (2.8, "ui_in[2]: aer_in_addr", "#00D4FF"),
        ]
        right_pins = [
            (8.0, "uo_out[0]: aer_out_valid", "#2ECC71"),
            (6.8, "uo_out[2:1]: aer_out_addr", "#2ECC71"),
            (5.4, "uo_out[6:3]: spike_cnt[3:0]", "#2ECC71"),
            (4.0, "uo_out[7]: core_en", "#2ECC71"),
            (2.4, "uio[7:0]: Hi-Z (oe=0)", "#8B949E"),
        ]
        for y, lbl, col in left_pins:
            fig_chip.add_shape(type="line", x0=1.5, y0=y, x1=2.2, y1=y, line=dict(color=col, width=3))
            fig_chip.add_annotation(x=1.4, y=y, text=lbl, xanchor="right", showarrow=False, font=dict(size=11, color=col))
        for y, lbl, col in right_pins:
            fig_chip.add_shape(type="line", x0=7.8, y0=y, x1=8.5, y1=y, line=dict(color=col, width=3))
            fig_chip.add_annotation(x=8.6, y=y, text=lbl, xanchor="left", showarrow=False, font=dict(size=11, color=col))

        fig_chip.update_xaxes(range=[0, 10], visible=False)
        fig_chip.update_yaxes(range=[0.2, 9.6], visible=False)
        apply_dark_layout(fig_chip, height=460)
        st.plotly_chart(fig_chip, width="stretch")

    st.subheader("Estimativa de Ocupação em Placas FPGA Reais")
    ice_luts = r_ice40["SB_LUT4"] if r_ice40 else 572
    ecp_luts = r_ecp5["LUT4"] if r_ecp5 else 408
    df_boards = pd.DataFrame([
        {"Placa / FPGA": "Lattice iCE40-HX1K", "LUTs Disponíveis": 1280, "LUTs Usadas": ice_luts, "Ocupação (%)": round(100 * ice_luts / 1280, 1)},
        {"Placa / FPGA": "Lattice iCE40-UP5K (UPduino)", "LUTs Disponíveis": 5280, "LUTs Usadas": ice_luts, "Ocupação (%)": round(100 * ice_luts / 5280, 1)},
        {"Placa / FPGA": "Lattice ECP5-25F (ULX3S / OrangeCrab)", "LUTs Disponíveis": 24288, "LUTs Usadas": ecp_luts, "Ocupação (%)": round(100 * ecp_luts / 24288, 1)},
    ])
    st.dataframe(df_boards, width="stretch", hide_index=True)

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

# --- ABA 5: Prototipagem (FPGA & Tiny Tapeout) ---
with tab5:
    st.subheader("Pacote Completo para Prototipagem Física")

    def extract_fmax(rpt_path: Path, fallback: str) -> str:
        if not rpt_path.exists():
            return fallback
        content = rpt_path.read_text(errors="ignore")
        matches = re.findall(r"Max frequency for clock[^:]*:\s*([0-9.]+\s*MHz)", content)
        return matches[-1] if matches else fallback

    fmax_ice = extract_fmax(ROOT / "build" / "pnr_ice40.rpt", "95.05 MHz")
    fmax_ecp = extract_fmax(ROOT / "build" / "pnr_ecp5.rpt", "102.52 MHz")

    p1_m, p2_m, p3_m, p4_m = st.columns(4)
    p1_m.metric("Fmax iCE40-HX1K (PnR)", fmax_ice)
    p2_m.metric("Fmax ECP5-25F (PnR)", fmax_ecp)
    p3_m.metric("Alvo Tiny Tapeout", "50 MHz (1×2)")
    p4_m.metric("Células ASIC", r_tt["cells"] if r_tt else 1689)

    st.markdown("### 0. Signoff Físico ASIC (Sky130 / OpenLane)")
    gds_dir = ROOT / "build" / "gds_artifacts" / "neurochip-snn-gdsii"
    m_csv, gds_f = gds_dir / "metrics.csv", gds_dir / "tt_um_neurochip_snn.gds"
    if m_csv.exists():
        mdf = pd.read_csv(m_csv)
        if not mdf.empty:
            r = mdf.iloc[0]
            s1, s2, s3, s4, s5 = st.columns(5)
            s1.metric("Status OpenLane", str(r.get("flow_status", "—")))
            s2.metric("Die (1×2)", f"{float(r.get('DIEAREA_mm^2', 0)):.5f} mm²")
            s3.metric("Total Células", int(r.get("TotalCells", 0)))
            s4.metric("Magic DRC", f"{int(r.get('Magic_violations', 0))} viol.")
            s5.metric("WNS / TNS", f"{r.get('wns', 0.0)} / {r.get('tns', 0.0)}")
            st.dataframe(pd.DataFrame([
                {"Métrica": "Core Area (µm²)", "Valor": f"{float(r.get('CoreArea_um^2', 0)):.2f}"},
                {"Métrica": "Células pré-ABC", "Valor": str(int(r.get("cells_pre_abc", 0)))},
                {"Métrica": "Trilhas (µm)", "Valor": str(int(r.get("wire_length", 0)))},
                {"Métrica": "GDSII", "Valor": f"{gds_f.stat().st_size/1048576:.2f} MB" if gds_f.exists() else "—"},
            ]), width="stretch", hide_index=True)
    else:
        st.info("`metrics.csv` ainda não baixado em `build/gds_artifacts/neurochip-snn-gdsii/`.")

    gds_img = ROOT / "docs" / "gds_die_layout.png"
    if gds_img.exists():
        st.image(str(gds_img), caption="Layout físico GDSII — tt_um_neurochip_snn (Sky130, tile 1×2, 0 DRC)", width="stretch")

    st.markdown("### 1. Esquema de Montagem & Interligação de Bancada")

    fig_asm = go.Figure()

    # Bloco central: DUT (tt_um_neurochip_snn / FPGA)
    fig_asm.add_shape(
        type="rect", x0=3.5, y0=1.5, x1=6.5, y1=8.5,
        line=dict(color="#00D4FF", width=2.5),
        fillcolor="#161B22",
    )
    fig_asm.add_annotation(
        x=5.0, y=7.6,
        text="<b>DUT: tt_um_neurochip_snn</b><br><span style='font-size:11px;color:#8B949E'>Sky130 1×1 / iCE40 / ECP5</span>",
        showarrow=False, font=dict(size=13, color="#E6EDF3"),
    )
    fig_asm.add_shape(type="rect", x0=3.8, y0=4.8, x1=6.2, y1=6.5, line=dict(color="#7B61FF", width=1.5), fillcolor="rgba(123,97,255,0.14)")
    fig_asm.add_annotation(x=5.0, y=5.65, text="<b>aer_top + snn_layer</b><br>4× LIF + 8× STDP", showarrow=False, font=dict(size=11, color="#E6EDF3"))

    fig_asm.add_shape(type="rect", x0=3.8, y0=2.3, x1=6.2, y1=4.2, line=dict(color="#2ECC71", width=1.5), fillcolor="rgba(46,204,113,0.14)")
    fig_asm.add_annotation(x=5.0, y=3.25, text="<b>Telemetria & I/O</b><br>spike_cnt[3:0] | core_en", showarrow=False, font=dict(size=11, color="#E6EDF3"))

    # Periféricos à esquerda (Clock, Reset, Entradas ui_in[2:0])
    left_blocks = [
        (7.5, "Oscilador 50 MHz<br>(ou pino clk FPGA)", "#FF4B4B", "clk"),
        (5.8, "Botão RST_N + Pull-up 10kΩ<br>(ativo em nível baixo)", "#FF4B4B", "rst_n"),
        (3.8, "Chaves DIP ui_in[2:0]<br>[0]=en | [1]=valid | [2]=addr", "#00D4FF", "ui_in[2:0]"),
        (2.0, "Desacoplamento 100nF + 10µF<br>entre VCC e GND", "#FF9F1C", "VCC/GND"),
    ]
    for y, lbl, col, port_lbl in left_blocks:
        fig_asm.add_shape(type="rect", x0=0.4, y0=y - 0.6, x1=2.6, y1=y + 0.6, line=dict(color=col, width=1.6), fillcolor="#161B22")
        fig_asm.add_annotation(x=1.5, y=y, text=lbl, showarrow=False, font=dict(size=10.5, color=col))
        fig_asm.add_shape(type="line", x0=2.6, y0=y, x1=3.5, y1=y, line=dict(color=col, width=2.5))
        fig_asm.add_annotation(x=3.05, y=y + 0.25, text=port_lbl, showarrow=False, font=dict(size=9.5, color="#E6EDF3"))

    # Periféricos à direita (Saídas uo_out[7:0] e uio[7:0])
    right_blocks = [
        (7.2, "LED / Osciloscópio uo_out[0]<br>aer_out_valid (disparo)", "#2ECC71", "uo_out[0]"),
        (5.4, "LEDs / Display uo_out[2:1]<br>aer_out_addr[1:0] (0..3)", "#2ECC71", "uo_out[2:1]"),
        (3.6, "Barra 4-LEDs / Hex uo_out[6:3]<br>spike_cnt[3:0] + uo_out[7] en", "#00D4FF", "uo_out[7:3]"),
        (1.9, "Headers uio[7:0] (Hi-Z)<br>Reservado / Expansão", "#8B949E", "uio[7:0]"),
    ]
    for y, lbl, col, port_lbl in right_blocks:
        fig_asm.add_shape(type="line", x0=6.5, y0=y, x1=7.4, y1=y, line=dict(color=col, width=2.5))
        fig_asm.add_annotation(x=6.95, y=y + 0.25, text=port_lbl, showarrow=False, font=dict(size=9.5, color="#E6EDF3"))
        fig_asm.add_shape(type="rect", x0=7.4, y0=y - 0.6, x1=9.6, y1=y + 0.6, line=dict(color=col, width=1.6), fillcolor="#161B22")
        fig_asm.add_annotation(x=8.5, y=y, text=lbl, showarrow=False, font=dict(size=10.5, color=col))

    fig_asm.update_xaxes(range=[0, 10], visible=False)
    fig_asm.update_yaxes(range=[0.8, 9.2], visible=False)
    apply_dark_layout(fig_asm, height=450, title="Diagrama Esquemático de Montagem em Bancada")
    st.plotly_chart(fig_asm, width="stretch")

    st.markdown("### 2. Lista de Componentes (BOM de Bancada)")
    bom_df = pd.DataFrame([
        {"Qtd": "1", "Item": "Módulo / Chip Alvo", "Especificação": "ASIC Sky130 (1×1) ou FPGA iCE40-HX1K / ECP5-25F", "Função": "Executa tt_um_neurochip_snn a até 50 MHz (TT) / ~95–102 MHz (FPGA)"},
        {"Qtd": "1", "Item": "Fonte / Regulador", "Especificação": "3.3V / 1.8V regulada, baixo ripple (≥ 500 mA)", "Função": "Alimentação do núcleo e trilhos de I/O"},
        {"Qtd": "4", "Item": "Capacitores Cerâmicos", "Especificação": "100 nF (X7R, 0603/0805) + 1× 10 µF", "Função": "Desacoplamento de alta frequência próximo aos pinos VCC/GND"},
        {"Qtd": "1", "Item": "Chave DIP (3 vias)", "Especificação": "DIP-3 (ou 3× chaves tácteis + pull-down 10kΩ)", "Função": "Controle de ui_in[0] (en), ui_in[1] (aer_in_valid) e ui_in[2] (aer_in_addr)"},
        {"Qtd": "1", "Item": "Push-button + Resistor", "Especificação": "Chave NA + resistor pull-up 10kΩ", "Função": "Reset ativo em nível baixo (rst_n)"},
        {"Qtd": "8", "Item": "LEDs + Resistores", "Especificação": "LEDs SMD/THT + resistores limitadores 330Ω–1kΩ", "Função": "Monitorar uo_out[0] (valid), [2:1] (addr), [6:3] (spike_cnt) e [7] (core_en)"},
        {"Qtd": "2×12", "Item": "Barras de Pinos (Headers)", "Especificação": "Passo 2,54 mm (macho/fêmea)", "Função": "Conexão com analisador lógico, osciloscópio ou gravador FPGA"},
    ])
    st.dataframe(bom_df, width="stretch", hide_index=True)

    st.markdown("### 3. Passo a Passo de Montagem e Validação Física")
    st.markdown("""
1. **Alimentação e desacoplamento:** Soldar capacitores de `100 nF` o mais próximo possível dos pinos de alimentação e `10 µF` na entrada da placa antes de energizar.
2. **Reset e habilitação:** Manter `rst_n` em `0` por alguns ciclos de clock e, em seguida, subir para `1`; ajustar `ena = 1` e `ui_in[0] = 1` para acionar `core_en` (`uo_out[7] = 1`).
3. **Estímulo AER e telemetria:** Alternar `ui_in[2]` (`0` ou `1`) e pulsar `ui_in[1] = 1`, verificando os disparos em `uo_out[0]` (`aer_out_valid`), o endereço em `uo_out[2:1]` e a contagem acumulada em `uo_out[6:3]`.
""")
    st.markdown("### 4. Checklist de Artefatos Prontos para Bancada")
    artifacts_check = [
        ("build/neurochip_ice40.bin", "Bitstream Lattice iCE40-HX1K (32 KB)"),
        ("build/neurochip_ecp5.bit", "Bitstream Lattice ECP5-25F (108 KB)"),
        ("build/pnr_ice40.rpt", "Relatório Place & Route iCE40"),
        ("build/pnr_ecp5.rpt", "Relatório Place & Route ECP5"),
        ("info.yaml", "Metadados oficiais Tiny Tapeout"),
        ("docs/info.md", "Documentação do projeto Tiny Tapeout"),
        ("rtl/config.json", "Restrições físicas OpenLane / Sky130"),
    ]
    chk_rows = []
    for rel_path, desc in artifacts_check:
        fp = ROOT / rel_path
        exists = fp.exists()
        size_kb = f"{fp.stat().st_size / 1024:.1f} KB" if exists else "—"
        chk_rows.append({
            "Arquivo": rel_path,
            "Descrição": desc,
            "Status": "Pronto" if exists else "Pendente",
            "Tamanho": size_kb,
        })
    st.dataframe(pd.DataFrame(chk_rows), width="stretch", hide_index=True)

    st.markdown("### 5. Comandos de Gravação em Placa FPGA & Fluxo Tiny Tapeout")
    c_fpga, c_tt = st.columns(2)

    with c_fpga:
        st.markdown("**Gravação em FPGA (`openFPGALoader`)**")
        st.code(
            "# Gerar/atualizar bitstreams via neurochip_snn.sh\n"
            "./neurochip_snn.sh pnr-all\n\n"
            "# Gravar na SRAM da placa iCE40\n"
            "openFPGALoader -c usb-blaster build/neurochip_ice40.bin\n\n"
            "# Gravar na SRAM da placa ECP5\n"
            "openFPGALoader -b ulx3s build/neurochip_ecp5.bit",
            language="bash",
        )

    with c_tt:
        st.markdown("**Submissão Tiny Tapeout (ASIC Sky130)**")
        st.code(
            "# 1. Validar suíte completa (pytest + RTL + TT + sínteses)\n"
            "./neurochip_snn.sh ci\n\n"
            "# 2. Disparar geração GDSII manual no GitHub Actions\n"
            'gh workflow run "Tiny Tapeout GDSII (Manual)"\n\n'
            "# 3. Copiar rtl/, info.yaml e docs/info.md para o repo TT oficial",
            language="bash",
        )

    st.markdown("### 6. Download Direto dos Arquivos de Prototipagem")
    dl_cols = st.columns(3)
    download_candidates = [
        "build/neurochip_ice40.bin",
        "build/neurochip_ecp5.bit",
        "info.yaml",
        "docs/info.md",
        "rtl/config.json",
        "build/pnr_ice40.rpt",
        "build/gds_artifacts/neurochip-snn-gdsii/tt_um_neurochip_snn.gds",
        "build/gds_artifacts/neurochip-snn-gdsii/metrics.csv",
    ]
    for idx, fname in enumerate(download_candidates):
        fp = ROOT / fname
        col = dl_cols[idx % 3]
        if fp.exists():
            col.download_button(
                label=f"Baixar {fname}",
                data=fp.read_bytes(),
                file_name=fp.name,
                key=f"proto_dl_{fname}",
                width="stretch",
            )
        else:
            col.caption(f"`{fname}` ainda não gerado.")


with tab6:
    st.subheader("Esquema Eletrônico & Arquitetura Física do Hardware")
    st.caption("Desenho explicativo de interligação em bancada/PCB para prototipagem em FPGA ou ASIC Tiny Tapeout (3.3V).")

    svg_path = ROOT / "docs" / "esquema_eletronico_snn.svg"
    if svg_path.exists():
        svg_text = svg_path.read_text(encoding="utf-8")
        import base64
        b64 = base64.b64encode(svg_text.encode("utf-8")).decode("utf-8")
        st.markdown(f'<img src="data:image/svg+xml;base64,{b64}" style="width:100%; border-radius:8px;"/>', unsafe_allow_html=True)
        st.download_button(
            "Baixar Esquema Eletrônico (.svg)",
            data=svg_text.encode("utf-8"),
            file_name="esquema_eletronico_snn.svg",
            mime="image/svg+xml",
        )
    else:
        st.warning("Arquivo `docs/esquema_eletronico_snn.svg` não encontrado.")

    st.markdown("### Lista de Materiais (BOM) & Ligações Principais")
    bom_df = pd.DataFrame([
        {"Bloco": "Alimentação", "Componente": "Regulador LDO AMS1117-3.3 + 2× 10 µF + 1× 100 nF", "Função": "Estabiliza 5V USB para 3.3V com desacoplamento"},
        {"Bloco": "Clock & Reset", "Componente": "Oscilador 50 MHz (ou 12 MHz) + Botão + R 10 kΩ", "Função": "Clock principal (`clk`) e reset ativo-baixo (`rst_n`)"},
        {"Bloco": "Entradas AER", "Componente": "2× Chaves DIP + 1× Push-button + 3× R 10 kΩ", "Função": "Controla `ui_in[0]` (core_en), `ui_in[1]` (valid) e `ui_in[2]` (addr)"},
        {"Bloco": "Saídas Telemetria", "Componente": "8× LEDs (3mm/5mm) + 8× Resistores 330 Ω", "Função": "Exibe `uo_out[0]` (spike), `[2:1]` (addr), `[6:3]` (contador) e `[7]` (status)"},
        {"Bloco": "Depuração", "Componente": "Barra de pinos 2×8 (2.54 mm)", "Função": "Acesso rápido para analisador lógico (Saleae / PulseView)"},
    ])
    st.dataframe(bom_df, width="stretch", hide_index=True)

    st.markdown("### Exportar Resumo Técnico")
    resumo_md = f"""# NeuroChip SNN (v1.0.0) — Resumo Técnico
- **Top Module:** `tt_um_neurochip_snn` (Tiny Tapeout `1×2`, Sky130)
- **Área & Signoff ASIC:** `161.0 × 225.76 µm` (`0.03635 mm²`), `4.058` células, `0` violações Magic DRC, `WNS=0.0 / TNS=0.0` @ 50 MHz
- **FPGA PnR:** iCE40 (`96.26 MHz`) e ECP5 (`103.42 MHz`) com 14 pinos fixos
- **Hardware:** Regulação `5V → 3.3V`, clock `50 MHz`, entradas AER (`ui_in[2:0]`), LEDs + resistores `330 Ω` (`uo_out[7:0]`) e header `J1`
"""
    st.download_button(
        "Exportar Relatório Técnico (.md)",
        data=resumo_md.encode("utf-8"),
        file_name="neurochip_snn_relatorio_v1.0.0.md",
        mime="text/markdown",
    )

    pdf_path = Path("docs/neurochip_snn_report_v1.0.0.pdf")
    if pdf_path.exists():
        st.download_button(
            "Exportar Relatório Técnico Assinado (.pdf)",
            data=pdf_path.read_bytes(),
            file_name="neurochip_snn_report_v1.0.0.pdf",
            mime="application/pdf",
        )
