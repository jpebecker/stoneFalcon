"""Teste de fumaça dos scripts de início: roda iniciar.bat (Windows) ou iniciar.sh (Mac/Linux) do jeito que uma pessoa
rodaria, espera a plataforma responder em /api/v1/saude com a versão certa, confere que as telas são servidas e desliga.

Uso: python scripts/fumaca_iniciar.py [porta]      (a esteira de CI roda no Ubuntu e no Windows)
Código de saída 0 = a plataforma subiu e respondeu a versão esperada.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
LIMITE_S = 900            # a primeira vez compila as telas e instala as dependências
sys.path.insert(0, str(RAIZ / "scripts"))
from iniciar_ajuda import versao  # noqa: E402


def _desligar(proc: subprocess.Popen) -> None:
    if proc.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)], capture_output=True)
    else:
        try:
            os.killpg(proc.pid, 15)
        except ProcessLookupError:
            pass
    try:
        proc.wait(timeout=20)
    except subprocess.TimeoutExpired:
        proc.kill()


def main(argv: list[str]) -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    porta = int(argv[1]) if len(argv) > 1 else 18765
    esperado = versao()
    banco = Path(tempfile.mkdtemp(prefix="stonefalcon-fumaca-")) / "fumaca.db"
    env = dict(os.environ, STONEFALCON_PORTA=str(porta), STONEFALCON_SEM_NAVEGADOR="1", STONEFALCON_SEM_PAUSA="1",
               STONEFALCON_DB="sqlite:///" + banco.as_posix(), MODO_SIMULADO="1", STONEFALCON_VIGIA="0", STONEFALCON_AGENDADOR="0")
    cmd = ["cmd", "/c", str(RAIZ / "iniciar.bat")] if os.name == "nt" else ["sh", "iniciar.sh"]
    proc = subprocess.Popen(cmd, cwd=RAIZ, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8",
                            errors="replace", start_new_session=(os.name != "nt"))
    linhas: list[str] = []
    import threading

    def ler():
        for linha in proc.stdout:        # type: ignore[union-attr]
            linhas.append(linha.rstrip())
    threading.Thread(target=ler, daemon=True).start()
    inicio = time.time()
    resposta = None
    try:
        while time.time() - inicio < LIMITE_S:
            if proc.poll() is not None:
                print("O script terminou antes de a plataforma responder (código %s). Saída:" % proc.returncode)
                print("\n".join(linhas[-60:]))
                return 1
            try:
                with urllib.request.urlopen("http://127.0.0.1:%d/api/v1/saude" % porta, timeout=3) as r:
                    resposta = json.loads(r.read())
                    break
            except Exception:
                time.sleep(1.5)
        if resposta is None:
            print("A plataforma não respondeu em %d s. Saída:" % LIMITE_S)
            print("\n".join(linhas[-60:]))
            return 1
        problemas = []
        if resposta.get("versao") != esperado:
            problemas.append("a saúde diz versão %r, e o esperado é %r" % (resposta.get("versao"), esperado))
        with urllib.request.urlopen("http://127.0.0.1:%d/" % porta, timeout=5) as r:
            pagina = r.read().decode("utf-8", "replace")
        if "/assets/" not in pagina:
            problemas.append("as telas compiladas não foram servidas (sem /assets/ na página inicial)")
        for p in problemas:
            print("ERRO: " + p)
        if problemas:
            print("\n".join(linhas[-40:]))
            return 1
        print("Fumaça ok: %s respondeu a versão %s em %.0f s." % (Path(cmd[-1]).name, esperado, time.time() - inicio))
        return 0
    finally:
        _desligar(proc)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
