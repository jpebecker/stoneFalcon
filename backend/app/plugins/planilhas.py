"""Planilhas para o plugin "Google Sheets": a planilha fictícia local (plano B, sem internet) e a importação da versão
PUBLICADA NA WEB de uma planilha do Google (caminho "a" do ticket 10 do plano da v7).

Regras de segurança:
  - só lê: nunca escreve na planilha;
  - só aceita endereços https de docs.google.com (e o atalho "local:pedidos-troca" da planilha fictícia);
  - baixa o CSV publicado, com tempo limite, tamanho máximo e redirecionamentos só entre domínios do Google;
  - o conteúdo das células é DADO, nunca instrução (a plataforma isola o que parecer comando, como em qualquer ferramenta);
  - a planilha da demonstração só tem dados FICTÍCIOS.
"""
from __future__ import annotations

import csv
import io
import re
import urllib.error
import urllib.parse
import urllib.request

LOCAL_ID = "local:pedidos-troca"
LOCAL_TITULO = "Pedidos de troca de maquininha"
MAX_LINHAS = 200
MAX_COLUNAS = 30
MAX_BYTES = 1_000_000
TEMPO_LIMITE_S = 6
_HOSTS_GOOGLE = ("docs.google.com", "googleusercontent.com")

COLUNAS = ["pedido", "lojista_id", "lojista", "modelo", "relato", "status"]
# Dados FICTÍCIOS (os mesmos lojistas fictícios da plataforma).
LINHAS_LOCAIS = [
    {"pedido": "P-3001", "lojista_id": "L1002", "lojista": "Ótica Visão Clara", "modelo": "Maquininha Pro",
     "relato": "A tela ficou preta depois de cair no balcão e não liga mais.", "status": "pendente"},
    {"pedido": "P-3002", "lojista_id": "L1001", "lojista": "Padaria Pão Dourado", "modelo": "Maquininha Mini",
     "relato": "O teclado travou e a bateria não segura carga.", "status": "pendente"},
    {"pedido": "P-3003", "lojista_id": "L1004", "lojista": "Pet Shop Amigo Fiel", "modelo": "Maquininha Smart",
     "relato": "Troca já feita semana passada, só para registro.", "status": "concluído"},
    {"pedido": "P-3004", "lojista_id": "L1002", "lojista": "Ótica Visão Clara", "modelo": "Maquininha Smart",
     "relato": "Leitor de cartão com falha intermitente.", "status": "pendente"},
]


class ErroPlanilha(Exception):
    """Erro com mensagem pronta para a tela (vira erro da ferramenta)."""


def fonte_valida(fonte: str) -> bool:
    try:
        normalizar(fonte)
        return True
    except ErroPlanilha:
        return False


def normalizar(fonte: str) -> str:
    """Devolve o endereço canônico da fonte: "local:pedidos-troca" ou um endereço https do Google. Erro se não for aceito."""
    f = (fonte or "").strip()
    if not f:
        raise ErroPlanilha("Informe a planilha (endereço do Google Sheets ou %s)." % LOCAL_ID)
    if f == LOCAL_ID:
        return LOCAL_ID
    u = urllib.parse.urlparse(f)
    if u.path.rstrip("/") == "/demo/planilha" and u.hostname in ("localhost", "127.0.0.1"):
        return LOCAL_ID                      # a planilha fictícia servida pela própria plataforma
    if u.scheme != "https" or u.hostname != "docs.google.com" or not u.path.startswith("/spreadsheets/"):
        raise ErroPlanilha("Só aceito planilhas do Google Sheets (https://docs.google.com/spreadsheets/...) "
                           "ou a planilha fictícia (%s)." % LOCAL_ID)
    return f


