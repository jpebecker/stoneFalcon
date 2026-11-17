"""Regras do marketplace: integrar, pedir, aprovar, remover e a visão consolidada de cada plugin.

Marketplace é a camada de aquisição; o Catálogo continua sendo a de governança:
  - plugin público/interno: criador (da área do plugin) ou Engenharia integram direto;
  - plugin confidencial/restrito: vira PEDIDO na fila de Revisões do Lucas (quatro olhos: ninguém aprova o próprio);
    como a Segurança tem um revisor só, o pedido feito por ela é decidido pelo CoE de IA (Helena);
  - quem não cria nem governa só REGISTRA o pedido.
Tudo que muda vai para a trilha de auditoria; o resultado de um pedido chega ao solicitante como alerta.
"""
from __future__ import annotations

import uuid
from collections import defaultdict

from sqlmodel import Session, select

from ..agents import ciclo
from ..agents import modelos as am
from ..agents.blueprint import Blueprint
from ..audit import trilha
from ..core.db import trava
from ..core.identidade import CRIADOR, ENGENHARIA_PLATAFORMA, GESTOR_IA, PERSONAS, REVISOR_SEGURANCA, Persona
from ..core.relogio import agora
from ..llm import precos
from ..observability import alertas, metricas
from ..runtime import modelos as rm
from ..tools import executor
from ..tools.catalogo import CATALOGO
from . import estado as cache
from . import sistemas as sx
from .catalogo import PLUGINS, Plugin, obter, usados_por
from .modelos import APROVADO, PENDENTE, RECUSADO, REGISTRADO, IntegracaoPlugin, PedidoPlugin

REGRA_ALERTA = "plugin_pedido"            # alertas do marketplace: não fecham sozinhos na reavaliação periódica
REGRA_ALERTA_REMOVIDO = "plugin_removido"


class ErroPlugin(Exception):
    def __init__(self, mensagem: str, status: int = 409):
        super().__init__(mensagem)
        self.status = status


# ---------------------------------------------------------------- estado
def sincronizar(s: Session) -> None:
    """Recarrega o cache de plugins integrados a partir do banco (partida, depois de cada mudança, depois do reinício)."""
    cache.INTEGRADOS.clear()
    cache.INTEGRADOS.update(i.plugin_id for i in s.exec(select(IntegracaoPlugin)))


def zerar() -> None:
    cache.zerar()
    sx.zerar()


def _plugin(plugin_id: str) -> Plugin:
    p = obter(plugin_id)
    if p is None:
        raise ErroPlugin("Plugin não encontrado.", 404)
    return p


def _pedidos(s: Session, plugin_id: str | None = None) -> list[PedidoPlugin]:
    q = select(PedidoPlugin)
    if plugin_id:
        q = q.where(PedidoPlugin.plugin_id == plugin_id)
    return list(s.exec(q.order_by(PedidoPlugin.criado_em)))


def pedido_pendente(s: Session, plugin_id: str) -> PedidoPlugin | None:
    return next((p for p in _pedidos(s, plugin_id) if p.estado == PENDENTE), None)


def pode_integrar(pessoa: Persona, p: Plugin) -> bool:
    """Criadores integram para a própria área (só plugins homologados para ela); a Engenharia integra qualquer um."""
    return pessoa.tem(ENGENHARIA_PLATAFORMA) or (pessoa.tem(CRIADOR) and p.vale_para(pessoa))


def pode_decidir(pessoa: Persona, ped: PedidoPlugin) -> bool:
    """Quatro olhos: quem pediu nunca decide. A Segurança decide os pedidos; o pedido feito pela própria Segurança
    (não há segundo revisor na demo) é decidido pelo CoE de IA."""
    if ped.estado != PENDENTE or ped.solicitante == pessoa.id:
        return False
    if pessoa.tem(REVISOR_SEGURANCA):
        return True
    solicitante = PERSONAS.get(ped.solicitante)
    return pessoa.tem(GESTOR_IA) and solicitante is not None and solicitante.tem(REVISOR_SEGURANCA)


def estado_do_plugin(s: Session, p: Plugin) -> str:
    if p.id in cache.INTEGRADOS:
        return "integrado"
    return "aguardando_aprovacao" if pedido_pendente(s, p.id) else "disponivel"


