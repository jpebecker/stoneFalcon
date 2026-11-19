"""Processos: fluxos de blocos (agentes, plugins, dados, aprovações). Criar, versionar, publicar, operar e executar.

Todo mundo vê a aba; só criadores da área editam (a API confere a cada chamada, a tela só lê)."""
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, ValidationError
from sqlmodel import Session, select

from ..agents import ciclo as ciclo_agentes
from ..agents import modelos as am
from ..agents.blueprint import Blueprint
from ..agents.ciclo import ErroCiclo
from ..agents.dono import PROCESSO, Dono
from ..agents.governanca import avaliar_risco, estimar_custo, estimar_duracao_ms, ferramentas_sem_permissao
from ..audit import trilha
from ..core.db import sessao
from ..core.identidade import CRIADOR, GESTOR_IA, Persona, exigir, usuario_atual
from ..observability import avaliar_seguro
from ..processos import modelos as pm
from ..processos.blueprint import ProcessoBlueprint
from ..processos.compilar import compilar, trabalhador
from ..processos.diff import comparar
from ..processos.tipo import ciclo
from ..roteiros.catalogo import ROTEIROS
from ..rotinas import marcar as marcar_rotina
from ..runtime import motor
from ..runtime.modelos import Execucao
from .execucoes import _publico as execucao_publica

rotas = APIRouter(prefix="/api/v1", tags=["processos"])

_EVENTOS_CICLO = {"processo_criado", "processo_modificado", "processo_enviado_revisao", "revisao_aprovada",
                  "revisao_rejeitada", "processo_publicado", "processo_pausado", "processo_retomado",
                  "processo_depreciado", "processo_compartilhado", "execucao_escalada", "execucao_negada"}


def _erro(e: ErroCiclo):
    raise HTTPException(status_code=e.status, detail=str(e))


def _blueprint(dados: dict[str, Any]) -> ProcessoBlueprint:
    """Valida o fluxo e devolve os problemas em português (nunca o texto técnico do validador)."""
    try:
        return ProcessoBlueprint.model_validate(dados)
    except ValidationError as e:
        msgs = [err["msg"].removeprefix("Value error, ") for err in e.errors()]
        raise HTTPException(status_code=422, detail=" ".join(dict.fromkeys(msgs))) from None


def _dump(s: Session, obj) -> dict:
    s.refresh(obj)
    return obj.model_dump()


def _as_is(roteiro_id: str | None) -> dict | None:
    r = ROTEIROS.get(roteiro_id or "")
    return {"roteiro_id": r.id, "processo": r.processo, "persona": r.persona} if r else None


def agentes_do_processo(s: Session, p: pm.Processo) -> list[str]:
    versao = ciclo.versao(s, p.id, p.versao_publicada or p.ultima_versao)
    return ProcessoBlueprint.model_validate(versao.blueprint).agentes_usados()


def _resumo(p: pm.Processo, s: Session) -> dict:
    d = p.model_dump()
    execs = s.exec(select(Execucao).where(Execucao.dono_tipo == PROCESSO).where(Execucao.dono_id == p.id)).all()
    d["execucoes"] = len(execs)
    d["escaladas"] = sum(1 for e in execs if e.status == "escalada")
    d["custo_brl"] = round(sum(e.custo_usd for e in execs) * motor.precos.usd_para_brl(1.0), 4)
    d["as_is"] = _as_is(p.roteiro_id)
    d["agentes"] = agentes_do_processo(s, p)
    return d


def _ver(pessoa: Persona, p: pm.Processo) -> None:
    if not ciclo.pode_ver(pessoa, p):
        raise HTTPException(status_code=403, detail="Você não tem acesso a este processo.")


def _pode_editar(pessoa: Persona, p: pm.Processo) -> bool:
    return pessoa.id == p.dono or (pessoa.tem(CRIADOR) and pessoa.area == p.area)


@rotas.get("/processos")
def listar(pessoa: Persona = Depends(usuario_atual), s: Session = Depends(sessao)):
    todos = s.exec(select(pm.Processo).order_by(pm.Processo.atualizado_em.desc())).all()
    return [_resumo(p, s) for p in todos if ciclo.pode_ver(pessoa, p)]


class PedidoProcesso(BaseModel):
    blueprint: dict[str, Any]
    nota: str = Field(default="", max_length=500)


@rotas.post("/processos")
def criar(pedido: PedidoProcesso, pessoa: Persona = Depends(usuario_atual), s: Session = Depends(sessao)):
    exigir(pessoa, CRIADOR)
    try:
        return _dump(s, ciclo.criar(s, pessoa, _blueprint(pedido.blueprint), pedido.nota))
    except ErroCiclo as e:
        _erro(e)


