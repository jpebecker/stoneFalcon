"""Checagem de versão para a esteira: API, extensão, front e pacote do back contam o mesmo número.

A fonte é backend/app/core/versao.py. Falha (código 1) se alguma outra cópia divergir.
Uso: python scripts/verifica_versao.py [raiz_do_repositorio]
"""
import json
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]


def _versao_fonte(raiz: Path) -> str:
    texto = (raiz / "backend/app/core/versao.py").read_text(encoding="utf-8")
    achou = re.search(r'^VERSAO\s*=\s*"(\d+\.\d+\.\d+)"', texto, re.M)
    if not achou:
        raise ValueError("VERSAO não encontrada em backend/app/core/versao.py")
    return achou.group(1)


def coletar(raiz: Path) -> dict[str, str]:
    """Versão declarada em cada lugar (o que o rodapé e o Chrome mostram, mais o que os pacotes dizem)."""
    manifesto = json.loads((raiz / "extensao/manifest.json").read_text(encoding="utf-8"))
    pyproject = (raiz / "backend/pyproject.toml").read_text(encoding="utf-8")
    achou = re.search(r'^version\s*=\s*"([^"]+)"', pyproject, re.M)
    pacote = json.loads((raiz / "frontend/package.json").read_text(encoding="utf-8"))
    trava = json.loads((raiz / "frontend/package-lock.json").read_text(encoding="utf-8"))
    return {
        "extensao/manifest.json (version)": str(manifesto.get("version")),
        "backend/pyproject.toml": achou.group(1) if achou else "?",
        "frontend/package.json": str(pacote.get("version")),
        "frontend/package-lock.json": str(trava.get("version")),
    }


def verificar(raiz: Path) -> list[str]:
    fonte = _versao_fonte(raiz)
    problemas = [f"{onde} diz {v}, mas a plataforma é {fonte}" for onde, v in coletar(raiz).items() if v != fonte]
    manifesto = json.loads((raiz / "extensao/manifest.json").read_text(encoding="utf-8"))
    curta = ".".join(fonte.split(".")[:2])
    if f"StoneFalcon {curta}" != manifesto.get("name"):
        problemas.append(f'extensao/manifest.json (name) deve ser "StoneFalcon {curta}", e está {manifesto.get("name")!r}')
    return problemas


def main(argv: list[str]) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    raiz = Path(argv[1]) if len(argv) > 1 else RAIZ
    problemas = verificar(raiz)
    for p in problemas:
        print(f"ERRO: {p}")
    if not problemas:
        print(f"Versão {_versao_fonte(raiz)} consistente em todo o repositório.")
    return 1 if problemas else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
