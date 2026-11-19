"""Execução governada de ferramentas: o único caminho de um agente até um sistema.

Ordem fixa para cada chamada:
  1. conector existe e está ativo
  2. permissão de QUEM DISPAROU (área + nível)        -> nega e audita
  3. validação da entrada contra o esquema
  4. limite de chamadas por minuto
  5. falha injetada (demo de observabilidade)
  6. execução
  7. guardrails na saída: dados pessoais viram marcadores; conteúdo com cara de
     instrução é sinalizado (prompt injection)
  8. auditoria (entrada e saída já mascaradas, latência, resultado)
"""
from __future__ import annotations

import json
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any

from sqlmodel import Field, Session, SQLModel

from .. import guardrails
from ..audit import trilha
from ..core.db import trava as trava_db
from ..core.identidade import Persona
from ..core.relogio import agora
from ..guardrails import injecao
from .catalogo import CATALOGO, AcessoNegado, Contexto, ErroFerramenta, Especificacao
from .permissoes import avaliar

FALHAS = ("erro", "lento", "fora_do_ar")
LIMITE_TEXTO = 5_000   # por campo de texto enviado a um sistema


class EstadoConector(SQLModel, table=True):
    """O que muda em tempo de operação (o contrato do conector fica no catálogo)."""
    __tablename__ = "conector_estado"

    id: str = Field(primary_key=True)
    ativo: bool = True
    falha: str | None = None           # None | erro | lento | fora_do_ar
    atualizado_em: str | None = None
    atualizado_por: str | None = None


@dataclass
class Resultado:
    ok: bool
    conector_id: str
    saida: dict[str, Any] | None = None          # MASCARADA: é o que o modelo vê
    erro: str | None = None
    tipo_erro: str | None = None                  # negado | invalido | limite | inativo | falha | sistema
    latencia_ms: int = 0
    mascarados: list[dict] = field(default_factory=list)
    suspeitas: list[str] = field(default_factory=list)
    aguardando_aprovacao: bool = False
    mapa: dict[str, str] = field(default_factory=dict, repr=False)   # só para a tela de quem disparou

    def para_modelo(self) -> str:
        """Texto devolvido ao modelo como tool_result."""
        if not self.ok:
            return "ERRO (%s): %s" % (self.tipo_erro, self.erro)
        corpo = json.dumps(self.saida, ensure_ascii=False)
        return injecao.envelopar(self.conector_id, corpo) if self.suspeitas else corpo


# ---------- estado ----------
def estado(s: Session, conector_id: str) -> EstadoConector:
    with trava_db:
        e = s.get(EstadoConector, conector_id)
        if e is None:
            e = EstadoConector(id=conector_id)
            s.add(e)
            s.commit()
            s.refresh(e)
        return e


def definir_falha(s: Session, conector_id: str, falha: str | None, por: str) -> EstadoConector:
    if falha is not None and falha not in FALHAS:
        raise ValueError("Falha inválida. Use: %s ou nenhuma." % ", ".join(FALHAS))
    e = estado(s, conector_id)
    e.falha, e.atualizado_em, e.atualizado_por = falha, agora().isoformat(), por
    s.add(e)
    s.commit()
    trilha.registrar(s, "conector_falha_injetada" if falha else "conector_normalizado", por,
                     dados={"conector": conector_id, "falha": falha})
    return e


# ---------- limite por minuto ----------
_janelas: dict[tuple[str, str], deque] = defaultdict(deque)
_trava = threading.Lock()


def _dentro_do_limite(persona_id: str, esp: Especificacao) -> bool:
    agora_s = time.monotonic()
    with _trava:
        j = _janelas[(persona_id, esp.id)]
        while j and agora_s - j[0] > 60:
            j.popleft()
        if len(j) >= esp.limite_por_minuto:
            return False
        j.append(agora_s)
        return True


def zerar_limites() -> None:
    with _trava:
        _janelas.clear()


# ---------- validação ----------
_TIPOS = {"string": str, "integer": int, "number": (int, float), "boolean": bool}


def validar(esp: Especificacao, entrada: dict) -> str | None:
    if not isinstance(entrada, dict):
        return "A entrada deve ser um objeto."
    faltando = [k for k in esp.obrigatorios if entrada.get(k) in (None, "")]
    if faltando:
        return "Faltam campos obrigatórios: %s." % ", ".join(faltando)
    extras = set(entrada) - set(esp.parametros)
    if extras:
        return "Campos não previstos: %s." % ", ".join(sorted(extras))
    for k, v in entrada.items():
        regra = esp.parametros[k]
        tipo = _TIPOS.get(regra.get("type"))
        if tipo and (not isinstance(v, tipo) or (regra.get("type") != "boolean" and isinstance(v, bool))):
            return "O campo %s deve ser %s." % (k, regra.get("type"))
        if isinstance(v, str) and len(v) > LIMITE_TEXTO:
            return "O campo %s passou de %d caracteres." % (k, LIMITE_TEXTO)
        if "enum" in regra and v not in regra["enum"]:
            return "O campo %s aceita: %s." % (k, ", ".join(regra["enum"]))
    return None


