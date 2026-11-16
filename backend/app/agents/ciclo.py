"""Ciclo de vida dos agentes: criação -> modificações -> publicação -> execuções -> deprecação.

Regras de governança (todas registradas na trilha encadeada):
  - só quem tem papel de criador cria, e só com ferramentas que ele mesmo pode usar;
  - a versão publicada é imutável: editar gera uma versão nova em rascunho;
  - TODA versão de risco alto passa pela revisão da Segurança antes de publicar,
    feita por alguém que não é o autor (quatro olhos);
  - a Segurança e o CoE podem pausar qualquer agente na hora (botão de emergência);
  - agente depreciado não executa nem volta: o histórico fica para auditoria.
"""
from __future__ import annotations

import re
import unicodedata
import uuid

from sqlmodel import Session, select

from ..audit import trilha
from ..core.db import trava
from ..core.identidade import CRIADOR, GESTOR_IA, REVISOR_SEGURANCA, Persona
from ..core.relogio import agora
from . import modelos as m
from .blueprint import Blueprint
from .diff import comparar, ferramentas_novas
from .governanca import ALTO, avaliar_risco, ferramentas_sem_permissao


class ErroCiclo(Exception):
    def __init__(self, mensagem: str, status: int = 409):
        super().__init__(mensagem)
        self.status = status


# ---------- leitura ----------
def obter(s: Session, agente_id: str) -> m.Agente:
    a = s.get(m.Agente, agente_id)
    if a is None:
        raise ErroCiclo("Agente não encontrado.", 404)
    return a


def versao(s: Session, agente_id: str, numero: int) -> m.VersaoAgente:
    v = s.get(m.VersaoAgente, "%s-v%d" % (agente_id, numero))
    if v is None:
        raise ErroCiclo("Versão não encontrada.", 404)
    return v


def versoes(s: Session, agente_id: str) -> list[m.VersaoAgente]:
    return list(s.exec(select(m.VersaoAgente).where(m.VersaoAgente.agente_id == agente_id)
                       .order_by(m.VersaoAgente.numero.desc())))


def blueprint_publicado(s: Session, a: m.Agente) -> Blueprint:
    if a.versao_publicada is None:
        raise ErroCiclo("Este agente ainda não tem versão publicada.")
    return Blueprint.model_validate(versao(s, a.id, a.versao_publicada).blueprint)


def pode_ver(p: Persona, a: m.Agente) -> bool:
    return (p.area == a.area or p.area in (a.compartilhado_com or []) or p.id == a.dono
            or p.tem(GESTOR_IA) or p.tem(REVISOR_SEGURANCA))


def pode_executar(p: Persona, a: m.Agente) -> bool:
    return p.area == a.area or p.area in (a.compartilhado_com or []) or p.id == a.dono


def _pode_editar(p: Persona, a: m.Agente) -> None:
    if not (p.id == a.dono or (p.tem(CRIADOR) and p.area == a.area)):
        raise ErroCiclo("Só criadores da área %s podem alterar este agente." % a.area, 403)


