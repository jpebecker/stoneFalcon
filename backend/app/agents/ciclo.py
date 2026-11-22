"""Ciclo de vida de agentes e processos: criação -> modificações -> publicação -> execuções -> deprecação.

Regras de governança (todas registradas na trilha encadeada):
  - só quem tem papel de criador cria, e só com ferramentas que ele mesmo pode usar;
  - a versão publicada é imutável: editar gera uma versão nova em rascunho;
  - TODA versão de risco alto passa pela revisão da Segurança antes de publicar,
    feita por alguém que não é o autor (quatro olhos);
  - a Segurança e o CoE podem pausar qualquer agente ou processo na hora (botão de emergência);
  - o que foi depreciado não executa nem volta: o histórico fica para auditoria.

A lógica é uma só para os dois tipos de dono (`Ciclo`, parametrizado por `TipoDono`). As funções do módulo
(`criar`, `editar`, `publicar`...) são o ciclo do AGENTE; o ciclo do processo está em app/processos/tipo.py.
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
from .dono import AGENTE, Dono, TipoDono, registrar_tipo
from .governanca import ALTO, avaliar_risco, ferramentas_sem_permissao


class ErroCiclo(Exception):
    def __init__(self, mensagem: str, status: int = 409):
        super().__init__(mensagem)
        self.status = status


def _slug(nome: str, padrao: str = "agente") -> str:
    t = unicodedata.normalize("NFD", nome.lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")[:40] or padrao


def _salvar(s: Session, *objs) -> None:
    with trava:
        for o in objs:
            s.add(o)
        s.commit()
        for o in objs:
            s.refresh(o)


def _normalizar_agente(s: Session, p: Persona, bp: Blueprint) -> Blueprint:
    """v8: uma versão nova de agente é UM trabalhador (uma tarefa). Fluxos de vários passos são processos."""
    if len(bp.passos) > 1:
        raise ErroCiclo("Um agente faz uma tarefa só (%d passos não cabem). Para encadear passos, aprovações e ações em outros "
                        "sistemas, monte um processo na aba Processos e use este agente como um bloco dele." % len(bp.passos), 422)
    return bp.model_copy(update={"area": p.area})


# O tipo AGENTE: como se avalia, se compara e se executa o blueprint dele.
TIPO_AGENTE = registrar_tipo(TipoDono(
    nome=AGENTE, entidade=m.Agente, versao_cls=m.VersaoAgente, fk="agente_id", modelo=Blueprint, slug_padrao="agente",
    risco=lambda s, bp: avaliar_risco(bp),
    sem_permissao=lambda s, p, bp: ferramentas_sem_permissao(p, bp),
    comparar=comparar, ferramentas_novas=ferramentas_novas,
    executavel=lambda s, p, dono, bp: Blueprint.model_validate(bp), normalizar=_normalizar_agente,
))


class Ciclo:
    """Ciclo de vida versionado de um tipo de dono (agente ou processo)."""

    def __init__(self, tipo: TipoDono):
        self.t = tipo
        self.r = tipo.nome

    # ---------- leitura ----------
    def obter(self, s: Session, dono_id: str):
        a = s.get(self.t.entidade, dono_id)
        if a is None:
            raise ErroCiclo("%s não encontrado." % self.t.rotulo, 404)
        return a

    def versao(self, s: Session, dono_id: str, numero: int):
        v = s.get(self.t.versao_cls, self.t.versao_id(dono_id, numero))
        if v is None:
            raise ErroCiclo("Versão não encontrada.", 404)
        return v

    def versoes(self, s: Session, dono_id: str) -> list:
        vc = self.t.versao_cls
        return list(s.exec(select(vc).where(getattr(vc, self.t.fk) == dono_id).order_by(vc.numero.desc())))

    def blueprint_publicado(self, s: Session, a):
        if a.versao_publicada is None:
            raise ErroCiclo("Este %s ainda não tem versão publicada." % self.r)
        return self.t.modelo.model_validate(self.versao(s, a.id, a.versao_publicada).blueprint)

    def pode_ver(self, p: Persona, a) -> bool:
        return (p.area == a.area or p.area in (a.compartilhado_com or []) or p.id == a.dono
                or p.tem(GESTOR_IA) or p.tem(REVISOR_SEGURANCA))

    def pode_executar(self, p: Persona, a) -> bool:
        return p.area == a.area or p.area in (a.compartilhado_com or []) or p.id == a.dono

    def _pode_editar(self, p: Persona, a) -> None:
        if not (p.id == a.dono or (p.tem(CRIADOR) and p.area == a.area)):
            raise ErroCiclo("Só criadores da área %s podem alterar este %s." % (a.area, self.r), 403)

    # ---------- auxiliares ----------
    def _preparar(self, s: Session, p: Persona, bp):
        bp = self.t.normalizar(s, p, bp) if self.t.normalizar else bp.model_copy(update={"area": p.area})
        proibidas = self.t.sem_permissao(s, p, bp)
        if proibidas:
            raise ErroCiclo("O %s usa ferramentas que o seu perfil não pode usar: %s." % (self.r, "; ".join(proibidas.values())), 422)
        return bp

    def _evento(self, s: Session, tipo: str, ator: str, dono_id: str, dados: dict) -> None:
        trilha.registrar(s, "%s_%s" % (self.r, tipo), ator, dono_id, dados, dono_tipo=self.r)

    # ---------- criação e modificação ----------
    def criar(self, s: Session, p: Persona, bp, nota: str = ""):
        if not p.tem(CRIADOR):
            raise ErroCiclo("Seu perfil não cria %s." % self.t.plural, 403)
        bp = self._preparar(s, p, bp)
        agora_iso = agora().isoformat()
        dono_id = "%s-%s" % (_slug(bp.nome, self.t.slug_padrao), uuid.uuid4().hex[:4])
        risco = self.t.risco(s, bp).nivel
        extras = self.t.extras_criacao(bp) if self.t.extras_criacao else {}
        a = self.t.entidade(id=dono_id, nome=bp.nome, area=p.area, dono=p.id, estado=m.RASCUNHO, ultima_versao=1,
                            risco=risco, compartilhado_com=[], criado_em=agora_iso, atualizado_em=agora_iso, **extras)
        v = self.t.versao_cls(**{"id": dono_id + "-v1", self.t.fk: dono_id, "numero": 1, "blueprint": bp.model_dump(),
                                 "nota": nota or "Criado no Estúdio.", "autor": p.id, "criada_em": agora_iso, "risco": risco})
        _salvar(s, a, v)
        self._evento(s, "criado", p.id, dono_id, {"versao": 1, "nome": bp.nome, "risco": risco})
        return a

    def editar(self, s: Session, p: Persona, dono_id: str, bp, nota: str = ""):
        a = self.obter(s, dono_id)
        self._pode_editar(p, a)
        if a.estado == m.DEPRECIADO:
            raise ErroCiclo("%s depreciado não pode ser alterado." % self.t.rotulo)
        ultima = self.versao(s, a.id, a.ultima_versao)
        if ultima.estado == m.V_EM_REVISAO:
            raise ErroCiclo("Há uma versão em revisão pela Segurança. Aguarde o parecer para editar.")
        bp = self._preparar(s, p, bp)
        risco = self.t.risco(s, bp).nivel
        mudancas = self.t.comparar(ultima.blueprint, bp.model_dump())
        if not mudancas:
            return ultima
        agora_iso = agora().isoformat()
        if ultima.estado == m.V_RASCUNHO:      # continua o mesmo rascunho
            ultima.blueprint, ultima.risco, ultima.criada_em = bp.model_dump(), risco, agora_iso
            ultima.nota = nota or ultima.nota
            v = ultima
        else:                                   # publicada, rejeitada ou substituída: abre versão nova
            n = a.ultima_versao + 1
            v = self.t.versao_cls(**{"id": self.t.versao_id(a.id, n), self.t.fk: a.id, "numero": n, "blueprint": bp.model_dump(),
                                     "nota": nota or "Alteração no Estúdio.", "autor": p.id, "criada_em": agora_iso, "risco": risco})
            a.ultima_versao = n
        a.nome, a.atualizado_em = bp.nome, agora_iso
        if self.t.extras_criacao:               # campos próprios do tipo acompanham a edição (ex.: processo do AS IS)
            for k, val in self.t.extras_criacao(bp).items():
                setattr(a, k, val)
        _salvar(s, a, v)
        self._evento(s, "modificado", p.id, a.id, {
            "versao": v.numero, "risco": risco, "mudancas": len(mudancas),
            "resumo": [("%s %s %s" % (x["tipo"], x["alvo"], x["campo"] or "")).strip() for x in mudancas[:12]],
            "ferramentas_novas": sorted(self.t.ferramentas_novas(ultima.blueprint, bp.model_dump()))})
        return v

    # ---------- publicação e revisão ----------
    def _publicar_versao(self, s: Session, a, v, ator: str) -> None:
        agora_iso = agora().isoformat()
        if a.versao_publicada is not None:
            anterior = self.versao(s, a.id, a.versao_publicada)
            anterior.estado = m.V_SUBSTITUIDA
            s.add(anterior)
        v.estado, v.publicada_em = m.V_PUBLICADA, agora_iso
        a.versao_publicada, a.risco, a.atualizado_em, a.motivo_estado = v.numero, v.risco, agora_iso, None
        if a.estado in (m.RASCUNHO, m.EM_REVISAO):
            a.estado = m.PUBLICADO
        _salvar(s, a, v)
        self._evento(s, "publicado", ator, a.id, {"versao": v.numero, "risco": v.risco, "revisor": v.revisor})

    def publicar(self, s: Session, p: Persona, dono_id: str):
        a = self.obter(s, dono_id)
        self._pode_editar(p, a)
        if a.estado == m.DEPRECIADO:
            raise ErroCiclo("%s depreciado não pode ser publicado." % self.t.rotulo)
        v = self.versao(s, a.id, a.ultima_versao)
        if v.estado != m.V_RASCUNHO:
            raise ErroCiclo("Não há rascunho para publicar (última versão: %s)." % v.estado)
        if self.t.antes_de_publicar:
            self.t.antes_de_publicar(s, self.t.modelo.model_validate(v.blueprint))
        if v.risco == ALTO:
            v.estado = m.V_EM_REVISAO
            if a.versao_publicada is None:
                a.estado = m.EM_REVISAO
            a.atualizado_em = agora().isoformat()
            _salvar(s, a, v)
            self._evento(s, "enviado_revisao", p.id, a.id, {
                "versao": v.numero, "motivos": self.t.risco(s, self.t.modelo.model_validate(v.blueprint)).motivos})
            return a
        self._publicar_versao(s, a, v, p.id)
        return a

    def revisar(self, s: Session, p: Persona, dono_id: str, aprovar: bool, parecer: str):
        if not p.tem(REVISOR_SEGURANCA):
            raise ErroCiclo("Só a Segurança revisa %s." % self.t.plural, 403)
        a = self.obter(s, dono_id)
        v = self.versao(s, a.id, a.ultima_versao)
        if v.estado != m.V_EM_REVISAO:
            raise ErroCiclo("Não há versão esperando revisão.")
        if v.autor == p.id:
            raise ErroCiclo("Quem escreveu a versão não pode revisá-la.", 403)
        if not parecer.strip():
            raise ErroCiclo("Escreva um parecer: ele fica registrado para o criador e para a auditoria.", 422)
        v.revisor, v.parecer, v.revisada_em = p.id, parecer.strip(), agora().isoformat()
        trilha.registrar(s, "revisao_aprovada" if aprovar else "revisao_rejeitada", p.id, a.id,
                         {"versao": v.numero, "parecer": v.parecer}, dono_tipo=self.r)
        if aprovar:
            self._publicar_versao(s, a, v, p.id)
        else:
            v.estado = m.V_REJEITADA
            if a.versao_publicada is None:
                a.estado = m.RASCUNHO
            a.atualizado_em = agora().isoformat()
            _salvar(s, a, v)
        return a

    def pendentes_revisao(self, s: Session) -> list[tuple]:
        vs = s.exec(select(self.t.versao_cls).where(self.t.versao_cls.estado == m.V_EM_REVISAO)).all()
        return [(self.obter(s, getattr(v, self.t.fk)), v) for v in vs]

    # ---------- operação ----------
    def pode_operar(self, p: Persona, a) -> bool:
        """Pode pausar, retomar e operar `a`: o dono, um criador da área, o CoE de IA ou a Segurança."""
        return p.id == a.dono or (p.tem(CRIADOR) and p.area == a.area) or p.tem(GESTOR_IA) or p.tem(REVISOR_SEGURANCA)

    def _pode_operar(self, p: Persona, a) -> None:
        if not self.pode_operar(p, a):
            raise ErroCiclo("Seu perfil não pode mudar o estado deste %s." % self.r, 403)

    def pausar(self, s: Session, p: Persona, dono_id: str, motivo: str = ""):
        a = self.obter(s, dono_id)
        self._pode_operar(p, a)
        if a.estado != m.PUBLICADO:
            raise ErroCiclo("Só %s publicados podem ser pausados." % self.t.plural)
        a.estado, a.motivo_estado, a.atualizado_em = m.PAUSADO, motivo or None, agora().isoformat()
        _salvar(s, a)
        self._evento(s, "pausado", p.id, a.id, {"motivo": motivo})
        return a

    def retomar(self, s: Session, p: Persona, dono_id: str):
        a = self.obter(s, dono_id)
        self._pode_operar(p, a)
        if a.estado != m.PAUSADO:
            raise ErroCiclo("O %s não está pausado." % self.r)
        a.estado, a.motivo_estado, a.atualizado_em = m.PUBLICADO, None, agora().isoformat()
        _salvar(s, a)
        self._evento(s, "retomado", p.id, a.id, {})
        return a

    def depreciar(self, s: Session, p: Persona, dono_id: str, motivo: str):
        a = self.obter(s, dono_id)
        if not (p.id == a.dono or p.tem(GESTOR_IA)):
            raise ErroCiclo("Só o dono do %s ou o CoE de IA podem depreciá-lo." % self.r, 403)
        if a.estado == m.DEPRECIADO:
            raise ErroCiclo("O %s já está depreciado." % self.r)
        if not motivo.strip():
            raise ErroCiclo("Informe o motivo da deprecação.", 422)
        a.estado, a.motivo_estado, a.atualizado_em = m.DEPRECIADO, motivo.strip(), agora().isoformat()
        _salvar(s, a)
        self._evento(s, "depreciado", p.id, a.id, {"motivo": motivo.strip()})
        return a

    def compartilhar(self, s: Session, p: Persona, dono_id: str, areas: list[str]):
        a = self.obter(s, dono_id)
        self._pode_editar(p, a)
        a.compartilhado_com = sorted({x for x in areas if x and x != a.area})
        a.atualizado_em = agora().isoformat()
        _salvar(s, a)
        self._evento(s, "compartilhado", p.id, a.id, {"areas": a.compartilhado_com})
        return a

    def checar_execucao(self, s: Session, p: Persona, dono_id: str):
        a = self.obter(s, dono_id)
        if not self.pode_executar(p, a):
            trilha.registrar(s, "execucao_negada", p.id, a.id, {"motivo": "área sem acesso ao %s" % self.r}, dono_tipo=self.r)
            raise ErroCiclo("A área %s não tem acesso a este %s." % (p.area_nome, self.r), 403)
        if a.estado != m.PUBLICADO:
            raise ErroCiclo({"pausado": "O %s está pausado%s." % (self.r, ": " + a.motivo_estado if a.motivo_estado else ""),
                             "depreciado": "O %s foi depreciado e não executa mais." % self.r}.get(
                                 a.estado, "O %s ainda não foi publicado." % self.r))
        from ..finance.resumo import gasto_no_mes
        gasto = gasto_no_mes(s, a.id) if self.r == AGENTE else gasto_no_mes(s, a.id, self.r)
        if a.orcamento_mensal_brl and gasto >= a.orcamento_mensal_brl:
            trilha.registrar(s, "execucao_negada", p.id, a.id, {"motivo": "orçamento mensal atingido", "gasto_brl": gasto},
                             dono_tipo=self.r)
            raise ErroCiclo("O %s atingiu o orçamento do mês (R$ %.2f de R$ %.2f). Peça ao dono ou ao CoE para revisar."
                            % (self.r, gasto, a.orcamento_mensal_brl), 402)
        if a.versao_publicada is None:
            raise ErroCiclo("Este %s ainda não tem versão publicada." % self.r)
        bruto = self.versao(s, a.id, a.versao_publicada).blueprint
        return a, self.t.executavel(s, p, Dono(self.r, a.id, a.versao_publicada), bruto)

    def definir_orcamento(self, s: Session, p: Persona, dono_id: str, valor_brl: float):
        a = self.obter(s, dono_id)
        if not (p.id == a.dono or p.tem(GESTOR_IA)):
            raise ErroCiclo("Só o dono do %s ou o CoE de IA definem o orçamento." % self.r, 403)
        if valor_brl < 0:
            raise ErroCiclo("O orçamento não pode ser negativo.", 422)
        anterior = a.orcamento_mensal_brl
        a.orcamento_mensal_brl, a.atualizado_em = round(valor_brl, 2), agora().isoformat()
        _salvar(s, a)
        trilha.registrar(s, "orcamento_definido", p.id, a.id, {"de": anterior, "para": a.orcamento_mensal_brl}, dono_tipo=self.r)
        return a


# ---------- o ciclo do AGENTE (a API de sempre) ----------
_A = Ciclo(TIPO_AGENTE)
ciclo = _A   # o objeto Ciclo do agente, para quem trata agente e processo do mesmo jeito (ex.: observability/tratamento.py)
obter, versao, versoes, blueprint_publicado = _A.obter, _A.versao, _A.versoes, _A.blueprint_publicado
pode_ver, pode_executar = _A.pode_ver, _A.pode_executar
criar, editar, publicar, revisar, pendentes_revisao = _A.criar, _A.editar, _A.publicar, _A.revisar, _A.pendentes_revisao
pausar, retomar, depreciar, compartilhar = _A.pausar, _A.retomar, _A.depreciar, _A.compartilhar
checar_execucao, definir_orcamento = _A.checar_execucao, _A.definir_orcamento