def _ferramenta(esp, pessoa: Persona) -> dict:
    from ..tools.permissoes import avaliar
    # a ferramenta só roda se o nível de quem dispara cobre a classificação: mostramos isso mesmo antes de integrar
    nivel_ok = pessoa.nivel >= esp.classificacao
    return {"id": esp.id, "nome": esp.nome, "descricao": esp.descricao, "acao": esp.acao,
            "classificacao": esp.classificacao.name.lower(), "exige_aprovacao": esp.exige_aprovacao,
            "parametros": esp.parametros, "obrigatorios": list(esp.obrigatorios),
            "nivel_suficiente": nivel_ok,
            "disponivel_para_mim": avaliar(pessoa, esp).permitido}


def publico(s: Session, p: Plugin, pessoa: Persona) -> dict:
    estado = estado_do_plugin(s, p)
    integracao = s.get(IntegracaoPlugin, p.id)
    meu = next((x for x in reversed(_pedidos(s, p.id)) if x.solicitante == pessoa.id), None)
    pend = pedido_pendente(s, p.id)
    vale = p.vale_para(pessoa)
    pode = pode_integrar(pessoa, p)
    return {
        "id": p.id, "nome": p.nome, "categoria": p.categoria, "categoria_nome": p.categoria_nome, "descricao": p.descricao,
        "simulado": True, "janela": p.janela, "classificacao": p.classificacao.name.lower(), "sensivel": p.sensivel,
        "areas": ["todas"] if "*" in p.areas else list(p.areas),
        "areas_nomes": ["todas as áreas"] if "*" in p.areas else sorted({x.area_nome for x in PERSONAS.values() if x.area in p.areas}),
        "estado": estado, "vale_para_minha_area": vale,
        "ferramentas": [_ferramenta(f, pessoa) for f in p.ferramentas],
        "exige_aprovacao_para_integrar": p.sensivel,
        "integrado_por": PERSONAS[integracao.integrado_por].nome if integracao and integracao.integrado_por in PERSONAS else None,
        "integrado_em": integracao.quando if integracao else None,
        # o que a pessoa pode fazer com este plugin agora
        "pode_integrar": pode and estado == "disponivel",
        "pode_pedir": (not pode) and estado == "disponivel",
        "pode_remover": estado == "integrado" and (pessoa.tem(ENGENHARIA_PLATAFORMA) or
                                                   (integracao is not None and integracao.integrado_por == pessoa.id)),
        "pedido_pendente": ({"id": pend.id, "solicitante": PERSONAS[pend.solicitante].nome, "meu": pend.solicitante == pessoa.id,
                             "pode_decidir": pode_decidir(pessoa, pend)} if pend else None),
        "meu_pedido": ({"id": meu.id, "estado": meu.estado, "parecer": meu.parecer,
                        "revisor": PERSONAS[meu.revisor].nome if meu.revisor else None} if meu else None),
    }


def listar(s: Session, pessoa: Persona) -> list[dict]:
    return [publico(s, p, pessoa) for p in PLUGINS.values()]


# ---------------------------------------------------------------- integrar / remover
def _integrar_agora(s: Session, p: Plugin, por: Persona, origem: str) -> IntegracaoPlugin:
    with trava:
        i = IntegracaoPlugin(plugin_id=p.id, integrado_por=por.id, area=por.area, quando=agora().isoformat(), origem=origem)
        s.add(i)
        s.commit()
    sincronizar(s)
    for esp in p.ferramentas:
        executor.estado(s, esp.id)   # a ferramenta passa a ter estado de operação (saúde, falha simulada)
    trilha.registrar(s, "plugin_integrado", por.id, dados={
        "plugin": p.id, "nome": p.nome, "classificacao": p.classificacao.name.lower(), "origem": origem,
        "ferramentas": [f.id for f in p.ferramentas], "area": por.area})
    _fechar_alertas_remocao(s, p.id)
    return i


