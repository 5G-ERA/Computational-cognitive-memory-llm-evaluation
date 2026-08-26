#!/usr/bin/env bash
# Manifiesto de lo que el freeze congela.
#
# EXCLUYE deliberadamente la capa de firma y de estado. Un registro de freeze que
# hashea un manifiesto que lo contiene a el mismo nunca puede ser consistente: al
# firmarlo cambia, y el hash que certifica deja de valer. Se excluyen tambien los
# registros de autorizacion y la salida de la puerta, que cambian en cada ejecucion.
set -e
cd "$(dirname "$0")/.."
find . -type f \
  ! -name '*.pyc' ! -path '*__pycache__*' \
  ! -path './validation/SHA256SUMS.txt' \
  ! -path './validation/FREEZE_*.json' \
  ! -path './validation/AUTHORISATION_*.json' \
  ! -path './validation/go_no_go_gate.json' \
  | sort | xargs sha256sum > validation/SHA256SUMS.txt
wc -l < validation/SHA256SUMS.txt
