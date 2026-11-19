"""Tarefas de rotina (v7, v8): um criador dá a um agente ou a um PROCESSO publicado uma agenda ("toda segunda às 9h") com uma
entrada fixa.

A plataforma dispara sozinha. A execução é uma execução como qualquer outra: mesmas permissões (as de QUEM AGENDOU),
mesmos guardrails, mesmo orçamento (ciclo.checar_execucao) e mesma trilha. Ação sensível dentro da rotina fica
aguardando confirmação humana, sem executar sozinha. Na demo, um RELÓGIO ACELERADO e o botão "Rodar agora" mostram
isso sem esperar até segunda-feira. Reiniciar a demo apaga as agendas e volta o relógio.
"""
from __future__ import annotations

import json
import logging
import threading
import time
import uuid
from datetime import datetime, timedelta

from sqlmodel import Session, select

from .. import guardrails
from ..agents import ciclo
from ..agents import modelos as am
from ..audit import trilha
from ..core.db import trava
from ..core.identidade import CRIADOR, PERSONAS, Persona
from ..agents.dono import PROCESSO, Dono
from ..core.relogio import FUSO
from ..observability import avaliar_seguro
from ..processos import modelos as pm
from ..processos.tipo import ciclo as ciclo_processos
from ..runtime import motor
from .modelos import Rotina, RotinaExecucao

DIAS = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"]
_FEMININO = {0, 1, 2, 3, 4}          # "toda segunda", mas "todo sábado"
MAX_POR_AGENTE = 10
_log = logging.getLogger("stonefalcon.rotinas")
FREQUENCIAS = ("diaria", "semanal")


class ErroRotina(Exception):
    def __init__(self, mensagem: str, status: int = 400):
        super().__init__(mensagem)
        self.status = status


# =============================================================
# Relógio das rotinas (só a agenda usa: auditoria e métricas seguem o relógio real)
# =============================================================
class Relogio:
    """Hora das rotinas. Normal: a hora de verdade. Na demo: acelerado (fator), com saltos (avancar) ou fixo (fixar)."""

    def __init__(self) -> None:
        self._trava = threading.Lock()
        self.zerar()

    def zerar(self) -> None:
        with self._trava:
            self._real0 = time.time()
            self._demo0 = datetime.now(FUSO).replace(microsecond=0)
            self.fator = 1.0

    def agora(self) -> datetime:
        with self._trava:
            return (self._demo0 + timedelta(seconds=(time.time() - self._real0) * self.fator)).replace(microsecond=0)

    def avancar(self, delta: timedelta) -> None:
        with self._trava:
            self._demo0 += delta

    def acelerar(self, fator: float) -> None:
        agora = self.agora()
        with self._trava:
            self._demo0, self._real0, self.fator = agora, time.time(), fator

    def fixar(self, quando: datetime) -> None:
        """Relógio parado em `quando` (testes e ensaio: nada dispara até alguém avançar)."""
        with self._trava:
            self._demo0, self._real0, self.fator = quando.astimezone(FUSO), time.time(), 0.0


relogio = Relogio()
_trava_tick = threading.Lock()


def zerar() -> None:
    """Reiniciar a demo: o relógio volta ao normal (as agendas somem junto com o banco)."""
    relogio.zerar()


# =============================================================
# Agenda
# =============================================================
def descricao(r: Rotina) -> str:
    hora = "%02d:%02d" % (r.hora, r.minuto)
    if r.frequencia == "diaria":
        return "todo dia às %s" % hora
    return "%s %s às %s" % ("toda" if r.dia_semana in _FEMININO else "todo", DIAS[r.dia_semana], hora)


def proxima_depois(r: Rotina, referencia: datetime) -> datetime:
    """Próximo disparo ESTRITAMENTE depois de `referencia`."""
    cand = referencia.replace(hour=r.hora, minute=r.minuto, second=0, microsecond=0)
    if r.frequencia == "semanal":
        cand += timedelta(days=(r.dia_semana - cand.weekday()) % 7)
    if cand <= referencia:
        cand += timedelta(days=7 if r.frequencia == "semanal" else 1)
    return cand


