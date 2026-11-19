"""Catálogo de ferramentas: listar, testar no sandbox e (Engenharia) injetar falhas."""
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session

from .. import guardrails
from ..core.db import sessao
from ..core.identidade import ENGENHARIA_PLATAFORMA, Persona, exigir, usuario_atual
from ..observability import avaliar_seguro
from ..tools import executor, saidas
from ..plugins.catalogo import PLUGINS
from ..tools.catalogo import CATALOGO, MODULOS, TODAS, Contexto, disponiveis
from ..tools.permissoes import avaliar

rotas = APIRouter(prefix="/api/v1/ferramentas", tags=["ferramentas"])


def _esp(conector_id: str):
    esp = disponiveis().get(conector_id)   # ferramenta de plugin só existe no Catálogo enquanto o plugin está integrado
    if not esp:
        raise HTTPException(status_code=404, detail="Ferramenta não encontrada.")
    return esp


def _publico(esp, pessoa: Persona, s: Session) -> dict:
    est = executor.estado(s, esp.id)
    v = avaliar(pessoa, esp)
    return {
        "id": esp.id, "nome": esp.nome, "descricao": esp.descricao,
        "modulo": esp.modulo, "modulo_nome": MODULOS[esp.modulo],
        "classificacao": esp.classificacao.name.lower(),
        "areas": ["todas"] if TODAS in esp.areas else list(esp.areas),
        "origem": (("plugin interno %s" if PLUGINS[esp.plugin].interno else "plugin %s") % PLUGINS[esp.plugin].nome) if esp.plugin else "plataforma", "plugin": esp.plugin,
        "acao": esp.acao, "exige_aprovacao": esp.exige_aprovacao,
        "limite_por_minuto": esp.limite_por_minuto,
        "parametros": esp.parametros, "obrigatorios": list(esp.obrigatorios), "campos_saida": saidas.campos(esp.id),
        "ativo": est.ativo, "falha": est.falha,
        "disponivel_para_mim": v.permitido, "motivo": v.motivo,
    }


@rotas.get("")
def listar(pessoa: Persona = Depends(usuario_atual), s: Session = Depends(sessao)):
    return {"modulos": MODULOS, "ferramentas": [_publico(e, pessoa, s) for e in disponiveis().values()]}


@rotas.get("/{conector_id}")
def detalhe(conector_id: str, pessoa: Persona = Depends(usuario_atual), s: Session = Depends(sessao)):
    return _publico(_esp(conector_id), pessoa, s)


class PedidoTeste(BaseModel):
    entrada: dict[str, Any]
    confirmar: bool = False   # confirmação humana para ferramentas que exigem aprovação


@rotas.post("/{conector_id}/testar")
def testar(conector_id: str, pedido: PedidoTeste, pessoa: Persona = Depends(usuario_atual),
           s: Session = Depends(sessao)):
    """Sandbox: roda a ferramenta com as permissões de quem está logado."""
    _esp(conector_id)
    r = executor.executar(s, pessoa, conector_id, pedido.entrada, Contexto(persona_id=pessoa.id),
                          aprovado_por=pessoa.id if pedido.confirmar else None)
    saida_tela = None
    if r.saida is not None:   # quem disparou vê os dados reais; o modelo e a auditoria, só marcadores
        import json
        saida_tela = json.loads(guardrails.restaurar(json.dumps(r.saida, ensure_ascii=False), r.mapa))
    return {
        "ok": r.ok, "erro": r.erro, "tipo_erro": r.tipo_erro, "latencia_ms": r.latencia_ms,
        "aguardando_aprovacao": r.aguardando_aprovacao,
        "saida": saida_tela, "enviado_ao_modelo": r.para_modelo() if r.ok else None,
        "mascarados": r.mascarados, "suspeitas": r.suspeitas,
    }


class PedidoFalha(BaseModel):
    falha: str | None = None   # erro | lento | fora_do_ar | null (normaliza)


@rotas.post("/{conector_id}/falha")
def injetar_falha(conector_id: str, pedido: PedidoFalha, pessoa: Persona = Depends(usuario_atual),
                  s: Session = Depends(sessao)):
    """Demo de observabilidade: a Engenharia simula um sistema quebrado."""
    exigir(pessoa, ENGENHARIA_PLATAFORMA)
    _esp(conector_id)
    try:
        executor.definir_falha(s, conector_id, pedido.falha, pessoa.id)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    avaliar_seguro(s)
    return _publico(_esp(conector_id), pessoa, s)
