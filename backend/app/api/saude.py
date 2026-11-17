"""Saúde dos agentes e dos sistemas integrados, alertas e notificações.

Leituras não reavaliam alertas (o sino é consultado a cada 15 s por pessoa conectada).
Quem reavalia: cada execução, mudança de estado ou de orçamento, falha simulada e a vigia de 60 s."""
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..agents import ciclo
from ..agents import modelos as am
from ..agents.blueprint import Blueprint
from ..core.db import sessao
from ..core.identidade import Persona, usuario_atual
from ..observability import alertas, metricas
from ..tools import executor
from ..tools.catalogo import CATALOGO, disponiveis

rotas = APIRouter(prefix="/api/v1", tags=["saude"])


def _saude_agente(s: Session, a: am.Agente, abertos: list[alertas.Alerta]) -> dict:
    execs = metricas.execucoes(s, a.id)
    r = metricas.resumo_execucoes(execs)
    meus = [al for al in abertos if al.agente_id == a.id]
    return {"agente": {"id": a.id, "nome": a.nome, "area": a.area, "dono": a.dono, "estado": a.estado, "risco": a.risco},
            "metricas": r, "score": alertas.score(r["taxa_sucesso"], meus),
            "alertas": [al.model_dump() for al in meus]}


@rotas.get("/saude/agentes")
def agentes(pessoa: Persona = Depends(usuario_atual), s: Session = Depends(sessao)):
    abertos = list(s.exec(select(alertas.Alerta).where(alertas.Alerta.resolvido_em.is_(None))))
    lista = [a for a in s.exec(select(am.Agente).where(am.Agente.estado != am.DEPRECIADO)) if ciclo.pode_ver(pessoa, a)]
    saida = [_saude_agente(s, a, abertos) for a in lista]
    return sorted(saida, key=lambda x: x["score"]["nota"])


@rotas.get("/saude/agentes/{agente_id}")
def agente(agente_id: str, pessoa: Persona = Depends(usuario_atual), s: Session = Depends(sessao)):
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


@rotas.get("/alertas")
def listar_alertas(abertos: bool = True, pessoa: Persona = Depends(usuario_atual), s: Session = Depends(sessao)):
    return [dict(al.model_dump(), lido=pessoa.id in (al.lido_por or []))
            for al in alertas.visiveis(s, pessoa, so_abertos=abertos)]


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