def integrar(s: Session, pessoa: Persona, plugin_id: str, motivo: str = "") -> dict:
    """Plugin público/interno: integra na hora. Confidencial/restrito: abre um pedido para a Segurança."""
    p = _plugin(plugin_id)
    # checar e gravar sob a mesma trava (reentrante): dois cliques seguidos não integram nem pedem duas vezes
    with trava:
        if s.get(IntegracaoPlugin, p.id) is not None:
            raise ErroPlugin("Este plugin já está integrado.")
        if pedido_pendente(s, p.id):
            raise ErroPlugin("Já existe um pedido de integração aguardando a Segurança.")
        if not pode_integrar(pessoa, p):
            raise ErroPlugin("Seu perfil não integra este plugin: %s Use \"Pedir integração\"." % (
                "ele não é homologado para a sua área." if not p.vale_para(pessoa) else "só criadores e a Engenharia integram."), 403)
        if p.sensivel:
            ped = _criar_pedido(s, pessoa, p, PENDENTE, motivo or "Integração de %s para a área %s." % (p.nome, pessoa.area_nome))
            dados = ped.model_dump()   # antes do alerta: o commit dele expira o objeto
            if pessoa.tem(REVISOR_SEGURANCA):   # pedido da própria Segurança: o CoE de IA decide (e fica sabendo)
                for gestor in (x for x in PERSONAS.values() if x.tem(GESTOR_IA)):
                    _avisar(s, gestor.id, "Pedido de integração do %s espera a sua decisão" % p.nome,
                            "%s (Segurança) pediu o plugin %s; como quem pede não decide, o parecer é do CoE de IA."
                            % (pessoa.nome, p.nome), "decidir:" + dados["id"], "atencao")
            return {"resultado": "pedido", "pedido": dados}
        _integrar_agora(s, p, pessoa, "direta")
    return {"resultado": "integrado"}


def pedir(s: Session, pessoa: Persona, plugin_id: str, motivo: str = "") -> dict:
    """Quem não pode integrar só registra o desejo (nenhum fluxo de aprovação é aberto)."""
    p = _plugin(plugin_id)
    if p.id in cache.INTEGRADOS:
        raise ErroPlugin("Este plugin já está integrado.")
    if pode_integrar(pessoa, p):
        raise ErroPlugin("O seu perfil integra este plugin diretamente: use \"Integrar\".")
    ped = _criar_pedido(s, pessoa, p, REGISTRADO, motivo or "Pedido de integração de %s." % p.nome)
    return {"resultado": "registrado", "pedido": ped.model_dump()}


def _criar_pedido(s: Session, pessoa: Persona, p: Plugin, estado: str, motivo: str) -> PedidoPlugin:
    with trava:
        ped = PedidoPlugin(id=uuid.uuid4().hex[:12], plugin_id=p.id, solicitante=pessoa.id, area=pessoa.area, motivo=motivo,
                           estado=estado, criado_em=agora().isoformat())
        s.add(ped)
        s.commit()
        s.refresh(ped)
    trilha.registrar(s, "plugin_pedido_criado" if estado == PENDENTE else "plugin_pedido_registrado", pessoa.id, dados={
        "pedido": ped.id, "plugin": p.id, "nome": p.nome, "estado": estado, "area": pessoa.area,
        "classificacao": p.classificacao.name.lower(), "ferramentas": [f.id for f in p.ferramentas]})
    s.refresh(ped)   # o commit da auditoria expira o objeto
    return ped


def decidir(s: Session, revisor: Persona, pedido_id: str, aprovar: bool, parecer: str) -> dict:
    if not (revisor.tem(REVISOR_SEGURANCA) or revisor.tem(GESTOR_IA)):
        raise ErroPlugin("Só a Segurança decide pedidos de integração.", 403)
    if not parecer.strip():
        raise ErroPlugin("Escreva o parecer: ele aparece para quem pediu.", 422)
    # ler, conferir e decidir sob a mesma trava: dois cliques em "Aprovar" decidem (e integram) uma vez só
    with trava:
        ped = s.get(PedidoPlugin, pedido_id)
        if ped is None:
            raise ErroPlugin("Pedido não encontrado.", 404)
        s.refresh(ped)   # o estado pode ter mudado em outra requisição
        if ped.estado != PENDENTE:
            raise ErroPlugin("Este pedido já foi decidido.")
        if ped.solicitante == revisor.id:   # quatro olhos
            raise ErroPlugin("Você fez este pedido: quem pede não decide (quatro olhos). %s" % (
                "O CoE de IA decide os pedidos da Segurança." if revisor.tem(REVISOR_SEGURANCA) else ""), 403)
        if not pode_decidir(revisor, ped):
            raise ErroPlugin("Só a Segurança decide pedidos de integração (o CoE de IA só decide os pedidos feitos pela Segurança).", 403)
        p = _plugin(ped.plugin_id)
        solicitante = PERSONAS[ped.solicitante]
        ped.estado, ped.revisor, ped.parecer, ped.decidido_em = (APROVADO if aprovar else RECUSADO), revisor.id, parecer.strip(), agora().isoformat()
        s.add(ped)
        s.commit()
        s.refresh(ped)
        trilha.registrar(s, "plugin_pedido_aprovado" if aprovar else "plugin_pedido_recusado", revisor.id, dados={
            "pedido": ped.id, "plugin": p.id, "nome": p.nome, "solicitante": ped.solicitante, "parecer": ped.parecer})
        if aprovar and s.get(IntegracaoPlugin, p.id) is None:
            _integrar_agora(s, p, solicitante, "pedido:" + ped.id)
    _avisar(s, solicitante.id, "Integração do %s %s" % (p.nome, "aprovada" if aprovar else "recusada"),
            "%s: %s" % (revisor.nome, ped.parecer), ped.id, "atencao")
    s.refresh(ped)
    return ped.model_dump()


