"""Saúde dos agentes e dos sistemas integrados, alertas e notificações.

Leituras não reavaliam alertas (o sino é consultado a cada 15 s por pessoa conectada).
Quem reavalia: cada execução, mudança de estado ou de orçamento, falha simulada e a vigia de 60 s."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from ..agents import ciclo
from ..agents import modelos as am
from ..agents.blueprint import Blueprint
from ..core.db import sessao
from ..core.identidade import PERSONAS, Persona, usuario_atual
from ..observability import alertas, metricas, tratamento
from ..processos import modelos as pm
from ..processos.tipo import ciclo as ciclo_processos
from ..tools import executor
from ..tools.catalogo import CATALOGO, disponiveis

rotas = APIRouter(prefix="/api/v1", tags=["saude"])


def _dump(al: alertas.Alerta) -> dict:
    """O alerta com o nome de quem está tratando (o que o cartão de Saúde mostra)."""
    return dict(al.model_dump(), tratando_nome=PERSONAS[al.tratando_por].nome if al.tratando_por in PERSONAS else None)


def _saude_agente(s: Session, a: am.Agente, abertos: list[alertas.Alerta]) -> dict:
    execs = metricas.execucoes(s, a.id)
    r = metricas.resumo_execucoes(execs)
    meus = [al for al in abertos if al.agente_id == a.id]
    return {"agente": {"id": a.id, "nome": a.nome, "area": a.area, "dono": a.dono, "estado": a.estado, "risco": a.risco},
            "metricas": r, "score": alertas.score(r["taxa_sucesso"], meus),
            "alertas": [_dump(al) for al in meus]}


def _saude_processo(s: Session, p: pm.Processo, abertos: list[alertas.Alerta]) -> dict:
    """A saúde de um PROCESSO (v8.1): as execuções são do processo, e os alertas abertos dele entram na nota."""
    r = metricas.resumo_execucoes(metricas.execucoes(s, p.id, tipo="processo"))
    meus = [al for al in abertos if al.processo_id == p.id]
    return {"agente": {"id": p.id, "nome": p.nome, "area": p.area, "dono": p.dono, "estado": p.estado, "risco": p.risco, "tipo": "processo"},
            "metricas": r, "score": alertas.score(r["taxa_sucesso"], meus),
            "alertas": [_dump(al) for al in meus]}


@rotas.get("/saude/agentes")
def agentes(pessoa: Persona = Depends(usuario_atual), s: Session = Depends(sessao)):
    abertos = list(s.exec(select(alertas.Alerta).where(alertas.Alerta.resolvido_em.is_(None))))
    lista = [a for a in s.exec(select(am.Agente).where(am.Agente.estado != am.DEPRECIADO)) if ciclo.pode_ver(pessoa, a)]
    saida = [_saude_agente(s, a, abertos) for a in lista]
    saida += [_saude_processo(s, p, abertos) for p in s.exec(select(pm.Processo).where(pm.Processo.estado.in_((am.PUBLICADO, am.PAUSADO))))
              if ciclo_processos.pode_ver(pessoa, p)]
    return sorted(saida, key=lambda x: x["score"]["nota"])


@rotas.get("/saude/agentes/{agente_id}")
def agente(agente_id: str, pessoa: Persona = Depends(usuario_atual), s: Session = Depends(sessao)):
    processo = s.get(pm.Processo, agente_id)
    if processo is not None:   # o mesmo detalhe vale para um processo
        if not ciclo_processos.pode_ver(pessoa, processo):
            raise HTTPException(status_code=403, detail="Você não tem acesso a este processo.")
        abertos = list(s.exec(select(alertas.Alerta).where(alertas.Alerta.resolvido_em.is_(None))))
        d = _saude_processo(s, processo, abertos)
        d["por_dia"] = metricas.por_dia(metricas.execucoes(s, processo.id, horas=24 * 30, tipo="processo"))
        d["ferramentas"] = []
        return d
    try:
        a = ciclo.obter(s, agente_id)
    except ciclo.ErroCiclo as e:
        raise HTTPException(status_code=e.status, detail=str(e))
    if not ciclo.pode_ver(pessoa, a):
        raise HTTPException(status_code=403, detail="Você não tem acesso a este agente.")
    abertos = list(s.exec(select(alertas.Alerta).where(alertas.Alerta.resolvido_em.is_(None))))
    d = _saude_agente(s, a, abertos)
    d["por_dia"] = metricas.por_dia(metricas.execucoes(s, a.id, horas=24 * 30))
    usadas = Blueprint.model_validate(ciclo.versao(s, a.id, a.versao_publicada).blueprint).ferramentas_usadas() \
        if a.versao_publicada else set()
    uso = metricas.chamadas_ferramentas(s, horas=24)
    d["ferramentas"] = [{"id": f, "nome": CATALOGO[f].nome, **uso.get(f, {"chamadas": 0, "erros": 0, "taxa_erro": 0.0}),
                         "falha": executor.estado(s, f).falha} for f in sorted(usadas)]
    return d


@rotas.get("/saude/conectores")
def conectores(_p: Persona = Depends(usuario_atual), s: Session = Depends(sessao)):
    uso = metricas.chamadas_ferramentas(s, horas=alertas.JANELA_CONECTOR_H)
    abertos = {al.conector: al for al in s.exec(select(alertas.Alerta).where(alertas.Alerta.resolvido_em.is_(None)))
               if al.conector}
    saida = []
    for cid, esp in disponiveis().items():
        al = abertos.get(cid)
        status = "fora" if al and al.regra == "conector_fora" else "lento" if al else "ok"
        saida.append({"id": cid, "nome": esp.nome, "modulo": esp.modulo, "status": status,
                      "verificacao": "sintética + chamadas reais da última hora",
                      "latencia_tipica_ms": esp.latencia_ms, **uso.get(cid, {"chamadas": 0, "erros": 0, "taxa_erro": 0.0}),
                      "detalhe": al.detalhe if al else None})
    return saida


def _publico(s: Session, al: alertas.Alerta, pessoa: Persona) -> dict:
    """O alerta como a tela o mostra: lido por mim, quem está tratando (nome) e a ação que o meu perfil pode executar."""
    return dict(_dump(al), lido=pessoa.id in (al.lido_por or []), acao=tratamento.acao_para(s, al, pessoa))


@rotas.get("/alertas")
def listar_alertas(abertos: bool = True, pessoa: Persona = Depends(usuario_atual), s: Session = Depends(sessao)):
    return [_publico(s, al, pessoa) for al in alertas.visiveis(s, pessoa, so_abertos=abertos)]


@rotas.get("/notificacoes/contagem")
def contagem(pessoa: Persona = Depends(usuario_atual), s: Session = Depends(sessao)):
    nao_lidos = [al for al in alertas.visiveis(s, pessoa) if pessoa.id not in (al.lido_por or [])]
    return {"nao_lidos": len(nao_lidos), "criticos": sum(1 for al in nao_lidos if al.severidade == alertas.CRITICO)}


@rotas.post("/alertas/{alerta_id}/lido")
def marcar_lido(alerta_id: str, pessoa: Persona = Depends(usuario_atual), s: Session = Depends(sessao)):
    al = s.get(alertas.Alerta, alerta_id)
    if al is None or al not in alertas.visiveis(s, pessoa, so_abertos=False):
        raise HTTPException(status_code=404, detail="Alerta não encontrado.")
    if pessoa.id not in (al.lido_por or []):
        al.lido_por = sorted(set(al.lido_por or []) | {pessoa.id})
        s.add(al)
        s.commit()
    return {"ok": True}


def _meu_alerta(s: Session, alerta_id: str, pessoa: Persona) -> alertas.Alerta:
    al = s.get(alertas.Alerta, alerta_id)
    if al is None or al not in alertas.visiveis(s, pessoa, so_abertos=False):
        raise HTTPException(status_code=404, detail="Alerta não encontrado.")
    return al


def _tratar(fn, *args, **kw):
    try:
        return fn(*args, **kw)
    except tratamento.ErroTratamento as e:
        raise HTTPException(status_code=e.status, detail=str(e))


class PedidoAssumir(BaseModel):
    nota: str = Field(default="", max_length=300)


@rotas.post("/alertas/{alerta_id}/assumir")
def assumir(alerta_id: str, pedido: PedidoAssumir, pessoa: Persona = Depends(usuario_atual), s: Session = Depends(sessao)):
    """Assume o alerta com uma nota curta: ele passa a "em tratamento · por você" para todos os destinatários."""
    al = _tratar(tratamento.assumir, s, _meu_alerta(s, alerta_id, pessoa), pessoa, pedido.nota)
    return _publico(s, al, pessoa)


@rotas.post("/alertas/{alerta_id}/devolver")
def devolver(alerta_id: str, pessoa: Persona = Depends(usuario_atual), s: Session = Depends(sessao)):
    al = _tratar(tratamento.devolver, s, _meu_alerta(s, alerta_id, pessoa), pessoa)
    return _publico(s, al, pessoa)


class PedidoAcao(BaseModel):
    motivo: str = Field(default="", max_length=500)
    valor_brl: float | None = Field(default=None, ge=0)


@rotas.post("/alertas/{alerta_id}/acao")
def acao(alerta_id: str, pedido: PedidoAcao, pessoa: Persona = Depends(usuario_atual), s: Session = Depends(sessao)):
    """Executa a ação primária da regra do alerta (pausar, revisar o orçamento, abrir o sistema, restaurar o provedor) e o assume."""
    al = _meu_alerta(s, alerta_id, pessoa)
    resposta = _tratar(tratamento.executar_acao, s, al, pessoa, pedido.motivo, pedido.valor_brl)
    return {**resposta, "alerta": _publico(s, al, pessoa)}