@rotas.get("/processos/agentes-disponiveis")
def agentes_disponiveis(pessoa: Persona = Depends(usuario_atual), s: Session = Depends(sessao)):
    """Agentes que o criador pode pôr num bloco: os da área dele (ou compartilhados). Só trabalhadores (um passo de IA) servem."""
    saida = []
    for a in s.exec(select(am.Agente).order_by(am.Agente.nome)):
        if a.estado == am.DEPRECIADO or not ciclo_agentes.pode_executar(pessoa, a):
            continue
        v = ciclo_agentes.versao(s, a.id, a.versao_publicada or a.ultima_versao)
        bp = Blueprint.model_validate(v.blueprint)
        w = trabalhador(bp)
        saida.append({"id": a.id, "nome": a.nome, "objetivo": bp.objetivo, "estado": a.estado, "area": a.area,
                      "publicado": a.versao_publicada is not None, "trabalhador": w is not None,
                      "ferramentas": list(w.ferramentas) if w else [], "modelo": w.modelo if w else None,
                      "motivo": None if w else "Tem vários passos (formato antigo): converta em processo para reaproveitar."})
    return saida


@rotas.get("/processos/as-is")
def opcoes_as_is(pessoa: Persona = Depends(usuario_atual)):
    """Processos AS IS -> TO BE a que o criador pode ligar o fluxo: o do roteiro dele (o CoE vê todos)."""
    return [{"roteiro_id": r.id, "processo": r.processo, "persona": r.persona}
            for r in ROTEIROS.values() if not r.apresentacao and (r.persona == pessoa.id or pessoa.tem(GESTOR_IA))]


class PedidoBlueprint(BaseModel):
    blueprint: dict[str, Any]


@rotas.post("/processos/validar")
def validar(pedido: PedidoBlueprint, pessoa: Persona = Depends(usuario_atual), s: Session = Depends(sessao)):
    """Checagem ao vivo enquanto a pessoa monta o fluxo."""
    try:
        pbp = ProcessoBlueprint.model_validate(pedido.blueprint)
    except ValidationError as e:
        return {"valido": False, "erros": list(dict.fromkeys(err["msg"].removeprefix("Value error, ") for err in e.errors()))}
    try:
        bp = compilar(s, pbp, pessoa, "ultima")
    except ErroCiclo as e:
        return {"valido": False, "erros": [str(e)]}
    est = estimar_custo(bp)
    risco = avaliar_risco(bp)
    return {
        "valido": True, "erros": [], "niveis": pbp.niveis(),
        "sem_permissao": ferramentas_sem_permissao(pessoa, bp),
        "bloqueios": {p.id: p.bloqueio for p in bp.passos if p.bloqueio},
        "risco": {"nivel": risco.nivel, "motivos": risco.motivos, "exige_revisao_seguranca": risco.exige_revisao},
        "estimativa": {"custo_por_execucao_brl": est.custo_brl, "chamadas_modelo": est.chamadas_modelo,
                       "por_passo": est.por_passo, "duracao_ms": estimar_duracao_ms(bp)},
    }


class PedidoTeste(BaseModel):
    blueprint: dict[str, Any]
    entrada: dict[str, Any] = Field(default_factory=dict)


@rotas.post("/processos/testar")
def testar(pedido: PedidoTeste, pessoa: Persona = Depends(usuario_atual), s: Session = Depends(sessao)):
    """Sandbox: roda o rascunho com as permissões de quem está montando (agentes em rascunho incluídos)."""
    exigir(pessoa, CRIADOR)
    pbp = _blueprint(pedido.blueprint).model_copy(update={"area": pessoa.area})
    try:
        bp = compilar(s, pbp, pessoa, "ultima")
    except ErroCiclo as e:
        _erro(e)
    faltando = [c for c in bp.ids_campos() if pedido.entrada.get(c) in (None, "")]
    if faltando:
        raise HTTPException(status_code=422, detail="Preencha: %s." % ", ".join(faltando))
    exe, mapa = motor.executar(s, pessoa, bp, pedido.entrada, dono=Dono(PROCESSO, "sandbox", None))
    return execucao_publica(exe, mapa)


@rotas.get("/processos/{processo_id}")
def detalhe(processo_id: str, pessoa: Persona = Depends(usuario_atual), s: Session = Depends(sessao)):
    try:
        p = ciclo.obter(s, processo_id)
    except ErroCiclo as e:
        _erro(e)
    _ver(pessoa, p)
    d = _resumo(p, s)
    d["versoes"] = [v.model_dump() for v in ciclo.versoes(s, p.id)]
    d["pode_executar"] = ciclo.pode_executar(pessoa, p)
    d["pode_editar"] = _pode_editar(pessoa, p)
    eventos = [e for e in trilha.listar(s, agente_id=p.id, limite=300, dono_tipo=PROCESSO) if e.tipo in _EVENTOS_CICLO]
    d["historico"] = [e.model_dump() for e in eventos]
    return d


