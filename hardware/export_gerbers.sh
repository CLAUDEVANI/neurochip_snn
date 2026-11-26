#!/usr/bin/env bash
set -euo pipefail
PCB="hardware/kicad/neurochip_snn.kicad_pcb"
OUT="hardware/gerbers"
mkdir -p "$OUT"

if ! command -v kicad-cli >/dev/null 2>&1; then
  echo "Aviso: kicad-cli não encontrado. Instale com: sudo apt install kicad"
  exit 0
fi

if [ ! -f "$PCB" ]; then
  echo "Aviso: $PCB ainda não foi roteado no KiCad. Abra hardware/kicad/neurochip_snn.kicad_pro no KiCad."
  exit 0
fi

kicad-cli pcb export gerbers --output "$OUT/" "$PCB"
kicad-cli pcb export drill --output "$OUT/" "$PCB"
zip -j "hardware/neurochip_snn_gerbers.zip" "$OUT"/*
echo "OK: Gerbers prontos em hardware/neurochip_snn_gerbers.zip"