def _dt(iso: str) -> datetime:
    return datetime.fromisoformat(iso)


def publica(s: Session, r: Rotina) -> dict:
    s.refresh(r)          # a auditoria faz commit e expira o objeto: recarrega antes de serializar
    d = r.model_dump()
    d["descricao"] = descricao(r)
    return d


def _obter(s: Session, rotina_id: str) -> Rotina:
    r = s.get(Rotina, rotina_id)
    if r is None:
        raise ErroRotina("Rotina não encontrada.", 404)
    return r


def _ciclo(tipo: str):
    """O ciclo de vida do dono da rotina: o módulo dos agentes ou o `Ciclo` dos processos (mesma interface)."""
    return ciclo_processos if tipo == PROCESSO else ciclo


def _pode_gerir(p: Persona, r: Rotina, a) -> bool:
    return p.id == r.dono or p.id == a.dono or (p.tem(CRIADOR) and p.area == a.area)


def _pode_rodar(p: Persona, r: Rotina) -> bool:
    return p.id == r.dono


def _agente(s: Session, agente_id: str, tipo: str = "agente"):
    """Agente ou processo da rotina; erro do ciclo vira erro de rotina (a API só converte ErroRotina em resposta HTTP)."""
    try:
        return _ciclo(tipo).obter(s, agente_id)
    except ciclo.ErroCiclo as e:
        raise ErroRotina(str(e), e.status)


def _exigir_gestao(s: Session, p: Persona, r: Rotina, acao: str = "gerem"):
    a = _agente(s, r.agente_id, r.dono_tipo)
    if not _pode_gerir(p, r, a):
        raise ErroRotina("Só quem agendou ou os criadores da área %s esta rotina." % acao, 403)
    return a


def _salvar(s: Session, r: Rotina) -> None:
    with trava:
        s.add(r)
        s.commit()
        s.refresh(r)


# =============================================================
# Criar, pausar, retomar, remover
# =============================================================
def criar(s: Session, pessoa: Persona, agente_id: str, frequencia: str, dia_semana: int | None, hora: int, minuto: int,
          entrada: dict, tipo: str = "agente") -> Rotina:
    if frequencia not in FREQUENCIAS:
        raise ErroRotina("A frequência é diária ou semanal.", 422)
    if frequencia == "semanal" and (dia_semana is None or not 0 <= dia_semana <= 6):
        raise ErroRotina("Escolha o dia da semana.", 422)
    if not (0 <= hora <= 23 and 0 <= minuto <= 59):
        raise ErroRotina("Horário inválido.", 422)
    c = _ciclo(tipo)
    a = _agente(s, agente_id, tipo)
    if a.estado != am.PUBLICADO:
        raise ErroRotina("Só %s publicados têm rotina." % ("processos" if tipo == PROCESSO else "agentes"), 409)
    if not (pessoa.tem(CRIADOR) and c.pode_executar(pessoa, a)):
        raise ErroRotina("Só criadores com acesso ao %s agendam rotinas." % ("processo" if tipo == PROCESSO else "agente"), 403)
    bp = c.blueprint_publicado(s, a)
    faltando = [c for c in bp.ids_campos() if entrada.get(c) in (None, "")]
    if faltando:
        raise ErroRotina("Preencha a entrada fixa: %s." % ", ".join(faltando), 422)
    mapa: dict[str, str] = {}
    guardrails.mascarar(json.dumps(entrada, ensure_ascii=False), mapa)
    if mapa:
        raise ErroRotina("A entrada fixa de uma rotina não pode ter dado pessoal (CPF, e-mail, telefone...).", 422)
    if len(s.exec(select(Rotina).where(Rotina.agente_id == agente_id)).all()) >= MAX_POR_AGENTE:
        raise ErroRotina("Este %s já tem %d rotinas." % ("processo" if tipo == PROCESSO else "agente", MAX_POR_AGENTE), 409)
    agora = relogio.agora()
    r = Rotina(id=uuid.uuid4().hex[:10], agente_id=agente_id, dono_tipo=tipo, dono=pessoa.id, frequencia=frequencia,
               dia_semana=dia_semana if frequencia == "semanal" else None, hora=hora, minuto=minuto,
               entrada={k: entrada[k] for k in bp.ids_campos() if k in entrada}, criada_em=agora.isoformat())
    r.proxima_em = proxima_depois(r, agora).isoformat()
    _salvar(s, r)
    trilha.registrar(s, "rotina_criada", pessoa.id, agente_id, {"rotina": r.id, "agenda": descricao(r), "proxima_em": r.proxima_em},
                     dono_tipo=tipo)
    return r


