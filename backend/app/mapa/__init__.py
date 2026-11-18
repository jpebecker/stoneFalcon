"""Mapa de IA da Helena: quem criou -> agentes -> plugins/ferramentas -> plataformas (da Stone e externas).

Uma única função monta o grafo a partir do que a plataforma já sabe (agentes publicados, catálogo, plugins integrados,
execuções); a tela consulta de poucos em poucos segundos e anima o que mudou. Nada aqui é gravado: o mapa é só leitura.
"""
from __future__ import annotations

from collections import defaultdict

from sqlmodel import Session, select

from ..agents import modelos as am
from ..agents.blueprint import Blueprint
from ..core.identidade import PERSONAS
from ..llm import precos
from ..observability import metricas
from ..plugins import catalogo as plugins_catalogo
from ..plugins import estado as plugins_estado
from ..runtime import modelos as rm
from ..tools.catalogo import CATALOGO

COLUNAS = [
    {"id": "criadores", "rotulo": "Quem criou"},
    {"id": "agentes", "rotulo": "Agentes publicados"},
    {"id": "ferramentas", "rotulo": "Plugins e ferramentas"},
    {"id": "plataformas", "rotulo": "Plataformas"},
]

# Sistemas da Stone (fictícios) que cada ferramenta interna toca. Plugins apontam para o sistema externo do próprio plugin.
SISTEMA_STONE = {
    "consultar_lojista": ("cadastro", "Cadastro de lojistas"),
    "listar_transacoes": ("transacoes", "Transações e contestações"),
    "listar_chargebacks": ("transacoes", "Transações e contestações"),
    "bloquear_repasse": ("repasses", "Repasses e liquidação"),
    "abrir_chamado": ("chamados", "Central de chamados"),
    "buscar_politica": ("politicas", "Base de políticas"),
    "consultar_colaborador": ("rh", "Cadastro de colaboradores"),
    "consultar_estoque": ("estoque", "Estoque e logística"),
    "enviar_notificacao": ("mensageria", "Mensageria interna"),
}
_PADRAO_STONE = ("outros", "Outros sistemas da Stone")


def _no(id_: str, tipo: str, coluna: str, rotulo: str, **extra) -> dict:
    return {"id": id_, "tipo": tipo, "coluna": coluna, "rotulo": rotulo, **extra}


def grafo(s: Session, dias: int = 7) -> dict:
    execs = metricas.execucoes(s, horas=24 * dias)
    por_agente: dict[str, list[rm.Execucao]] = defaultdict(list)
    for e in execs:
        if e.agente_id:
            por_agente[e.agente_id].append(e)

    agentes = [a for a in s.exec(select(am.Agente).order_by(am.Agente.nome))
               if a.estado in (am.PUBLICADO, am.PAUSADO) and a.versao_publicada is not None]
    nos: dict[str, dict] = {}
    ligacoes: dict[tuple[str, str], int] = defaultdict(int)

    def ligar(de: str, para: str, volume: int) -> None:
        ligacoes[(de, para)] += volume

    for a in agentes:
        v = s.get(am.VersaoAgente, "%s-v%d" % (a.id, a.versao_publicada))
        if v is None:
            continue
        bp = Blueprint.model_validate(v.blueprint)
        feitas = por_agente.get(a.id, [])
        dono = PERSONAS.get(a.dono)
        volume = len(feitas)
        nos["agente:" + a.id] = _no(
            "agente:" + a.id, "agente", "agentes", a.nome, area=a.area, estado=a.estado, risco=a.risco, dono=a.dono,
            execucoes=volume, custo_brl=round(precos.usd_para_brl(sum(e.custo_usd for e in feitas)), 4),
            rota="/agentes/" + a.id, ferramentas=len(bp.ferramentas_usadas()))
        criador = "criador:" + a.dono
        nos.setdefault(criador, _no(criador, "criador", "criadores", dono.nome if dono else a.dono,
                                    area=a.area, detalhe=dono.area_nome if dono else a.area, execucoes=0, custo_brl=0.0))
        nos[criador]["execucoes"] += volume
        ligar(criador, "agente:" + a.id, volume)
        usadas = bp.ferramentas_usadas()
        plugins_usados: set[str] = set()
        for fid in sorted(usadas):
            esp = CATALOGO.get(fid)
            if esp is None:
                continue
            if esp.plugin:
                plugins_usados.add(esp.plugin)
                continue
            fno = "ferramenta:" + fid
            nos.setdefault(fno, _no(fno, "ferramenta", "ferramentas", esp.nome, detalhe=esp.modulo,
                                    classificacao=esp.classificacao.name.lower(), usada_por=0, execucoes=0))
            nos[fno]["usada_por"] += 1
            nos[fno]["execucoes"] += volume
            ligar("agente:" + a.id, fno, volume)
            sid, snome = SISTEMA_STONE.get(fid, _PADRAO_STONE)
            sno = "sistema:" + sid
            nos.setdefault(sno, _no(sno, "sistema", "plataformas", snome, externo=False, execucoes=0))
            nos[sno]["execucoes"] += volume
            ligar(fno, sno, volume)
        for pid in sorted(plugins_usados):
            _plugin(nos, ligar, pid, "agente:" + a.id, volume, a.id)

    # plugins integrados aparecem mesmo sem ninguém usando: integrar (ou remover) muda o mapa
    for pid, p in plugins_catalogo.PLUGINS.items():
        if plugins_estado.integrado(pid):
            _plugin(nos, ligar, pid, None, 0, None)

    lista = list(nos.values())
    return {
        "dias": dias, "colunas": COLUNAS, "nos": lista,
        "ligacoes": [{"de": d, "para": p, "volume": v} for (d, p), v in sorted(ligacoes.items())],
        "totais": {"agentes": sum(1 for n in lista if n["tipo"] == "agente"),
                   "plugins": sum(1 for n in lista if n["tipo"] == "plugin"),
                   "ferramentas": sum(1 for n in lista if n["tipo"] == "ferramenta"),
                   "plataformas": sum(1 for n in lista if n["tipo"] == "sistema"), "execucoes": len(execs)},
        "tem_demo": any(e.demo for e in execs),
    }


def _plugin(nos: dict, ligar, pid: str, agente_no: str | None, volume: int, agente_id: str | None) -> None:
    p = plugins_catalogo.PLUGINS[pid]
    pno = "plugin:" + pid
    nos.setdefault(pno, _no(pno, "plugin", "ferramentas", p.nome, detalhe=p.categoria_nome,
                            integrado=plugins_estado.integrado(pid), classificacao=p.classificacao.name.lower(),
                            usada_por=0, execucoes=0, rota="/plugins/" + pid,
                            ferramentas=[f.nome for f in p.ferramentas]))
    sno = "sistema:ext:" + pid
    nos.setdefault(sno, _no(sno, "sistema", "plataformas", p.nome, externo=True, execucoes=0))
    if agente_no is not None:
        nos[pno]["usada_por"] += 1
        nos[pno]["execucoes"] += volume
        nos[sno]["execucoes"] += volume
        ligar(agente_no, pno, volume)
    ligar(pno, sno, volume)
