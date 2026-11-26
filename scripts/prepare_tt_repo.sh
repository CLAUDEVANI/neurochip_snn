#!/usr/bin/env bash
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "Uso: $0 <caminho_do_clone_ttsky_template>"
  echo "Exemplo: $0 ~/ttsky-neurochip-snn"
  exit 1
fi

DEST="$1"
TAR="build/tt_submission_1x2.tar.gz"

[ -f "$TAR" ] || { echo "Erro: $TAR não encontrado."; exit 1; }
[ -d "$DEST/.git" ] || { echo "Erro: $DEST não é um repositório Git válido."; exit 1; }

tar -xzf "$TAR" -C "$DEST"
cd "$DEST"
git status -sb
echo ""
echo "Próximo passo dentro de $DEST:"
echo "  git add info.yaml src/ docs/info.md"
echo "  git commit -m 'feat: adiciona NeuroChip SNN (1x2, Sky130)'"
echo "  git push"
