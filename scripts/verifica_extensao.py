"""Checagem da extensão para a esteira de CI.

Falha (código 1) se o manifesto for inválido ou citar um arquivo que não existe.
Uso: python scripts/verifica_extensao.py [pasta_da_extensao]
"""
import json
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
CAMPOS = ("manifest_version", "name", "version", "description")


def _arquivos_citados(m: dict) -> list[str]:
    citados: list[str] = []
    citados += list((m.get("icons") or {}).values())
    acao = m.get("action") or {}
    icone = acao.get("default_icon")
    if isinstance(icone, dict):
        citados += list(icone.values())
    elif isinstance(icone, str):
        citados.append(icone)
    if acao.get("default_popup"):
        citados.append(acao["default_popup"])
    fundo = (m.get("background") or {}).get("service_worker")
    if fundo:
        citados.append(fundo)
    painel = (m.get("side_panel") or {}).get("default_path")
    if painel:
        citados.append(painel)
    if m.get("options_page"):
        citados.append(m["options_page"])
    for cs in m.get("content_scripts") or []:
        citados += cs.get("js", []) + cs.get("css", [])
    return citados


def verificar(pasta: Path) -> list[str]:
    """Devolve a lista de problemas (vazia = tudo certo)."""
    caminho = pasta / "manifest.json"
    if not caminho.is_file():
        return [f"manifest.json não encontrado em {pasta}"]
    try:
        m = json.loads(caminho.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return [f"manifest.json inválido: {e}"]
    if not isinstance(m, dict):
        return ["manifest.json deve ser um objeto"]
    problemas = [f"campo obrigatório ausente: {c}" for c in CAMPOS if not m.get(c)]
    if m.get("manifest_version") != 3:
        problemas.append("manifest_version deve ser 3")
    versao = str(m.get("version", ""))
    if versao and not all(p.isdigit() for p in versao.split(".")):
        problemas.append(f"version inválida para o Chrome: {versao!r}")
    citados = _arquivos_citados(m)
    for arq in citados:
        if not (pasta / arq).is_file():
            problemas.append(f"o manifesto cita um arquivo que não existe: {arq}")
    # páginas HTML citadas também referenciam scripts e estilos locais
    for pagina in {a for a in citados if a.endswith(".html")}:
        arq = pasta / pagina
        if not arq.is_file():
            continue
        for ref in re.findall(r'(?:src|href)="([^"]+)"', arq.read_text(encoding="utf-8")):
            if "://" in ref or ref.startswith(("#", "data:")):
                continue
            if not (pasta / ref).is_file():
                problemas.append(f"{pagina} cita um arquivo que não existe: {ref}")
    return problemas


def main(argv: list[str]) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    pasta = Path(argv[1]) if len(argv) > 1 else RAIZ / "extensao"
    problemas = verificar(pasta)
    for p in problemas:
        print(f"ERRO: {p}")
    if not problemas:
        print(f"Extensão ok ({pasta}).")
    return 1 if problemas else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