def remover(s: Session, pessoa: Persona, plugin_id: str) -> dict:
    p = _plugin(plugin_id)
    i = s.get(IntegracaoPlugin, p.id)
    if i is None:
        raise ErroPlugin("Este plugin não está integrado.")
    if not (pessoa.tem(ENGENHARIA_PLATAFORMA) or i.integrado_por == pessoa.id):
        raise ErroPlugin("Só quem integrou o plugin ou a Engenharia o removem.", 403)
    afetados = agentes_que_usam(s, p)
    with trava:
        s.delete(i)
        s.commit()
    sincronizar(s)
    trilha.registrar(s, "plugin_removido", pessoa.id, dados={
        "plugin": p.id, "nome": p.nome, "ferramentas": [f.id for f in p.ferramentas],
        "agentes_afetados": [a.id for a in afetados]})
    # agentes que usam as ferramentas ficam sinalizados (não quebram em silêncio): alerta ao dono e à Engenharia
    engenharia = [x.id for x in PERSONAS.values() if x.tem(ENGENHARIA_PLATAFORMA)]
    for a in afetados:
        _avisar(s, a.dono, "Plugin %s removido: %s depende dele" % (p.nome, a.nome),
                "As ferramentas de %s saíram do Catálogo. O agente \"%s\" vai escalar para humano até o plugin ser integrado de novo "
                "ou o passo ser trocado." % (p.nome, a.nome), "%s:%s" % (p.id, a.id), "atencao",
                regra=REGRA_ALERTA_REMOVIDO, agente_id=a.id, extras=engenharia)
    return {"resultado": "removido", "agentes_afetados": [{"id": a.id, "nome": a.nome} for a in afetados]}


# ---------------------------------------------------------------- agentes que usam um plugin
def _blueprint_atual(s: Session, a: am.Agente) -> Blueprint | None:
    numero = a.versao_publicada or a.ultima_versao
    v = s.get(am.VersaoAgente, "%s-v%d" % (a.id, numero))
    return Blueprint.model_validate(v.blueprint) if v else None


def agentes_que_usam(s: Session, p: Plugin) -> list[am.Agente]:
    ids = {f.id for f in p.ferramentas}
    saida = []
    for a in s.exec(select(am.Agente).where(am.Agente.estado != am.DEPRECIADO)):
        bp = _blueprint_atual(s, a)
        if bp and bp.ferramentas_usadas() & ids:
            saida.append(a)
    return saida


def plugins_indisponiveis(s: Session, a: am.Agente) -> list[dict]:
    """Plugins de que o agente depende e que NÃO estão integrados (sinalização na lista e na página do agente)."""
    bp = _blueprint_atual(s, a)
    if bp is None:
        return []
    return [{"id": pid, "nome": PLUGINS[pid].nome} for pid in sorted(usados_por(bp.ferramentas_usadas()) - cache.INTEGRADOS)
            if pid in PLUGINS]


