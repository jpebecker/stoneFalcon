"""Plugin "Arquivos e Planilhas" (v8): o plugin REAL, que funciona de verdade e sem internet.

Uma pessoa envia um CSV ou XLSX, escolhe a classificação (pública a restrita, no máximo o nível dela) e as áreas que podem
usá-lo. O arquivo vira colunas e linhas no banco. Agentes e processos ganham ferramentas de verdade: listar arquivos, ler
linhas (com filtro), buscar uma linha, acrescentar uma linha e atualizar uma linha.

Regras, as mesmas de toda ferramenta:
  - quem lê precisa ser da área do arquivo E ter nível que cubra a classificação (senão: negado e auditado);
  - a leitura passa pelo mascaramento do executor (CPF, CNPJ, cartão, e-mail, telefone e segredos viram marcadores);
  - escrita em arquivo confidencial ou restrito espera a confirmação de um humano;
  - toda escrita fica na trilha de auditoria: quem, qual agente ou processo, qual arquivo e qual linha.
"""
from __future__ import annotations

import base64
import binascii
import csv
import io
import json
import re
import uuid
import zipfile
from datetime import date, datetime

from sqlmodel import Session, select

from ..audit import trilha
from ..core.db import trava
from ..core.identidade import PERSONAS, Classificacao, Persona
from ..core.relogio import agora
from ..tools.contexto import AcessoNegado, Contexto, ErroFerramenta
from .modelos import ArquivoPlugin

PLUGIN_ID = "arquivos"
MAX_BYTES = 2_000_000
MAX_LINHAS = 5_000
MAX_COLUNAS = 30
MAX_CELULA = 2_000
LIMITES = {"bytes": MAX_BYTES, "linhas": MAX_LINHAS, "colunas": MAX_COLUNAS, "formatos": ["csv", "xlsx"]}
TAMANHO_PREVIA = 50
TODAS = "*"


class ErroArquivo(Exception):
    def __init__(self, mensagem: str, status: int = 400):
        super().__init__(mensagem)
        self.status = status


# =============================================================
# Ler o arquivo enviado
# =============================================================
def _celula(v):
    if v is None:
        return ""
    if isinstance(v, bool):
        return "sim" if v else "não"
    if isinstance(v, (datetime, date)):
        return v.isoformat()
    if isinstance(v, float) and v.is_integer():
        return int(v)
    if isinstance(v, (int, float)):
        return v
    t = str(v).strip()
    return t[:MAX_CELULA]


def _montar(cabecalho: list, bruto: list[list]) -> tuple[list[str], list[dict]]:
    colunas = [str(c).strip() if c is not None else "" for c in cabecalho]
    while colunas and not colunas[-1]:
        colunas.pop()
    if not colunas:
        raise ErroArquivo("A primeira linha do arquivo precisa ter o nome de cada coluna. Não encontrei nenhum.", 422)
    if any(not c for c in colunas):
        raise ErroArquivo("Toda coluna precisa de um nome na primeira linha. Há uma coluna sem nome.", 422)
    repetidas = sorted({c for c in colunas if colunas.count(c) > 1})
    if repetidas:
        raise ErroArquivo("Há colunas com o mesmo nome: %s. Dê um nome diferente a cada uma." % ", ".join(repetidas), 422)
    if len(colunas) > MAX_COLUNAS:
        raise ErroArquivo("O arquivo tem %d colunas; o máximo é %d." % (len(colunas), MAX_COLUNAS), 422)
    linhas = []
    for r in bruto:
        valores = [_celula(v) for v in list(r)[:len(colunas)]] + [""] * (len(colunas) - len(r))
        if all(v == "" for v in valores):
            continue
        linhas.append(dict(zip(colunas, valores)))
        if len(linhas) > MAX_LINHAS:
            raise ErroArquivo("O arquivo passa de %d linhas, o máximo que o plugin guarda." % MAX_LINHAS, 422)
    return colunas, linhas


def _ler_csv(conteudo: bytes) -> tuple[list[str], list[dict]]:
    for codificacao in ("utf-8-sig", "cp1252"):
        try:
            texto = conteudo.decode(codificacao)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise ErroArquivo("Não consegui ler o texto do arquivo. Salve-o como CSV em UTF-8 e envie de novo.", 422)
    primeira = texto.splitlines()[0] if texto.strip() else ""
    separador = max((",", ";", "\t"), key=primeira.count)
    try:
        linhas = list(csv.reader(io.StringIO(texto), delimiter=separador))
    except csv.Error:
        raise ErroArquivo("O arquivo CSV está malformado. Confira as aspas e os separadores.", 422)
    if not linhas:
        raise ErroArquivo("O arquivo está vazio.", 422)
    return _montar(linhas[0], linhas[1:])


