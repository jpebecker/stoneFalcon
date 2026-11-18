"""Ajuda dos scripts de início (iniciar.bat e iniciar.sh): as decisões ficam aqui, em Python, para valerem igual no Windows,
no Mac e no Linux e para terem teste automático (backend/tests/test_iniciar.py).

Uso (códigos de saída: 0 = tudo certo, 10 = "precisa fazer", 1 = erro com mensagem em português):
    python scripts/iniciar_ajuda.py python              confere a versão do Python (3.11 ou mais nova)
    python scripts/iniciar_ajuda.py porta [N]           confere se a porta (padrão 8765) está livre
    python scripts/iniciar_ajuda.py front               10 se as telas precisam ser compiladas (de novo)
    python scripts/iniciar_ajuda.py marcar-front        grava a marca das telas recém-compiladas
    python scripts/iniciar_ajuda.py deps <pasta_venv>   10 se as dependências do back mudaram (ou nunca foram instaladas)
    python scripts/iniciar_ajuda.py marcar-deps <venv>  grava a marca das dependências recém-instaladas
    python scripts/iniciar_ajuda.py versao              imprime a versão da plataforma
"""
from __future__ import annotations

import hashlib
import re
import socket
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
MINIMO = (3, 11)
PORTA_PADRAO = 8765
PRECISA = 10
MARCA_FRONT = "frontend/dist/.stonefalcon-marca"
MARCA_DEPS = ".stonefalcon-requirements.sha256"


def versao(raiz: Path = RAIZ) -> str:
    texto = (raiz / "backend/app/core/versao.py").read_text(encoding="utf-8")
    achou = re.search(r'^VERSAO\s*=\s*"([^"]+)"', texto, re.M)
    return achou.group(1) if achou else "?"


def python_ok(versao_atual: tuple[int, ...] | None = None) -> str | None:
    """Mensagem de erro se o Python for velho demais; None se estiver tudo certo."""
    atual = versao_atual or sys.version_info[:3]
    if tuple(atual[:2]) < MINIMO:
        return ("O Python %d.%d.%d é antigo para o StoneFalcon. Instale o Python %d.%d ou mais novo em "
                "https://www.python.org/downloads/ e rode de novo." % (tuple(atual[:3]) + MINIMO))
    return None


def porta_livre(porta: int = PORTA_PADRAO) -> str | None:
    """Mensagem de erro se a porta estiver ocupada (ex.: outra cópia do StoneFalcon aberta); None se livre."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 0)
        try:
            s.bind(("127.0.0.1", porta))
        except OSError:
            return ("A porta %d já está em uso, provavelmente por outra cópia do StoneFalcon que ainda está aberta. "
                    "Feche a outra janela (ou o outro programa) e rode de novo, ou use outra porta: "
                    "defina STONEFALCON_PORTA, por exemplo 8766." % porta)
    return None


def _impressao_do_front(raiz: Path) -> str:
    """Resumo do que vira as telas: versão da plataforma, código-fonte e dependências."""
    h = hashlib.sha256(versao(raiz).encode())
    arquivos = sorted((raiz / "frontend/src").rglob("*")) + [raiz / "frontend/index.html", raiz / "frontend/package.json",
                                                           raiz / "frontend/package-lock.json", raiz / "frontend/vite.config.ts",
                                                           raiz / "frontend/tailwind.config.js"]
    for a in arquivos:
        if a.is_file():
            h.update(a.relative_to(raiz).as_posix().encode())
            h.update(a.read_bytes())
    return h.hexdigest()


def front_precisa_compilar(raiz: Path = RAIZ) -> bool:
    """Compila de novo se nunca foi compilado ou se a versão ou o código das telas mudaram (pasta que já rodou a v6)."""
    if not (raiz / "frontend/dist/index.html").is_file():
        return True
    marca = raiz / MARCA_FRONT
    return not marca.is_file() or marca.read_text(encoding="utf-8").strip() != _impressao_do_front(raiz)


def marcar_front(raiz: Path = RAIZ) -> None:
    marca = raiz / MARCA_FRONT
    marca.parent.mkdir(parents=True, exist_ok=True)
    marca.write_text(_impressao_do_front(raiz), encoding="utf-8")


def _hash_deps(raiz: Path) -> str:
    return hashlib.sha256((raiz / "backend/requirements.txt").read_bytes()).hexdigest()


def deps_precisam_instalar(venv: Path, raiz: Path = RAIZ) -> bool:
    """Instala de novo se o ambiente não existe, nunca foi marcado ou se o requirements.txt mudou."""
    marca = venv / MARCA_DEPS
    return not venv.is_dir() or not marca.is_file() or marca.read_text(encoding="utf-8").strip() != _hash_deps(raiz)


def marcar_deps(venv: Path, raiz: Path = RAIZ) -> None:
    (venv / MARCA_DEPS).write_text(_hash_deps(raiz), encoding="utf-8")


def main(argv: list[str]) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    cmd = argv[1] if len(argv) > 1 else ""
    if cmd == "python":
        erro = python_ok()
    elif cmd == "porta":
        erro = porta_livre(int(argv[2]) if len(argv) > 2 and argv[2].isdigit() else PORTA_PADRAO)
    elif cmd == "front":
        return PRECISA if front_precisa_compilar() else 0
    elif cmd == "marcar-front":
        marcar_front()
        return 0
    elif cmd == "deps" and len(argv) > 2:
        return PRECISA if deps_precisam_instalar(Path(argv[2])) else 0
    elif cmd == "marcar-deps" and len(argv) > 2:
        marcar_deps(Path(argv[2]))
        return 0
    elif cmd == "versao":
        print(versao())
        return 0
    else:
        print(__doc__)
        return 1
    if erro:
        print("  " + erro)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