# ---------------------------------------------------------------- alertas do marketplace
def _avisar(s: Session, destino: str, titulo: str, detalhe: str, chave: str, severidade: str,
            regra: str = REGRA_ALERTA, agente_id: str | None = None, extras: list[str] | None = None) -> None:
    agora_iso = agora().isoformat()
    s.add(alertas.Alerta(id=uuid.uuid4().hex[:12], chave="%s:%s" % (regra, chave), regra=regra, severidade=severidade,
                         agente_id=agente_id, titulo=titulo, detalhe=detalhe,
                         destinatarios=sorted({destino, *(extras or [])}), lido_por=[], aberto_em=agora_iso,
                         atualizado_em=agora_iso))
    s.commit()
    trilha.registrar(s, "alerta_aberto", "sistema", agente_id, {"regra": regra, "titulo": titulo, "destinatarios": [destino, *(extras or [])]})


def _fechar_alertas_remocao(s: Session, plugin_id: str) -> None:
    for a in s.exec(select(alertas.Alerta).where(alertas.Alerta.regra == REGRA_ALERTA_REMOVIDO)
                    .where(alertas.Alerta.resolvido_em.is_(None))):
        if a.chave.startswith("%s:%s:" % (REGRA_ALERTA_REMOVIDO, plugin_id)):
            a.resolvido_em = a.atualizado_em = agora().isoformat()
            s.add(a)
    s.commit()


# ---------------------------------------------------------------- fila de pedidos (Revisões)
def fila_para(s: Session, pessoa: Persona) -> list[dict]:
    """Segurança: todos os pedidos pendentes. CoE de IA: os pendentes feitos pela Segurança. Todos: os próprios pedidos."""
    def entra(x: PedidoPlugin) -> bool:
        if pessoa.tem(REVISOR_SEGURANCA):
            return x.estado == PENDENTE
        return x.solicitante == pessoa.id or pode_decidir(pessoa, x)
    pedidos = [x for x in _pedidos(s) if entra(x)]
    return [_pedido_publico(x, pessoa) for x in reversed(pedidos)]


def _pedido_publico(x: PedidoPlugin, pessoa: Persona) -> dict:
    p = PLUGINS[x.plugin_id]
    d = x.model_dump()
    d.update({"plugin_nome": p.nome, "categoria_nome": p.categoria_nome, "classificacao": p.classificacao.name.lower(),
              "ferramentas": [{"id": f.id, "nome": f.nome, "acao": f.acao} for f in p.ferramentas],
              "solicitante_nome": PERSONAS[x.solicitante].nome, "area_nome": PERSONAS[x.solicitante].area_nome,
              "e_meu": x.solicitante == pessoa.id, "pode_decidir": pode_decidir(pessoa, x),
              "revisor_nome": PERSONAS[x.revisor].nome if x.revisor else None})
    return d