# ---------- execução ----------
def executar(s: Session, pessoa: Persona, conector_id: str, entrada: dict, ctx: Contexto | None = None,
             aprovado_por: str | None = None) -> Resultado:
    ctx = ctx or Contexto(persona_id=pessoa.id)
    inicio = time.perf_counter()

    def fim(r: Resultado, evento: str) -> Resultado:
        r.latencia_ms = r.latencia_ms or int((time.perf_counter() - inicio) * 1000)
        entrada_masc, _, _ = guardrails.mascarar(json.dumps(entrada, ensure_ascii=False))
        trilha.registrar(s, evento, pessoa.id, agente_id=ctx.agente_id, dono_tipo=ctx.dono_tipo, dados={
            "conector": conector_id, "execucao": ctx.execucao_id, "ok": r.ok, "tipo_erro": r.tipo_erro,
            "erro": r.erro, "entrada": entrada_masc, "latencia_ms": r.latencia_ms,
            "mascarados": r.mascarados, "suspeitas": r.suspeitas, "aprovado_por": aprovado_por,
            "dados_retidos": ctx.extras.get("retidos") or [],
        })
        return r

    esp = CATALOGO.get(conector_id)
    if esp is None:
        return fim(Resultado(False, conector_id, erro="Ferramenta não existe no catálogo.", tipo_erro="inativo"),
                   "ferramenta_erro")
    est = estado(s, conector_id)
    if not est.ativo:
        return fim(Resultado(False, conector_id, erro="Ferramenta desativada pela Engenharia.", tipo_erro="inativo"),
                   "ferramenta_erro")

    veredito = avaliar(pessoa, esp)
    if not veredito.permitido:
        return fim(Resultado(False, conector_id, erro=veredito.motivo, tipo_erro="negado"), "ferramenta_negada")

    problema = validar(esp, entrada)
    if problema:
        return fim(Resultado(False, conector_id, erro=problema, tipo_erro="invalido"), "ferramenta_erro")

    if (esp.exige_aprovacao or (esp.aprovacao_se and esp.aprovacao_se(s, entrada, ctx))) and not aprovado_por:
        return fim(Resultado(False, conector_id, erro="Ação sensível: aguardando confirmação de um humano.",
                             tipo_erro="aprovacao", aguardando_aprovacao=True), "ferramenta_aguardando_aprovacao")

    if not _dentro_do_limite(pessoa.id, esp):
        return fim(Resultado(False, conector_id, erro="Limite de %d chamadas por minuto atingido." % esp.limite_por_minuto,
                             tipo_erro="limite"), "ferramenta_erro")

    if est.falha == "fora_do_ar":
        return fim(Resultado(False, conector_id, erro="O sistema não respondeu (tempo esgotado).", tipo_erro="falha",
                             latencia_ms=10_000), "ferramenta_erro")
    if est.falha == "erro":
        return fim(Resultado(False, conector_id, erro="O sistema respondeu com erro 500.", tipo_erro="falha",
                             latencia_ms=esp.latencia_ms), "ferramenta_erro")

    ctx.extras["sessao"] = s            # ferramentas que guardam dados no banco (plugin Arquivos e Planilhas)
    ctx.extras.pop("classificacao_dado", None)
    try:
        bruto = esp.executar(entrada, ctx)
    except AcessoNegado as e:
        return fim(Resultado(False, conector_id, erro=str(e), tipo_erro="negado"), "ferramenta_negada")
    except ErroFerramenta as e:
        return fim(Resultado(False, conector_id, erro=str(e), tipo_erro="invalido"), "ferramenta_erro")
    except Exception as e:  # sistema quebrou: registra, não derruba o agente
        return fim(Resultado(False, conector_id, erro="Falha inesperada no conector (%s)." % type(e).__name__,
                             tipo_erro="sistema"), "ferramenta_erro")

    texto = json.dumps(bruto, ensure_ascii=False)
    compartilhado = ctx.extras.get("mapa")
    antes = set(compartilhado or {})
    masc, mapa, resumo = guardrails.mascarar(texto, compartilhado)
    origens = ctx.extras.get("origens")
    if origens is not None:   # dado novo herda a classificação do sistema de onde veio
        for marcador in set(mapa) - antes:
            origens[marcador] = max(int(esp.classificacao), int(ctx.extras.get("classificacao_dado") or 0))
    latencia = esp.latencia_ms * (8 if est.falha == "lento" else 1)
    try:
        saida = json.loads(masc)
    except json.JSONDecodeError:   # máscara atravessou a estrutura: entrega como texto
        saida = {"texto": masc}
    r = Resultado(True, conector_id, saida=saida, latencia_ms=latencia,
                  mascarados=resumo, suspeitas=injecao.suspeito(texto), mapa=mapa)
    return fim(r, "ferramenta_executada")
