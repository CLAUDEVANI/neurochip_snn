import hashlib
from pathlib import Path
from weasyprint import HTML

ROOT = Path(__file__).resolve().parent.parent

def sha256_file(path: Path) -> str:
    if not path.exists():
        return "arquivo-nao-encontrado"
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

artifacts = [
    ("Layout GDSII (PNG)", ROOT / "docs/gds_die_layout.png"),
    ("Esquema PCB Rev 1.1 (SVG)", ROOT / "docs/esquema_eletronico_snn.svg"),
    ("Bitstream FPGA iCE40", ROOT / "build/neurochip_ice40.bin"),
    ("Bitstream FPGA ECP5", ROOT / "build/neurochip_ecp5.bit"),
    ("Pacote Tiny Tapeout 1x2", ROOT / "build/tt_submission_1x2.tar.gz"),
    ("GDSII Sky130", ROOT / "build/gds_artifacts/neurochip-snn-gdsii/tt_um_neurochip_snn.gds"),
]

rows = "\n".join(
    f"<tr><td>{name}</td><td><code>{p.name}</code></td><td style='font-size:8pt'><code>{sha256_file(p)}</code></td></tr>"
    for name, p in artifacts
)

html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<style>
  body {{ font-family: sans-serif; margin: 24px; color: #1a1a1a; font-size: 10.5pt; }}
  h1 {{ color: #0b2545; border-bottom: 2px solid #0b2545; padding-bottom: 6px; }}
  h2 {{ color: #134074; margin-top: 20px; }}
  table {{ width: 100%; border-collapse: collapse; margin-top: 8px; }}
  th, td {{ border: 1px solid #ccc; padding: 6px 8px; text-align: left; }}
  th {{ background: #eef3f8; }}
  .img-box {{ text-align: center; margin: 12px 0; }}
  img {{ max-width: 92%; max-height: 360px; border: 1px solid #ddd; }}
  code {{ background: #f4f4f4; padding: 1px 4px; border-radius: 3px; }}
</style>
</head>
<body>
  <h1>NeuroChip SNN (v1.0.0) — Relatório Técnico de Signoff & Hardware</h1>
  <p><strong>Top Module:</strong> <code>tt_um_neurochip_snn</code> | <strong>Arquitetura:</strong> LIF + STDP + AER</p>

  <h2>1. Métricas Consolidadas (ASIC & FPGA)</h2>
  <table>
    <tr><th>Alvo</th><th>Recursos / Área</th><th>Frequência / Timing</th><th>Status</th></tr>
    <tr><td>ASIC Sky130 (1×2)</td><td>161.0 × 225.76 µm | 4.058 células</td><td>50 MHz (WNS=0.0, TNS=0.0)</td><td>0 DRC</td></tr>
    <tr><td>FPGA iCE40</td><td>572 LUT4 | 172 FFs | 759/1280 LCs</td><td>96.26 MHz (PASS @ 12 MHz)</td><td>0 Erros</td></tr>
    <tr><td>FPGA ECP5</td><td>408 LUT4 | 164 CCU2C | 172 FFs</td><td>103.42 MHz (PASS @ 25 MHz)</td><td>0 Erros</td></tr>
  </table>

  <h2>2. Layout Físico GDSII (Sky130 1×2)</h2>
  <div class="img-box"><img src="file://{(ROOT / 'docs/gds_die_layout.png').as_posix()}"></div>

  <h2>3. Layout PCB de Bancada (Rev 1.1)</h2>
  <div class="img-box"><img src="file://{(ROOT / 'docs/esquema_eletronico_snn.svg').as_posix()}"></div>

  <h2>4. Integridade Criptográfica dos Artefatos (SHA-256)</h2>
  <table>
    <tr><th>Artefato</th><th>Arquivo</th><th>SHA-256</th></tr>
    {rows}
  </table>
</body>
</html>
"""

out_pdf = ROOT / "docs/neurochip_snn_report_v1.0.0.pdf"
HTML(string=html, base_url=str(ROOT)).write_pdf(str(out_pdf))
print(f"OK: PDF gerado em {out_pdf}")