# ---------- auxiliares ----------
def _slug(nome: str) -> str:
    t = unicodedata.normalize("NFD", nome.lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")[:40] or "agente"


def _preparar(p: Persona, bp: Blueprint) -> Blueprint:
    bp = bp.model_copy(update={"area": p.area})
    proibidas = ferramentas_sem_permissao(p, bp)
    if proibidas:
        raise ErroCiclo("O agente usa ferramentas que o seu perfil não pode usar: %s." % "; ".join(proibidas.values()), 422)
    return bp


def _salvar(s: Session, *objs) -> None:
    with trava:
        for o in objs:
            s.add(o)
        s.commit()
        for o in objs:
            s.refresh(o)


# ---------- criação e modificação ----------
def criar(s: Session, p: Persona, bp: Blueprint, nota: str = "") -> m.Agente:
    if not p.tem(CRIADOR):
        raise ErroCiclo("Seu perfil não cria agentes.", 403)
    bp = _preparar(p, bp)
    agora_iso = agora().isoformat()
    agente_id = "%s-%s" % (_slug(bp.nome), uuid.uuid4().hex[:4])
    risco = avaliar_risco(bp).nivel
    a = m.Agente(id=agente_id, nome=bp.nome, area=p.area, dono=p.id, estado=m.RASCUNHO, ultima_versao=1,
                 risco=risco, compartilhado_com=[], criado_em=agora_iso, atualizado_em=agora_iso)
    v = m.VersaoAgente(id=agente_id + "-v1", agente_id=agente_id, numero=1, blueprint=bp.model_dump(),
                       nota=nota or "Criado no Estúdio.", autor=p.id, criada_em=agora_iso, risco=risco)
    _salvar(s, a, v)
    trilha.registrar(s, "agente_criado", p.id, agente_id, {"versao": 1, "nome": bp.nome, "risco": risco})
    return a


def editar(s: Session, p: Persona, agente_id: str, bp: Blueprint, nota: str = "") -> m.VersaoAgente:
    a = obter(s, agente_id)
    _pode_editar(p, a)
    if a.estado == m.DEPRECIADO:
        raise ErroCiclo("Agente depreciado não pode ser alterado.")
    ultima = versao(s, a.id, a.ultima_versao)
    if ultima.estado == m.V_EM_REVISAO:
        raise ErroCiclo("Há uma versão em revisão pela Segurança. Aguarde o parecer para editar.")
    bp = _preparar(p, bp)
    risco = avaliar_risco(bp).nivel
    mudancas = comparar(ultima.blueprint, bp.model_dump())
    if not mudancas:
        return ultima
    agora_iso = agora().isoformat()
    if ultima.estado == m.V_RASCUNHO:      # continua o mesmo rascunho
        ultima.blueprint, ultima.risco, ultima.criada_em = bp.model_dump(), risco, agora_iso
        ultima.nota = nota or ultima.nota
        v = ultima
    else:                                   # publicada, rejeitada ou substituída: abre versão nova
        n = a.ultima_versao + 1
        v = m.VersaoAgente(id="%s-v%d" % (a.id, n), agente_id=a.id, numero=n, blueprint=bp.model_dump(),
                           nota=nota or "Alteração no Estúdio.", autor=p.id, criada_em=agora_iso, risco=risco)
        a.ultima_versao = n
    a.nome, a.atualizado_em = bp.nome, agora_iso
    _salvar(s, a, v)
    trilha.registrar(s, "agente_modificado", p.id, a.id, {
        "versao": v.numero, "risco": risco, "mudancas": len(mudancas),
        "resumo": [("%s %s %s" % (x["tipo"], x["alvo"], x["campo"] or "")).strip() for x in mudancas[:12]],
        "ferramentas_novas": sorted(ferramentas_novas(ultima.blueprint, bp.model_dump()))})
    return v


# ---------- publicação e revisão ----------
def _publicar_versao(s: Session, a: m.Agente, v: m.VersaoAgente, ator: str) -> None:
    agora_iso = agora().isoformat()
    if a.versao_publicada is not None:
        anterior = versao(s, a.id, a.versao_publicada)
        anterior.estado = m.V_SUBSTITUIDA
        s.add(anterior)
    v.estado, v.publicada_em = m.V_PUBLICADA, agora_iso
    a.versao_publicada, a.risco, a.atualizado_em, a.motivo_estado = v.numero, v.risco, agora_iso, None
    if a.estado in (m.RASCUNHO, m.EM_REVISAO):
        a.estado = m.PUBLICADO
    _salvar(s, a, v)
    trilha.registrar(s, "agente_publicado", ator, a.id, {"versao": v.numero, "risco": v.risco, "revisor": v.revisor})


def publicar(s: Session, p: Persona, agente_id: str) -> m.Agente:
    a = obter(s, agente_id)
    _pode_editar(p, a)
    if a.estado == m.DEPRECIADO:
        raise ErroCiclo("Agente depreciado não pode ser publicado.")
    v = versao(s, a.id, a.ultima_versao)
    if v.estado != m.V_RASCUNHO:
        raise ErroCiclo("Não há rascunho para publicar (última versão: %s)." % v.estado)
    if v.risco == ALTO:
        v.estado = m.V_EM_REVISAO
        if a.versao_publicada is None:
            a.estado = m.EM_REVISAO
        a.atualizado_em = agora().isoformat()
        _salvar(s, a, v)
        trilha.registrar(s, "agente_enviado_revisao", p.id, a.id, {
            "versao": v.numero, "motivos": avaliar_risco(Blueprint.model_validate(v.blueprint)).motivos})
        return a
    _publicar_versao(s, a, v, p.id)
    return a


def revisar(s: Session, p: Persona, agente_id: str, aprovar: bool, parecer: str) -> m.Agente:
    if not p.tem(REVISOR_SEGURANCA):
        raise ErroCiclo("Só a Segurança revisa agentes.", 403)
    a = obter(s, agente_id)
    v = versao(s, a.id, a.ultima_versao)
    if v.estado != m.V_EM_REVISAO:
        raise ErroCiclo("Não há versão esperando revisão.")
    if v.autor == p.id:
        raise ErroCiclo("Quem escreveu a versão não pode revisá-la.", 403)
    if not parecer.strip():
        raise ErroCiclo("Escreva um parecer: ele fica registrado para o criador e para a auditoria.", 422)
    v.revisor, v.parecer, v.revisada_em = p.id, parecer.strip(), agora().isoformat()
    trilha.registrar(s, "revisao_aprovada" if aprovar else "revisao_rejeitada", p.id, a.id,
                     {"versao": v.numero, "parecer": v.parecer})
    if aprovar:
        _publicar_versao(s, a, v, p.id)
    else:
        v.estado = m.V_REJEITADA
        if a.versao_publicada is None:
            a.estado = m.RASCUNHO
        a.atualizado_em = agora().isoformat()
        _salvar(s, a, v)
    return a


def pendentes_revisao(s: Session) -> list[tuple[m.Agente, m.VersaoAgente]]:
    vs = s.exec(select(m.VersaoAgente).where(m.VersaoAgente.estado == m.V_EM_REVISAO)).all()
    return [(obter(s, v.agente_id), v) for v in vs]


# ---------- operação ----------
def _pode_operar(p: Persona, a: m.Agente) -> None:
    if not (p.id == a.dono or (p.tem(CRIADOR) and p.area == a.area) or p.tem(GESTOR_IA) or p.tem(REVISOR_SEGURANCA)):
        raise ErroCiclo("Seu perfil não pode mudar o estado deste agente.", 403)


def pausar(s: Session, p: Persona, agente_id: str, motivo: str = "") -> m.Agente:
    a = obter(s, agente_id)
    _pode_operar(p, a)
    if a.estado != m.PUBLICADO:
        raise ErroCiclo("Só agentes publicados podem ser pausados.")
    a.estado, a.motivo_estado, a.atualizado_em = m.PAUSADO, motivo or None, agora().isoformat()
    _salvar(s, a)
    trilha.registrar(s, "agente_pausado", p.id, a.id, {"motivo": motivo})
    return a


def retomar(s: Session, p: Persona, agente_id: str) -> m.Agente:
    a = obter(s, agente_id)
    _pode_operar(p, a)
    if a.estado != m.PAUSADO:
        raise ErroCiclo("O agente não está pausado.")
    a.estado, a.motivo_estado, a.atualizado_em = m.PUBLICADO, None, agora().isoformat()
    _salvar(s, a)
    trilha.registrar(s, "agente_retomado", p.id, a.id, {})
    return a


def depreciar(s: Session, p: Persona, agente_id: str, motivo: str) -> m.Agente:
    a = obter(s, agente_id)
    if not (p.id == a.dono or p.tem(GESTOR_IA)):
        raise ErroCiclo("Só o dono do agente ou o CoE de IA podem depreciá-lo.", 403)
    if a.estado == m.DEPRECIADO:
        raise ErroCiclo("O agente já está depreciado.")
    if not motivo.strip():
        raise ErroCiclo("Informe o motivo da deprecação.", 422)
    a.estado, a.motivo_estado, a.atualizado_em = m.DEPRECIADO, motivo.strip(), agora().isoformat()
    _salvar(s, a)
    trilha.registrar(s, "agente_depreciado", p.id, a.id, {"motivo": motivo.strip()})
    return a


def compartilhar(s: Session, p: Persona, agente_id: str, areas: list[str]) -> m.Agente:
    a = obter(s, agente_id)
    _pode_editar(p, a)
    a.compartilhado_com = sorted({x for x in areas if x and x != a.area})
    a.atualizado_em = agora().isoformat()
    _salvar(s, a)
    trilha.registrar(s, "agente_compartilhado", p.id, a.id, {"areas": a.compartilhado_com})
    return a


def checar_execucao(s: Session, p: Persona, agente_id: str) -> tuple[m.Agente, Blueprint]:
    a = obter(s, agente_id)
    if not pode_executar(p, a):
        trilha.registrar(s, "execucao_negada", p.id, a.id, {"motivo": "área sem acesso ao agente"})
        raise ErroCiclo("A área %s não tem acesso a este agente." % p.area_nome, 403)
    if a.estado != m.PUBLICADO:
        raise ErroCiclo({"pausado": "O agente está pausado%s." % (": " + a.motivo_estado if a.motivo_estado else ""),
                         "depreciado": "O agente foi depreciado e não executa mais."}.get(
                             a.estado, "O agente ainda não foi publicado."))
    from ..finance.resumo import gasto_no_mes
    gasto = gasto_no_mes(s, a.id)
    if a.orcamento_mensal_brl and gasto >= a.orcamento_mensal_brl:
        trilha.registrar(s, "execucao_negada", p.id, a.id, {"motivo": "orçamento mensal atingido", "gasto_brl": gasto})
        raise ErroCiclo("O agente atingiu o orçamento do mês (R$ %.2f de R$ %.2f). Peça ao dono ou ao CoE para revisar."
                        % (gasto, a.orcamento_mensal_brl), 402)
    return a, blueprint_publicado(s, a)


def definir_orcamento(s: Session, p: Persona, agente_id: str, valor_brl: float) -> m.Agente:
    a = obter(s, agente_id)
    if not (p.id == a.dono or p.tem(GESTOR_IA)):
        raise ErroCiclo("Só o dono do agente ou o CoE de IA definem o orçamento.", 403)
    if valor_brl < 0:
        raise ErroCiclo("O orçamento não pode ser negativo.", 422)
    anterior = a.orcamento_mensal_brl
    a.orcamento_mensal_brl, a.atualizado_em = round(valor_brl, 2), agora().isoformat()
    _salvar(s, a)
    trilha.registrar(s, "orcamento_definido", p.id, a.id, {"de": anterior, "para": a.orcamento_mensal_brl})
    return a
