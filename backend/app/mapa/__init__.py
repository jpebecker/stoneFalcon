"""Mapa de IA da Helena: quem criou -> agentes -> modelos (por provedor) -> plugins/ferramentas -> plataformas.

Uma única função monta o grafo a partir do que a plataforma já sabe (agentes publicados, catálogo, plugins integrados,
execuções); a tela consulta de poucos em poucos segundos, anima o que mudou e faz um pulso percorrer o caminho de cada
execução nova. Nada aqui é gravado: o mapa é só leitura.
"""
from __future__ import annotations

from collections import defaultdict

from sqlmodel import Session, select

from ..agents import modelos as am
from ..agents.blueprint import Blueprint
from ..agents.governanca import estimar_custo
from ..core.identidade import PERSONAS
from ..llm import precos, registro
from ..observability import metricas
from ..plugins import catalogo as plugins_catalogo
from ..plugins import estado as plugins_estado
from ..runtime import modelos as rm
from ..tools.catalogo import CATALOGO

COLUNAS = [
    {"id": "criadores", "rotulo": "Quem criou"},
    {"id": "agentes", "rotulo": "Agentes publicados"},
    {"id": "modelos", "rotulo": "Modelos"},
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

RECENTES = 12     # execuções na linha do tempo ao lado do mapa


def _no(id_: str, tipo: str, coluna: str, rotulo: str, **extra) -> dict:
    return {"id": id_, "tipo": tipo, "coluna": coluna, "rotulo": rotulo, **extra}


def _modelos_do_agente(feitas: list[rm.Execucao], bp: Blueprint) -> dict[str, dict]:
    """Modelos que o agente usou no período (chamadas e custo); sem execuções, os que a estimativa do agente escolheria."""
    usados: dict[str, dict] = {}
    for e in feitas:
        for chave, v in (e.por_modelo or {}).items():
            if not registro.existe(chave):
                continue
            u = usados.setdefault(registro.obter(chave).chave, {"chamadas": 0, "custo_usd": 0.0})
            u["chamadas"] += v.get("chamadas", 0)
            u["custo_usd"] += v.get("custo_usd", 0.0)
    if not usados:
        for x in estimar_custo(bp).por_passo.values():
            if x.get("modelo_chave"):
                usados.setdefault(x["modelo_chave"], {"chamadas": 0, "custo_usd": 0.0})
    return usados


def grafo(s: Session, dias: int = 7, area: str | None = None, provedor: str | None = None) -> dict:
    execs = metricas.execucoes(s, horas=24 * dias)
    por_agente: dict[str, list[rm.Execucao]] = defaultdict(list)
    for e in execs:
        if e.agente_id:
            por_agente[e.agente_id].append(e)

    todos = [a for a in s.exec(select(am.Agente).order_by(am.Agente.nome))
             if a.estado in (am.PUBLICADO, am.PAUSADO) and a.versao_publicada is not None]
    areas = sorted({a.area for a in todos})
    nos: dict[str, dict] = {}
    ligacoes: dict[tuple[str, str], int] = defaultdict(int)
    caminho_do_agente: dict[str, dict] = {}     # para montar o caminho de cada execução

    def ligar(de: str, para: str, volume: int) -> None:
        ligacoes[(de, para)] += volume

    for a in todos:
        if area and a.area != area:
            continue
        v = s.get(am.VersaoAgente, "%s-v%d" % (a.id, a.versao_publicada))
        if v is None:
            continue
        bp = Blueprint.model_validate(v.blueprint)
        feitas = por_agente.get(a.id, [])
        modelos = _modelos_do_agente(feitas, bp)
        if provedor:
            modelos = {k: u for k, u in modelos.items() if registro.obter(k).provedor == provedor}
            if not modelos:
                continue    # filtro por provedor: só agentes que usam esse provedor
        dono = PERSONAS.get(a.dono)
        volume = len(feitas)
        custo_agente = sum(e.custo_usd for e in feitas)
        ano = "agente:" + a.id
        nos[ano] = _no(ano, "agente", "agentes", a.nome, area=a.area, estado=a.estado, risco=a.risco, dono=a.dono,
                       execucoes=volume, custo_brl=round(precos.usd_para_brl(custo_agente), 4),
                       rota="/agentes/" + a.id, ferramentas=len(bp.ferramentas_usadas()))
        criador = "criador:" + a.dono
        nos.setdefault(criador, _no(criador, "criador", "criadores", dono.nome if dono else a.dono, area=a.area,
                                    detalhe=dono.area_nome if dono else a.area, execucoes=0, custo_brl=0.0))
        nos[criador]["execucoes"] += volume
        nos[criador]["custo_brl"] = round(nos[criador]["custo_brl"] + precos.usd_para_brl(custo_agente), 4)
        ligar(criador, ano, volume)

        # ferramentas e plugins que o agente usa -> plataformas
        alvos: list[str] = []
        plugins_usados: set[str] = set()
        for fid in sorted(bp.ferramentas_usadas()):
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
            sid, snome = SISTEMA_STONE.get(fid, _PADRAO_STONE)
            sno = "sistema:" + sid
            nos.setdefault(sno, _no(sno, "sistema", "plataformas", snome, externo=False, execucoes=0))
            nos[sno]["execucoes"] += volume
            ligar(fno, sno, volume)
            alvos.append(fno)
        for pid in sorted(plugins_usados):
            alvos.append(_plugin(nos, ligar, pid, volume, usado=True))

        # agente -> modelo -> ferramenta (agente sem passo de IA liga direto às ferramentas)
        if modelos:
            for chave, u in modelos.items():
                m = registro.obter(chave)
                mno = "modelo:" + chave
                nos.setdefault(mno, _no(mno, "modelo", "modelos", m.nome, provedor=m.provedor,
                                        provedor_nome=registro.PROVEDORES[m.provedor].nome,
                                        simulado=not registro.roda_de_verdade(chave), execucoes=0, chamadas=0, custo_brl=0.0))
                nos[mno]["chamadas"] += u["chamadas"]
                nos[mno]["execucoes"] += volume
                nos[mno]["custo_brl"] = round(nos[mno]["custo_brl"] + precos.usd_para_brl(u["custo_usd"]), 4)
                ligar(ano, mno, u["chamadas"] or volume)
                for alvo in alvos:
                    ligar(mno, alvo, u["chamadas"] or volume)
        else:
            for alvo in alvos:
                ligar(ano, alvo, volume)
        caminho_do_agente[a.id] = {"alvos": alvos, "bp": bp}

    # plugins integrados aparecem mesmo sem ninguém usando: integrar (ou remover) muda o mapa
    if not area and not provedor:
        for pid in plugins_catalogo.PLUGINS:
            if plugins_estado.integrado(pid):
                _plugin(nos, ligar, pid, 0, usado=False)

    lista = list(nos.values())
    visiveis = {a_id for a_id in caminho_do_agente}
    recentes = _recentes(execs, visiveis, caminho_do_agente, provedor)
    return {
        "dias": dias, "colunas": COLUNAS, "nos": lista,
        "ligacoes": [{"de": d, "para": p, "volume": v} for (d, p), v in sorted(ligacoes.items())],
        "totais": {"agentes": sum(1 for n in lista if n["tipo"] == "agente"),
                   "modelos": sum(1 for n in lista if n["tipo"] == "modelo"),
                   "plugins": sum(1 for n in lista if n["tipo"] == "plugin"),
                   "ferramentas": sum(1 for n in lista if n["tipo"] == "ferramenta"),
                   "plataformas": sum(1 for n in lista if n["tipo"] == "sistema"), "execucoes": len(execs)},
        "filtros": {"area": area, "provedor": provedor, "areas": areas,
                    "provedores": [{"id": p.id, "nome": p.nome} for p in registro.PROVEDORES.values()]},
        "execucoes_recentes": recentes,
        "tem_demo": any(e.demo for e in execs),
    }


def _plugin(nos: dict, ligar, pid: str, volume: int, usado: bool) -> str:
    p = plugins_catalogo.PLUGINS[pid]
    pno = "plugin:" + pid
    nos.setdefault(pno, _no(pno, "plugin", "ferramentas", p.nome, detalhe=p.categoria_nome,
                            integrado=plugins_estado.integrado(pid), classificacao=p.classificacao.name.lower(),
                            usada_por=0, execucoes=0, rota="/plugins/" + pid, ferramentas=[f.nome for f in p.ferramentas]))
    sno = "sistema:ext:" + pid
    nos.setdefault(sno, _no(sno, "sistema", "plataformas", p.nome, externo=True, execucoes=0))
    if usado:
        nos[pno]["usada_por"] += 1
        nos[pno]["execucoes"] += volume
        nos[sno]["execucoes"] += volume
    ligar(pno, sno, volume)
    return pno


def _sistema_de(alvo: str) -> str:
    """Nó de plataforma a que uma ferramenta ou plugin leva."""
    if alvo.startswith("plugin:"):
        return "sistema:ext:" + alvo.split(":", 1)[1]
    return "sistema:" + SISTEMA_STONE.get(alvo.split(":", 1)[1], _PADRAO_STONE)[0]


def _recentes(execs: list[rm.Execucao], visiveis: set[str], caminhos: dict[str, dict], provedor: str | None) -> list[dict]:
    """As últimas execuções, cada uma com o caminho que o pulso percorre: agente -> modelo -> ferramenta -> plataforma.
    `ordem` (0, 1, 2) diz em que etapa a aresta acende, para os pulsos saírem em sequência."""
    saida = []
    for e in sorted((x for x in execs if x.agente_id in visiveis), key=lambda x: (x.inicio, x.id), reverse=True)[:RECENTES]:
        ano = "agente:" + e.agente_id
        usados = [registro.obter(k).chave for k in (e.por_modelo or {}) if registro.existe(k)]
        if provedor:
            usados = [k for k in usados if registro.obter(k).provedor == provedor]
        alvos = caminhos[e.agente_id]["alvos"]
        arestas: list[list] = []
        if usados:
            for k in usados:
                arestas.append([ano, "modelo:" + k, 0])
                arestas += [["modelo:" + k, alvo, 1] for alvo in alvos]
        else:
            arestas += [[ano, alvo, 1] for alvo in alvos]
        arestas += [[alvo, _sistema_de(alvo), 2] for alvo in alvos]
        saida.append({"id": e.id, "agente_id": e.agente_id, "agente": e.agente_nome, "status": e.status, "quando": e.inicio,
                      "custo_brl": round(precos.usd_para_brl(e.custo_usd), 5), "rotina": bool(getattr(e, "rotina", False)),
                      "modelos": [registro.obter(k).nome for k in usados], "demo": e.demo, "arestas": arestas})
    return saida