def pausar(s: Session, pessoa: Persona, rotina_id: str) -> Rotina:
    r = _obter(s, rotina_id)
    _exigir_gestao(s, pessoa, r)
    r.ativa, r.proxima_em = False, None
    _salvar(s, r)
    trilha.registrar(s, "rotina_pausada", pessoa.id, r.agente_id, {"rotina": r.id, "agenda": descricao(r)}, dono_tipo=r.dono_tipo)
    return r


def retomar(s: Session, pessoa: Persona, rotina_id: str) -> Rotina:
    r = _obter(s, rotina_id)
    _exigir_gestao(s, pessoa, r)
    r.ativa = True
    r.proxima_em = proxima_depois(r, relogio.agora()).isoformat()
    _salvar(s, r)
    trilha.registrar(s, "rotina_retomada", pessoa.id, r.agente_id, {"rotina": r.id, "proxima_em": r.proxima_em}, dono_tipo=r.dono_tipo)
    return r


def remover(s: Session, pessoa: Persona, rotina_id: str) -> None:
    r = _obter(s, rotina_id)
    _exigir_gestao(s, pessoa, r)
    agente_id, agenda, tipo = r.agente_id, descricao(r), r.dono_tipo
    with trava:
        s.delete(r)
        s.commit()
    trilha.registrar(s, "rotina_removida", pessoa.id, agente_id, {"rotina": rotina_id, "agenda": agenda}, dono_tipo=tipo)


def listar(s: Session, pessoa: Persona, agente_id: str | None = None) -> list[dict]:
    q = select(Rotina)
    if agente_id:
        q = q.where(Rotina.agente_id == agente_id)
    saida = []
    for r in s.exec(q.order_by(Rotina.criada_em)):
        a = s.get(pm.Processo if r.dono_tipo == PROCESSO else am.Agente, r.agente_id)
        if a is not None and _ciclo(r.dono_tipo).pode_ver(pessoa, a):
            d = publica(s, r)
            d["agente_nome"] = a.nome
            d["pode_gerir"] = _pode_gerir(pessoa, r, a)
            d["pode_rodar"] = _pode_rodar(pessoa, r)
            saida.append(d)
    return saida


# =============================================================
# Disparo
# =============================================================
def disparar(s: Session, r: Rotina, origem: str = "agenda", por: Persona | None = None) -> dict:
    """Roda a rotina AGORA, em nome de quem agendou. Devolve {"execucao": id|None, "status": ..., "motivo": ...}.
    Passa pelas mesmas verificações de uma execução manual (acesso, estado do agente, orçamento do mês)."""
    dono = PERSONAS[r.dono]
    ator = por.id if por else "sistema"
    agora = relogio.agora().isoformat()
    try:
        a, bp = _ciclo(r.dono_tipo).checar_execucao(s, dono, r.agente_id)
        faltando = [c for c in bp.ids_campos() if r.entrada.get(c) in (None, "")]
        if faltando:
            raise ciclo.ErroCiclo("A versão publicada pede campos que a rotina não tem: %s." % ", ".join(faltando), 422)
    except ciclo.ErroCiclo as e:
        r.ultima_em, r.ultimo_resultado, r.ultima_execucao_id = agora, "pulada: %s" % e, None
        _salvar(s, r)
        trilha.registrar(s, "rotina_pulada", ator, r.agente_id, {"rotina": r.id, "origem": origem, "motivo": str(e)}, dono_tipo=r.dono_tipo)
        return {"execucao": None, "status": "pulada", "motivo": str(e)}
    if r.dono_tipo == PROCESSO:
        exe, _mapa = motor.executar(s, dono, bp, dict(r.entrada), dono=Dono(PROCESSO, a.id, a.versao_publicada))
    else:
        exe, _mapa = motor.executar(s, dono, bp, dict(r.entrada), agente_id=a.id, versao=a.versao_publicada)
    with trava:
        s.add(RotinaExecucao(execucao_id=exe.id, rotina_id=r.id, origem=origem))
        s.commit()
    r.ultima_em, r.ultima_execucao_id, r.ultimo_resultado = agora, exe.id, exe.status
    _salvar(s, r)
    trilha.registrar(s, "rotina_disparada", ator, a.id, {"rotina": r.id, "execucao": exe.id, "origem": origem,
                                                         "em_nome_de": dono.id, "status": exe.status}, dono_tipo=r.dono_tipo)
    avaliar_seguro(s)
    return {"execucao": exe.id, "status": exe.status, "motivo": exe.motivo}


