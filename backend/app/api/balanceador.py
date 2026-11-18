"""Política do balanceador de modelos: a Helena vê, simula a queda de um provedor e roda uma carga de teste;
a Engenharia (Lucas) só vê. Criadores veem o modelo escolhido em cada passo, na trilha da execução."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session

from ..audit import trilha
from ..core.db import sessao
from ..core.identidade import ENGENHARIA_PLATAFORMA, GESTOR_IA, Persona, exigir, usuario_atual
from ..llm import balanceador, registro
from ..observability import avaliar_seguro

rotas = APIRouter(prefix="/api/v1/balanceador", tags=["balanceador"])


def _pode_ver(p: Persona) -> None:
    if not (p.tem(GESTOR_IA) or p.tem(ENGENHARIA_PLATAFORMA)):
        raise HTTPException(status_code=403, detail="A política do balanceador é do CoE de IA e da Engenharia.")


def _escolha_do_nivel(idx: int) -> dict:
    e = balanceador.escolher(idx)
    return {"modelo": e.modelo.nome, "chave": e.modelo.chave, "provedor": e.modelo.provedor, "modo": e.modo, "motivo": e.motivo,
            "simulado": not registro.roda_de_verdade(e.modelo.chave),
            "candidatos": [c for c in e.candidatos if c["descartado"] is None][:4]}


@rotas.get("/politica")
def politica(pessoa: Persona = Depends(usuario_atual)):
    _pode_ver(pessoa)
    fora = balanceador.fora_do_ar()
    return {
        "niveis": [{"id": n, "rotulo": balanceador.ROTULO[n], **balanceador.REQUISITOS[n], "escolha": _escolha_do_nivel(i + 1)}
                   for i, n in enumerate(balanceador.NIVEIS)],
        "regras": {
            "tolerancia_homologado": balanceador.TOLERANCIA_HOMOLOGADO, "provedor_homologado": balanceador.PROVEDOR_HOMOLOGADO,
            "orcamento_apertado": balanceador.ORCAMENTO_APERTADO, "limite_contexto_longo": balanceador.LIMITE_CONTEXTO_LONGO,
        },
        "provedores": [{"id": p.id, "nome": p.nome, "real": p.real, "fora": p.id in fora,
                        "modelos": [m.nome for m in registro.do_provedor(p.id)]} for p in registro.PROVEDORES.values()],
        "ultima_carga": balanceador.ultima_carga(),
        "pode_simular": pessoa.tem(GESTOR_IA),
        "demonstracao": "Só o Claude roda de verdade; os outros provedores são simulados.",
    }


class PedidoFalha(BaseModel):
    fora: bool = True


@rotas.post("/provedores/{provedor_id}/falha")
def falha(provedor_id: str, pedido: PedidoFalha, pessoa: Persona = Depends(usuario_atual), s: Session = Depends(sessao)):
    """Simula a queda (ou a volta) de um provedor. Só o CoE de IA."""
    exigir(pessoa, GESTOR_IA)
    if provedor_id not in registro.PROVEDORES:
        raise HTTPException(status_code=404, detail="Provedor desconhecido.")
    balanceador.marcar_fora(provedor_id, pedido.fora)
    trilha.registrar(s, "provedor_falha_simulada" if pedido.fora else "provedor_normalizado", pessoa.id, None,
                     {"provedor": provedor_id})
    avaliar_seguro(s)
    return politica(pessoa)


class PedidoCarga(BaseModel):
    passos: int = Field(default=300, ge=10, le=5000)


@rotas.post("/simular-carga")
def simular_carga(pedido: PedidoCarga, pessoa: Persona = Depends(usuario_atual), s: Session = Depends(sessao)):
    """Lote de passos sintéticos: mostra a distribuição por nível e provedor e o custo, sem chamar nenhum modelo."""
    exigir(pessoa, GESTOR_IA)
    r = balanceador.simular_carga(pedido.passos)
    trilha.registrar(s, "balanceador_carga_simulada", pessoa.id, None,
                     {"passos": r["passos"], "custo_brl": r["custo_brl"], "fora": r["fora"]})
    return r