def _ler_xlsx(conteudo: bytes) -> tuple[list[str], list[dict]]:
    from openpyxl import load_workbook
    try:
        with zipfile.ZipFile(io.BytesIO(conteudo)) as z:
            if sum(i.file_size for i in z.infolist()) > 40_000_000:
                raise ErroArquivo("A planilha é grande demais depois de aberta.", 422)
        wb = load_workbook(io.BytesIO(conteudo), read_only=True, data_only=True)
    except ErroArquivo:
        raise
    except Exception:
        raise ErroArquivo("Não consegui abrir a planilha. Confira se é um arquivo .xlsx (Excel) e não está protegido por senha.", 422)
    try:
        ws = wb.worksheets[0]
        linhas = []
        for i, r in enumerate(ws.iter_rows(values_only=True)):
            linhas.append(list(r))
            if i > MAX_LINHAS + 50:
                raise ErroArquivo("A planilha passa de %d linhas, o máximo que o plugin guarda." % MAX_LINHAS, 422)
    finally:
        wb.close()
    while linhas and all(v in (None, "") for v in linhas[-1]):
        linhas.pop()
    if not linhas:
        raise ErroArquivo("A planilha está vazia.", 422)
    return _montar(linhas[0], linhas[1:])


def interpretar(nome: str, conteudo: bytes) -> tuple[str, list[str], list[dict]]:
    """(formato, colunas, linhas) de um CSV ou XLSX; qualquer problema vira uma mensagem em português."""
    if not conteudo:
        raise ErroArquivo("O arquivo está vazio.", 422)
    if len(conteudo) > MAX_BYTES:
        raise ErroArquivo("O arquivo tem %.1f MB; o máximo é %d MB." % (len(conteudo) / 1e6, MAX_BYTES // 1_000_000), 422)
    ext = (nome or "").rsplit(".", 1)[-1].lower() if "." in (nome or "") else ""
    if ext == "csv":
        return ("csv",) + _ler_csv(conteudo)
    if ext == "xlsx":
        return ("xlsx",) + _ler_xlsx(conteudo)
    raise ErroArquivo("Só envio arquivos CSV ou XLSX (Excel). O seu parece ser %s." % ("." + ext if ext else "de um tipo desconhecido"), 422)


# =============================================================
# Permissão: área E nível
# =============================================================
def pode_usar(pessoa: Persona, a: ArquivoPlugin) -> bool:
    area_ok = TODAS in a.areas or pessoa.area in a.areas or pessoa.area == a.area_dono
    return area_ok and pessoa.nivel >= a.classificacao


def _nome_area(area: str) -> str:
    return next((p.area_nome for p in PERSONAS.values() if p.area == area), area)


def publico(a: ArquivoPlugin, pessoa: Persona | None = None, previa: bool = False) -> dict:
    d = {"id": a.id, "nome": a.nome, "formato": a.formato, "classificacao": Classificacao(a.classificacao).name.lower(),
         "areas": list(a.areas), "areas_nomes": ["todas as áreas"] if TODAS in a.areas else [_nome_area(x) for x in a.areas],
         "dono": a.dono, "dono_nome": PERSONAS[a.dono].nome if a.dono in PERSONAS else a.dono, "colunas": list(a.colunas),
         "total_linhas": len(a.linhas), "tamanho_bytes": a.tamanho_bytes, "versao": a.versao, "criado_em": a.criado_em,
         "atualizado_em": a.atualizado_em, "atualizado_por": a.atualizado_por, "demo": a.demo,
         "exige_confirmacao_para_escrever": a.classificacao >= Classificacao.CONFIDENCIAL}
    if pessoa is not None:
        d["pode_remover"] = pessoa.id == a.dono
    if previa:
        d["previa"] = list(a.linhas[:TAMANHO_PREVIA])
        d["previa_limite"] = TAMANHO_PREVIA
    return d


# =============================================================
# A tela: enviar, listar, abrir, baixar, remover
# =============================================================
def _validar_publico(pessoa: Persona, classificacao: int, areas: list[str]) -> tuple[int, list[str]]:
    try:
        nivel = Classificacao(int(classificacao))
    except (ValueError, TypeError):
        raise ErroArquivo("Escolha uma classificação: pública, interna, confidencial ou restrita.", 422)
    if nivel > pessoa.nivel:
        raise ErroArquivo("Você não pode classificar um arquivo como %s: o seu nível de acesso é %s." % (
            nivel.name.lower(), pessoa.nivel.name.lower()), 403)
    conhecidas = {p.area for p in PERSONAS.values()}
    if TODAS in areas:
        areas = [TODAS]
    else:
        desconhecidas = [a for a in areas if a not in conhecidas]
        if desconhecidas:
            raise ErroArquivo("Área desconhecida: %s." % ", ".join(desconhecidas), 422)
        areas = sorted(set(areas) | {pessoa.area})     # a área de quem enviou sempre pode usar
    return int(nivel), areas


def enviar(s: Session, pessoa: Persona, nome: str, conteudo: bytes, classificacao: int, areas: list[str], demo: bool = False) -> ArquivoPlugin:
    nome = (nome or "").strip().replace("\\", "/").rsplit("/", 1)[-1][:120]
    if not nome:
        raise ErroArquivo("Dê um nome ao arquivo.", 422)
    nivel, areas = _validar_publico(pessoa, classificacao, areas)
    formato, colunas, linhas = interpretar(nome, conteudo)
    with trava:
        if any(x.nome.lower() == nome.lower() for x in s.exec(select(ArquivoPlugin)).all()):
            raise ErroArquivo("Já existe um arquivo chamado “%s”. Remova o antigo ou escolha outro nome." % nome, 409)
        quando = agora().isoformat()
        a = ArquivoPlugin(id=uuid.uuid4().hex[:10], nome=nome, formato=formato, classificacao=nivel, areas=areas, dono=pessoa.id,
                          area_dono=pessoa.area, colunas=colunas, linhas=linhas, tamanho_bytes=len(conteudo), criado_em=quando,
                          atualizado_em=quando, atualizado_por=pessoa.id, demo=demo)
        s.add(a)
        s.commit()
        s.refresh(a)
    trilha.registrar(s, "arquivo_enviado", pessoa.id, None, {
        "arquivo": a.id, "nome": a.nome, "formato": a.formato, "linhas": len(a.linhas), "colunas": len(a.colunas),
        "classificacao": Classificacao(a.classificacao).name.lower(), "areas": a.areas})
    return a


def enviar_base64(s: Session, pessoa: Persona, nome: str, conteudo_b64: str, classificacao: int, areas: list[str]) -> ArquivoPlugin:
    try:
        bruto = base64.b64decode(conteudo_b64 or "", validate=True)
    except (binascii.Error, ValueError):
        raise ErroArquivo("Não consegui receber o arquivo. Tente enviar de novo.", 422)
    return enviar(s, pessoa, nome, bruto, classificacao, areas)


def listar(s: Session, pessoa: Persona) -> list[ArquivoPlugin]:
    return [a for a in s.exec(select(ArquivoPlugin).order_by(ArquivoPlugin.nome)).all() if pode_usar(pessoa, a)]


def obter(s: Session, pessoa: Persona, arquivo_id: str) -> ArquivoPlugin:
    a = s.get(ArquivoPlugin, arquivo_id)
    if a is None:
        raise ErroArquivo("Arquivo não encontrado.", 404)
    if not pode_usar(pessoa, a):
        trilha.registrar(s, "arquivo_negado", pessoa.id, None, {"arquivo": a.id, "nome": a.nome})
        raise ErroArquivo("Você não tem acesso a este arquivo: ele é %s e das áreas %s." % (
            Classificacao(a.classificacao).name.lower(), ", ".join(_nome_area(x) if x != TODAS else "todas" for x in a.areas)), 403)
    return a


def _formula(v) -> object:
    """Texto que o Excel/CSV leria como fórmula ganha um apóstrofo na exportação (evita injeção de fórmula)."""
    if isinstance(v, str) and v[:1] in ("=", "@", "+", "-") and not re.fullmatch(r"[+-]?\d+([.,]\d+)?", v):
        return "'" + v
    return v


def gerar_arquivo(a: ArquivoPlugin) -> tuple[bytes, str, str]:
    """(conteúdo, tipo MIME, nome do arquivo) da versão ATUAL, no formato em que foi enviado."""
    if a.formato == "xlsx":
        from openpyxl import Workbook
        wb = Workbook()
        ws = wb.active
        ws.title = "Dados"[:31]
        ws.append(list(a.colunas))
        for l in a.linhas:
            ws.append([_formula(l.get(c, "")) for c in a.colunas])
        for linha in ws.iter_rows():
            for c in linha:
                if isinstance(c.value, str):
                    c.data_type = "s"
        buf = io.BytesIO()
        wb.save(buf)
        return buf.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", a.nome
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\r\n")
    w.writerow(a.colunas)
    for l in a.linhas:
        w.writerow([_formula(l.get(c, "")) for c in a.colunas])
    return ("﻿" + buf.getvalue()).encode("utf-8"), "text/csv; charset=utf-8", a.nome


def baixar(s: Session, pessoa: Persona, arquivo_id: str) -> tuple[bytes, str, str]:
    a = obter(s, pessoa, arquivo_id)
    trilha.registrar(s, "arquivo_baixado", pessoa.id, None, {"arquivo": a.id, "nome": a.nome, "versao": a.versao})
    return gerar_arquivo(a)


def remover(s: Session, pessoa: Persona, arquivo_id: str) -> None:
    a = obter(s, pessoa, arquivo_id)
    if a.dono != pessoa.id:
        raise ErroArquivo("Só quem enviou o arquivo pode removê-lo.", 403)
    nome = a.nome
    with trava:
        s.delete(a)
        s.commit()
    trilha.registrar(s, "arquivo_removido", pessoa.id, None, {"arquivo": arquivo_id, "nome": nome})


def criar_pelo_sistema(s: Session, pessoa: Persona, nome: str, colunas: list[str], linhas: list[dict], classificacao: int,
                       areas: list[str], demo: bool = False) -> ArquivoPlugin:
    """Cria um arquivo CSV a partir de linhas já prontas (estado inicial da demo, exportações da plataforma)."""
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\r\n")
    w.writerow(colunas)
    for l in linhas:
        w.writerow([l.get(c, "") for c in colunas])
    return enviar(s, pessoa, nome if nome.lower().endswith((".csv", ".xlsx")) else nome + ".csv", buf.getvalue().encode("utf-8"),
                  classificacao, areas, demo)


# =============================================================
# Ferramentas (o que agentes e processos usam)
# =============================================================
def _sessao(ctx: Contexto) -> Session:
    s = ctx.extras.get("sessao")
    if s is None:
        raise ErroFerramenta("Sem acesso ao banco de arquivos neste contexto.")
    return s


def _pessoa(ctx: Contexto) -> Persona:
    return PERSONAS[ctx.persona_id]


def _resolver(s: Session, pessoa: Persona, ref: str) -> ArquivoPlugin:
    """Acha o arquivo pelo id ou pelo nome. Arquivo que existe mas a pessoa não pode usar é NEGADO (e auditado)."""
    ref = (ref or "").strip()
    todos = s.exec(select(ArquivoPlugin)).all()
    achados = [a for a in todos if a.id == ref] or [a for a in todos if a.nome.lower() == ref.lower()]
    if not achados:
        nomes = [a.nome for a in todos if pode_usar(pessoa, a)]
        raise ErroFerramenta("Não achei o arquivo “%s”. Os que você pode usar: %s." % (ref, ", ".join(nomes) or "nenhum"))
    a = achados[0]
    if not pode_usar(pessoa, a):
        raise AcessoNegado("O arquivo “%s” é %s e das áreas %s; a sua área ou o seu nível de acesso não cobrem." % (
            a.nome, Classificacao(a.classificacao).name.lower(), ", ".join(_nome_area(x) if x != TODAS else "todas" for x in a.areas)))
    return a


def _coluna(a: ArquivoPlugin, nome: str) -> str:
    for c in a.colunas:
        if c.lower() == (nome or "").strip().lower():
            return c
    raise ErroFerramenta("O arquivo “%s” não tem a coluna “%s”. Colunas: %s." % (a.nome, nome, ", ".join(a.colunas)))


def _bate(valor, procurado: str) -> bool:
    return str(valor).strip().lower() == str(procurado).strip().lower()


def _valores(a: ArquivoPlugin, texto: str) -> dict:
    try:
        v = json.loads(texto) if isinstance(texto, str) else texto
    except json.JSONDecodeError:
        raise ErroFerramenta("Os valores precisam vir como um objeto JSON, por exemplo {\"coluna\": \"valor\"}.")
    if not isinstance(v, dict) or not v:
        raise ErroFerramenta("Informe ao menos uma coluna com o valor, por exemplo {\"coluna\": \"valor\"}.")
    saida = {}
    for k, val in v.items():
        saida[_coluna(a, str(k))] = _celula(val) if not isinstance(val, (dict, list)) else str(val)[:MAX_CELULA]
    return saida


def precisa_confirmacao(s: Session, entrada: dict, ctx: Contexto) -> bool:
    """Escrita em arquivo confidencial ou restrito espera um humano. Arquivo inexistente ou negado falha na própria ferramenta."""
    ref = (entrada.get("arquivo") or "").strip().lower()
    a = next((x for x in s.exec(select(ArquivoPlugin)).all() if x.id == entrada.get("arquivo") or x.nome.lower() == ref), None)
    return bool(a and a.classificacao >= Classificacao.CONFIDENCIAL)


def ferramenta_listar(e: dict, ctx: Contexto) -> dict:
    s, p = _sessao(ctx), _pessoa(ctx)
    return {"arquivos": [{"id": a.id, "nome": a.nome, "colunas": list(a.colunas), "linhas": len(a.linhas),
                          "classificacao": Classificacao(a.classificacao).name.lower()} for a in listar(s, p)]}


def ferramenta_ler(e: dict, ctx: Contexto) -> dict:
    s, p = _sessao(ctx), _pessoa(ctx)
    a = _resolver(s, p, e["arquivo"])
    coluna = _coluna(a, e["coluna"]) if e.get("coluna") else None
    achadas = [(i + 1, l) for i, l in enumerate(a.linhas) if coluna is None or _bate(l.get(coluna, ""), e.get("valor", ""))]
    limite = max(1, min(int(e.get("limite", 20)), 100))
    ctx.extras["classificacao_dado"] = a.classificacao
    return {"arquivo": a.nome, "colunas": list(a.colunas), "total_linhas": len(a.linhas), "linhas_encontradas": len(achadas),
            "linhas": [{"linha": n, **l} for n, l in achadas[:limite]]}


def ferramenta_buscar(e: dict, ctx: Contexto) -> dict:
    s, p = _sessao(ctx), _pessoa(ctx)
    a = _resolver(s, p, e["arquivo"])
    coluna = _coluna(a, e["coluna"])
    for i, l in enumerate(a.linhas):
        if _bate(l.get(coluna, ""), e["valor"]):
            ctx.extras["classificacao_dado"] = a.classificacao
            return {"arquivo": a.nome, "encontrada": True, "linha": {"linha": i + 1, **l}}
    return {"arquivo": a.nome, "encontrada": False, "motivo": "Nenhuma linha com %s = %s." % (coluna, e["valor"])}


def _gravar(s: Session, a: ArquivoPlugin, pessoa: Persona, ctx: Contexto, evento: str, linha_n: int, dados: dict) -> None:
    a.versao += 1
    a.atualizado_em, a.atualizado_por = agora().isoformat(), pessoa.id
    s.add(a)
    s.commit()
    s.refresh(a)
    trilha.registrar(s, evento, pessoa.id, ctx.agente_id, {
        "arquivo": a.id, "nome": a.nome, "linha": linha_n, "colunas": sorted(dados), "versao": a.versao,
        "execucao": ctx.execucao_id, "classificacao": Classificacao(a.classificacao).name.lower()}, dono_tipo=ctx.dono_tipo)


def ferramenta_adicionar(e: dict, ctx: Contexto) -> dict:
    s, p = _sessao(ctx), _pessoa(ctx)
    with trava:
        a = _resolver(s, p, e["arquivo"])
        valores = _valores(a, e["valores"])
        if len(a.linhas) >= MAX_LINHAS:
            raise ErroFerramenta("O arquivo já tem %d linhas, o máximo do plugin." % MAX_LINHAS)
        a.linhas = list(a.linhas) + [{c: valores.get(c, "") for c in a.colunas}]
        _gravar(s, a, p, ctx, "arquivo_linha_adicionada", len(a.linhas), valores)
    return {"arquivo": a.nome, "linha": len(a.linhas), "status": "linha acrescentada", "total_linhas": len(a.linhas)}


def ferramenta_atualizar(e: dict, ctx: Contexto) -> dict:
    s, p = _sessao(ctx), _pessoa(ctx)
    with trava:
        a = _resolver(s, p, e["arquivo"])
        chave = _coluna(a, e["coluna_chave"])
        novos = _valores(a, e["valores"])
        indices = [i for i, l in enumerate(a.linhas) if _bate(l.get(chave, ""), e["valor_chave"])]
        if not indices:
            raise ErroFerramenta("Nenhuma linha com %s = %s em “%s”." % (chave, e["valor_chave"], a.nome))
        if len(indices) > 1:
            raise ErroFerramenta("Há %d linhas com %s = %s; use uma coluna que identifique uma linha só." % (len(indices), chave, e["valor_chave"]))
        i = indices[0]
        linhas = [dict(l) for l in a.linhas]
        linhas[i].update(novos)
        a.linhas = linhas
        _gravar(s, a, p, ctx, "arquivo_linha_atualizada", i + 1, novos)
    return {"arquivo": a.nome, "linha": i + 1, "status": "linha atualizada", "colunas_alteradas": sorted(novos)}