# ---------------------------------------------------------------- página consolidada
def consolidado(s: Session, pessoa: Persona, plugin_id: str) -> dict:
    p = _plugin(plugin_id)
    if p.id not in cache.INTEGRADOS:
        raise ErroPlugin("Só plugins integrados têm página consolidada.")
    ids = {f.id for f in p.ferramentas}
    uso = metricas.chamadas_ferramentas(s, horas=24 * 30)
    por_ferramenta = []
    chamadas = erros = 0
    lat_p95 = 0
    for f in p.ferramentas:
        u = uso.get(f.id, {"chamadas": 0, "erros": 0, "taxa_erro": 0.0, "latencia_p50_ms": 0, "latencia_p95_ms": 0})
        chamadas += u["chamadas"]
        erros += u["erros"]
        lat_p95 = max(lat_p95, u["latencia_p95_ms"])
        por_ferramenta.append({"id": f.id, "nome": f.nome, "acao": f.acao, "chamadas": u["chamadas"], "erros": u["erros"],
                               "taxa_erro": u["taxa_erro"], "latencia_tipica_ms": f.latencia_ms,
                               "latencia_p95_ms": u["latencia_p95_ms"], "falha": executor.estado(s, f.id).falha})
    # custo: das execuções que chamaram o plugin (os tokens do modelo; a chamada ao sistema externo não custa token).
    # Mesma janela de 30 dias das chamadas; a contagem por agente sai dos mesmos eventos (cada agente, as próprias chamadas).
    execucoes_ids = set()
    contagem: dict[str, int] = defaultdict(int)
    from ..audit.trilha import EventoAuditoria
    for e in s.exec(select(EventoAuditoria).where(EventoAuditoria.tipo.in_(metricas.EVENTOS_FERRAMENTA))
                    .where(EventoAuditoria.quando >= metricas._desde(24 * 30))):
        if e.dados.get("conector") not in ids:
            continue
        if e.agente_id:
            contagem[e.agente_id] += 1
        if e.dados.get("execucao"):
            execucoes_ids.add(e.dados["execucao"])
    custo_usd = sum(x.custo_usd for x in s.exec(select(rm.Execucao).where(rm.Execucao.id.in_(execucoes_ids)))) if execucoes_ids else 0.0
    usam = agentes_que_usam(s, p)
    usam_visiveis = [a for a in usam if ciclo.pode_ver(pessoa, a)]
    abertos = [a for a in s.exec(select(alertas.Alerta).where(alertas.Alerta.resolvido_em.is_(None))) if a.conector in ids]
    status = "fora" if any(a.regra == "conector_fora" for a in abertos) else "lento" if abertos else "ok"
    nivel_ok = pessoa.nivel >= p.classificacao
    # conteúdo do sistema externo: os mesmos dois eixos das ferramentas (nível E área); o CoE de IA vê todas as áreas
    area_ok = p.vale_para(pessoa) or pessoa.tem(GESTOR_IA)
    return {
        "plugin": publico(s, p, pessoa), "simulado": True, "nivel_suficiente": nivel_ok, "area_permitida": area_ok,
        "numeros": {"agentes": len(usam), "chamadas_mes": chamadas, "erros": erros,
                    "custo_brl": round(precos.usd_para_brl(custo_usd), 4), "execucoes": len(execucoes_ids),
                    "latencia_p95_ms": lat_p95},
        "saude": {"status": status, "alertas": [{"id": a.id, "regra": a.regra, "severidade": a.severidade, "titulo": a.titulo,
                                                 "detalhe": a.detalhe, "conector": a.conector} for a in abertos],
                  "por_ferramenta": por_ferramenta},
        "agentes": [{"id": a.id, "nome": a.nome, "area": a.area, "estado": a.estado,
                     "chamadas": contagem.get(a.id, 0)} for a in usam_visiveis],
        "agentes_ocultos": len(usam) - len(usam_visiveis),
        # conteúdo do sistema externo só para quem tem nível para a classificação do plugin e é da área dele (ou do CoE)
        "janela": _janela(s, p) if (p.janela and nivel_ok and area_ok) else None,
    }


def _nome_agente(s: Session, agente_id: str | None) -> str | None:
    if not agente_id:
        return None
    if agente_id == "sandbox":
        return "Teste no Estúdio"
    a = s.get(am.Agente, agente_id)
    return a.nome if a else None


def _autor(s: Session, agente_id: str | None, persona_id: str) -> str:
    """Quem escreveu no sistema externo: o agente (com a pessoa que o disparou) ou a própria pessoa."""
    pessoa = PERSONAS[persona_id].nome if persona_id in PERSONAS else persona_id
    nome = _nome_agente(s, agente_id)
    return "%s (agente, disparado por %s)" % (nome, pessoa) if nome else pessoa


def _janela(s: Session, p: Plugin) -> dict:
    if p.id == "zendesk":
        return {"tipo": "fila", "titulo": "Fila de chamados · Atendimento", "itens": [
            {"id": c["id"], "assunto": c["assunto"], "solicitante": c["solicitante"], "prioridade": c["prioridade"],
             "status": c["status"], "mensagem": c["texto"],
             "respostas": [{"autor": _autor(s, r["agente_id"], r["autor"]), "texto": r["texto"]} for r in c["respostas"]]}
            for c in sx.ZENDESK]}
    if p.id == "slack":
        canais = []
        for nome in sx.CANAIS_SLACK:
            msgs = [m for m in sx.SLACK if m["canal"] == nome]
            canais.append({"canal": nome, "mensagens": [{"id": m["id"], "texto": m["mensagem"],
                                                         "autor": _autor(s, m["agente_id"], m["enviado_por"])} for m in msgs]})
        return {"tipo": "canais", "titulo": "Canais do Slack", "canais": canais}
    if p.id == "jira":
        colunas = {"A fazer": [], "Em andamento": [], "Concluído": []}
        for i in sx.JIRA:
            colunas.setdefault(i["status"], []).append({"id": i["id"], "titulo": i["titulo"], "projeto": i["projeto"]})
        return {"tipo": "quadro", "titulo": "Quadro · LOG e ENG", "colunas": [{"nome": k, "itens": v} for k, v in colunas.items()]}
    return {"tipo": "vazio", "titulo": p.nome}