def rodar_agora(s: Session, pessoa: Persona, rotina_id: str) -> dict:
    r = _obter(s, rotina_id)
    _exigir_gestao(s, pessoa, r, "rodam")
    # a execução usa as permissões (e a classificação de acesso) de QUEM AGENDOU e devolve o detalhe dela: se outra
    # pessoa pudesse disparar, "Rodar agora" viraria um jeito de agir e ler com o acesso de outra pessoa
    if not _pode_rodar(pessoa, r):
        raise ErroRotina("Só quem agendou a rotina roda agora (ela executa com as permissões dessa pessoa). "
                         "Os outros criadores da área podem pausar, retomar ou remover.", 403)
    return disparar(s, r, "manual", pessoa)


def tick(s: Session, agora: datetime | None = None) -> list[dict]:
    """Dispara o que venceu no relógio das rotinas. Perdeu várias vezes (servidor parado)? Roda uma vez só."""
    with _trava_tick:
        momento = agora or relogio.agora()
        vencidas = [r for r in s.exec(select(Rotina).where(Rotina.ativa == True)).all()  # noqa: E712
                    if r.proxima_em and _dt(r.proxima_em) <= momento]
        feitas = []
        for r in sorted(vencidas, key=lambda x: x.proxima_em or ""):
            r.proxima_em = proxima_depois(r, momento).isoformat()   # avança ANTES de rodar: nunca dispara duas vezes
            _salvar(s, r)
            try:
                feitas.append({"rotina": r.id, **disparar(s, r, "agenda")})
            except Exception as e:   # uma rotina com defeito não impede as outras do mesmo tick
                _log.exception("Falha ao disparar a rotina %s", r.id)
                s.rollback()
                motivo = "falhou: %s" % (str(e) or type(e).__name__)
                r = _obter(s, r.id)
                r.ultima_em, r.ultimo_resultado, r.ultima_execucao_id = momento.isoformat(), motivo, None
                _salvar(s, r)
                trilha.registrar(s, "rotina_pulada", "sistema", r.agente_id, {"rotina": r.id, "origem": "agenda", "motivo": motivo},
                                 dono_tipo=r.dono_tipo)
                feitas.append({"rotina": r.id, "execucao": None, "status": "pulada", "motivo": motivo})
        return feitas


# =============================================================
# Marcas nas execuções (selo "rotina")
# =============================================================
def ligacoes(s: Session, execucao_ids: list[str]) -> dict[str, dict]:
    if not execucao_ids:
        return {}
    rs = s.exec(select(RotinaExecucao).where(RotinaExecucao.execucao_id.in_(execucao_ids))).all()
    return {x.execucao_id: {"rotina": x.rotina_id, "origem": x.origem} for x in rs}


def marcar(s: Session, itens: list[dict]) -> list[dict]:
    """Acrescenta `rotina` ({rotina, origem} ou None) a cada execução serializada."""
    lig = ligacoes(s, [i["id"] for i in itens])
    for i in itens:
        i["rotina"] = lig.get(i["id"])
    return itens
