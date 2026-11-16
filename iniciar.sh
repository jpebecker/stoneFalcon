#!/bin/sh
# Liga o StoneFalcon no Mac ou no Linux:  sh iniciar.sh
cd "$(dirname "$0")" || exit 1
command -v python3 >/dev/null 2>&1 || { echo "Instale o Python 3.11+: https://www.python.org/downloads/"; exit 1; }

if [ ! -f frontend/dist/index.html ]; then
  command -v npm >/dev/null 2>&1 || { echo "Falta compilar as telas: instale o Node.js LTS (https://nodejs.org) e rode de novo."; exit 1; }
  echo "Compilando as telas (só na primeira vez)..."
  npm --prefix frontend install --no-audit --no-fund && npm --prefix frontend run build || exit 1
fi

if [ ! -x backend/.venv/bin/python ]; then
  echo "Preparando o ambiente Python (só na primeira vez)..."
  python3 -m venv backend/.venv && backend/.venv/bin/python -m pip install --quiet -r backend/requirements.txt || exit 1
fi

echo "Abrindo http://localhost:8765  (Ctrl+C para desligar)"
( sleep 2; command -v open >/dev/null && open http://localhost:8765 || xdg-open http://localhost:8765 ) >/dev/null 2>&1 &
exec backend/.venv/bin/python -m uvicorn --app-dir backend app.main:app --port 8765