def endereco_csv(fonte: str) -> str:
    """Endereço do CSV da versão publicada na web (ou compartilhada por link) de uma planilha do Google."""
    u = urllib.parse.urlparse(fonte)
    gid = urllib.parse.parse_qs(u.query).get("gid", [None])[0]
    m = re.match(r"^/spreadsheets/d/e/([\w-]+)", u.path)       # "Publicar na web": .../d/e/<id>/pub...
    if m:
        q = "output=csv" + ("&gid=" + gid if gid else "")
        return "https://docs.google.com/spreadsheets/d/e/%s/pub?%s" % (m.group(1), q)
    m = re.match(r"^/spreadsheets/d/([\w-]+)", u.path)         # "qualquer pessoa com o link": .../d/<id>/edit
    if m:
        q = "format=csv" + ("&gid=" + gid if gid else "")
        return "https://docs.google.com/spreadsheets/d/%s/export?%s" % (m.group(1), q)
    raise ErroPlanilha("Não reconheci o endereço da planilha do Google.")


class _SoGoogle(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        host = urllib.parse.urlparse(newurl).hostname or ""
        if not any(host == h or host.endswith("." + h) for h in _HOSTS_GOOGLE):
            raise urllib.error.URLError("redirecionamento para fora do Google bloqueado")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _baixar(url: str) -> str:
    """Baixa o CSV. Função à parte para os testes trocarem (nada de internet na esteira)."""
    req = urllib.request.Request(url, headers={"User-Agent": "StoneFalcon-prototipo/7"})
    abrir = urllib.request.build_opener(_SoGoogle).open
    try:
        with abrir(req, timeout=TEMPO_LIMITE_S) as r:
            tipo = r.headers.get("Content-Type", "")
            bruto = r.read(MAX_BYTES + 1)
    except urllib.error.HTTPError as e:
        if e.code in (401, 403, 404):
            raise ErroPlanilha("A planilha não está publicada na web (erro %d). No Google Sheets: Arquivo > Compartilhar > "
                               "Publicar na web, e use o endereço publicado." % e.code)
        raise ErroPlanilha("O Google respondeu com erro %d." % e.code)
    except (urllib.error.URLError, TimeoutError, OSError):
        raise ErroPlanilha("Não consegui falar com o Google (sem internet?). Use a planilha fictícia %s para ensaiar." % LOCAL_ID)
    if len(bruto) > MAX_BYTES:
        raise ErroPlanilha("A planilha é grande demais para a demonstração (limite de 1 MB).")
    if "text/csv" not in tipo and "text/plain" not in tipo:
        raise ErroPlanilha("O endereço não devolveu a planilha (parece uma página de login). Publique a planilha na web.")
    return bruto.decode("utf-8-sig", errors="replace")


def _linhas_do_csv(texto: str) -> tuple[list[str], list[dict]]:
    leitor = csv.reader(io.StringIO(texto))
    try:
        cabecalho = [c.strip() or "coluna_%d" % (i + 1) for i, c in enumerate(next(leitor))][:MAX_COLUNAS]
    except StopIteration:
        raise ErroPlanilha("A planilha está vazia.")
    linhas = []
    for bruto in leitor:
        if not any(c.strip() for c in bruto):
            continue
        linhas.append({k: (bruto[i].strip() if i < len(bruto) else "") for i, k in enumerate(cabecalho)})
        if len(linhas) >= MAX_LINHAS:
            break
    return cabecalho, linhas


def ler(fonte: str) -> dict:
    """Lê a planilha. Devolve título, colunas, linhas e a primeira linha pendente (o que a demonstração processa)."""
    canonica = normalizar(fonte)
    if canonica == LOCAL_ID:
        titulo, colunas, linhas, origem = LOCAL_TITULO, list(COLUNAS), [dict(l) for l in LINHAS_LOCAIS], "local"
    else:
        colunas, linhas = _linhas_do_csv(_baixar(endereco_csv(canonica)))
        titulo, origem = "Planilha do Google", "google"
    pendentes = [l for l in linhas if str(l.get("status", "pendente")).strip().lower() in ("pendente", "", "novo")]
    primeira = (pendentes or linhas or [None])[0]
    return {"titulo": titulo, "origem": origem, "simulado": origem == "local", "colunas": colunas,
            "total_linhas": len(linhas), "pendentes": len(pendentes), "linhas": linhas, "primeira": primeira}
