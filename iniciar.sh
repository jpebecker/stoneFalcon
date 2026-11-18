#!/bin/sh
# Liga o StoneFalcon no Mac ou no Linux:  sh iniciar.sh
# Variáveis opcionais: STONEFALCON_PORTA (padrão 8765) e STONEFALCON_SEM_NAVEGADOR=1 (não abre o navegador).
cd "$(dirname "$0")" || exit 1
PORTA="${STONEFALCON_PORTA:-8765}"
command -v python3 >/dev/null 2>&1 || { echo "Instale o Python 3.11+: https://www.python.org/downloads/"; exit 1; }
python3 scripts/iniciar_ajuda.py python || exit 1
python3 scripts/iniciar_ajuda.py porta "$PORTA" || exit 1

# telas: compila na primeira vez e de novo sempre que a versão ou o código mudou (pasta que já rodou uma versão anterior)
rc=0; python3 scripts/iniciar_ajuda.py front || rc=$?
if [ "$rc" -eq 10 ]; then
  command -v npm >/dev/null 2>&1 || { echo "Falta compilar as telas: instale o Node.js LTS (https://nodejs.org) e rode de novo."; exit 1; }
  echo "Compilando as telas (primeira vez ou depois de atualizar)..."
  # npm roda DE DENTRO de frontend (subshell): o npm 10.9 ignora --prefix no install e procura o package.json na raiz
  ( cd frontend && npm install --no-audit --no-fund && npm run build ) || exit 1
  python3 scripts/iniciar_ajuda.py marcar-front || exit 1
elif [ "$rc" -ne 0 ]; then
  exit 1
fi

# back: ambiente Python isolado; reinstala as dependências se o requirements.txt mudou
if [ ! -x backend/.venv/bin/python ]; then
  echo "Preparando o ambiente Python (só na primeira vez)..."
  python3 -m venv backend/.venv || exit 1
fi
rc=0; python3 scripts/iniciar_ajuda.py deps backend/.venv || rc=$?
if [ "$rc" -eq 10 ]; then
  echo "Instalando as dependências do back (primeira vez ou depois de atualizar)..."
  backend/.venv/bin/python -m pip install --quiet -r backend/requirements.txt || exit 1
  python3 scripts/iniciar_ajuda.py marcar-deps backend/.venv || exit 1
elif [ "$rc" -ne 0 ]; then
  exit 1
fi

echo "Abrindo http://localhost:$PORTA  (Ctrl+C para desligar)"
if [ -z "$STONEFALCON_SEM_NAVEGADOR" ]; then
  ( sleep 2; command -v open >/dev/null && open "http://localhost:$PORTA" || xdg-open "http://localhost:$PORTA" ) >/dev/null 2>&1 &
fi
exec backend/.venv/bin/python -m uvicorn --app-dir backend app.main:app --port "$PORTA"