@rotas.put("/processos/{processo_id}")
def editar(processo_id: str, pedido: PedidoProcesso, pessoa: Persona = Depends(usuario_atual), s: Session = Depends(sessao)):
    try:
        return _dump(s, ciclo.editar(s, pessoa, processo_id, _blueprint(pedido.blueprint), pedido.nota))
    except ErroCiclo as e:
        _erro(e)


@rotas.get("/processos/{processo_id}/diff")
def diff(processo_id: str, de: int, para: int, pessoa: Persona = Depends(usuario_atual), s: Session = Depends(sessao)):
    try:
        p = ciclo.obter(s, processo_id)
        _ver(pessoa, p)
        antes = ciclo.versao(s, processo_id, de).blueprint if de > 0 else None
        return comparar(antes, ciclo.versao(s, processo_id, para).blueprint)
    except ErroCiclo as e:
        _erro(e)


@rotas.post("/processos/{processo_id}/publicar")
def publicar(processo_id: str, pessoa: Persona = Depends(usuario_atual), s: Session = Depends(sessao)):
    try:
        return _dump(s, ciclo.publicar(s, pessoa, processo_id))
    except ErroCiclo as e:
        _erro(e)


class PedidoRevisao(BaseModel):
    aprovar: bool
    parecer: str = Field(default="", max_length=1500)


@rotas.post("/processos/{processo_id}/revisao")
def revisar(processo_id: str, pedido: PedidoRevisao, pessoa: Persona = Depends(usuario_atual), s: Session = Depends(sessao)):
    try:
        return _dump(s, ciclo.revisar(s, pessoa, processo_id, pedido.aprovar, pedido.parecer))
    except ErroCiclo as e:
        _erro(e)


class PedidoMotivo(BaseModel):
    motivo: str = Field(default="", max_length=500)


@rotas.post("/processos/{processo_id}/pausar")
def pausar(processo_id: str, pedido: PedidoMotivo, pessoa: Persona = Depends(usuario_atual), s: Session = Depends(sessao)):
    try:
        p = ciclo.pausar(s, pessoa, processo_id, pedido.motivo)
        avaliar_seguro(s)
        return _dump(s, p)
    except ErroCiclo as e:
        _erro(e)


@rotas.post("/processos/{processo_id}/retomar")
def retomar(processo_id: str, pessoa: Persona = Depends(usuario_atual), s: Session = Depends(sessao)):
    try:
        p = ciclo.retomar(s, pessoa, processo_id)
        avaliar_seguro(s)
        return _dump(s, p)
    except ErroCiclo as e:
        _erro(e)


@rotas.post("/processos/{processo_id}/depreciar")
def depreciar(processo_id: str, pedido: PedidoMotivo, pessoa: Persona = Depends(usuario_atual), s: Session = Depends(sessao)):
    try:
        p = ciclo.depreciar(s, pessoa, processo_id, pedido.motivo)
        avaliar_seguro(s)
        return _dump(s, p)
    except ErroCiclo as e:
        _erro(e)


class PedidoCompartilhar(BaseModel):
    areas: list[str]


@rotas.post("/processos/{processo_id}/compartilhar")
def compartilhar(processo_id: str, pedido: PedidoCompartilhar, pessoa: Persona = Depends(usuario_atual),
                 s: Session = Depends(sessao)):
    try:
        return _dump(s, ciclo.compartilhar(s, pessoa, processo_id, pedido.areas))
    except ErroCiclo as e:
        _erro(e)


class PedidoExecutar(BaseModel):
    entrada: dict[str, Any] = Field(default_factory=dict)


@rotas.post("/processos/{processo_id}/executar")
def executar(processo_id: str, pedido: PedidoExecutar, pessoa: Persona = Depends(usuario_atual), s: Session = Depends(sessao)):
    try:
        p, bp = ciclo.checar_execucao(s, pessoa, processo_id)
    except ErroCiclo as e:
        _erro(e)
    faltando = [c for c in bp.ids_campos() if pedido.entrada.get(c) in (None, "")]
    if faltando:
        raise HTTPException(status_code=422, detail="Preencha: %s." % ", ".join(faltando))
    exe, mapa = motor.executar(s, pessoa, bp, pedido.entrada, dono=Dono(PROCESSO, p.id, p.versao_publicada))
    avaliar_seguro(s)
    s.refresh(exe)
    return execucao_publica(exe, mapa)


@rotas.get("/processos/{processo_id}/execucoes")
def execucoes(processo_id: str, limite: int = 50, pessoa: Persona = Depends(usuario_atual), s: Session = Depends(sessao)):
    try:
        p = ciclo.obter(s, processo_id)
    except ErroCiclo as e:
        _erro(e)
    _ver(pessoa, p)
    itens = s.exec(select(Execucao).where(Execucao.dono_tipo == PROCESSO).where(Execucao.dono_id == p.id)
                   .order_by(Execucao.inicio.desc()).limit(min(max(limite, 1), 500))).all()
    return marcar_rotina(s, [execucao_publica(e) for e in itens])
