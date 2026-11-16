"""Catálogo governado de ferramentas (conectores).

Quem registra conectores é a Engenharia de Plataforma, não o criador do agente.
Cada conector tem:
  - classificação da informação que toca (pública → restrita);
  - áreas que podem usá-lo;
  - tipo de ação (leitura ou escrita) e se exige aprovação humana antes de agir;
  - limite de chamadas por minuto;
  - módulo de integração (os 4 módulos do documento de custos).

No protótipo, cada conector chama um sistema de mentira (dados_ficticios). Em
produção, o mesmo contrato apontaria para um webhook do n8n ou uma API interna:
o agente e o runtime não mudam.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from ..core.identidade import Classificacao
from ..seed.conhecimento import BASE_INICIAL
from ..texto.semelhanca import Indice
from . import dados_ficticios as fx

TODAS = "*"

MODULOS = {
    "lojistas": "Lojistas e transações",
    "atendimento": "Chamados e atendimento",
    "pessoas": "Pessoas (RH)",
    "comunicacao": "Comunicação e conhecimento",
}


class ErroFerramenta(Exception):
    """Erro esperado de um conector (entrada inválida, registro não encontrado...)."""


@dataclass(frozen=True)
class Especificacao:
    id: str
    nome: str
    descricao: str                     # vai para o modelo: diz QUANDO usar
    modulo: str
    classificacao: Classificacao
    areas: tuple[str, ...]
    acao: str                          # "leitura" | "escrita"
    parametros: dict[str, Any]         # JSON Schema (properties)
    obrigatorios: tuple[str, ...]
    executar: Callable[[dict, "Contexto"], dict]
    exige_aprovacao: bool = False      # escrita sensível: humano confirma antes
    limite_por_minuto: int = 30
    latencia_ms: int = 120             # latência típica do sistema (simulada)

    def para_modelo(self) -> dict:
        """Definição no formato de ferramenta da API da Anthropic."""
        return {
            "name": self.id,
            "description": self.descricao,
            "input_schema": {
                "type": "object",
                "properties": self.parametros,
                "required": list(self.obrigatorios),
                "additionalProperties": False,
            },
            "strict": True,
        }


@dataclass
class Contexto:
    """Quem está executando. Ferramentas rodam com as permissões de quem DISPAROU o agente."""
    persona_id: str
    agente_id: str | None = None
    execucao_id: str | None = None
    extras: dict = field(default_factory=dict)


# =============================================================
# Implementações (sistemas de mentira)
# =============================================================
def _lojista(id_: str) -> dict:
    l = fx.LOJISTAS.get((id_ or "").strip().upper())
    if not l:
        raise ErroFerramenta("Lojista %s não encontrado." % id_)
    return l


def _consultar_lojista(e: dict, _c: Contexto) -> dict:
    l = dict(_lojista(e["lojista_id"]))
    l["titular"] = fx.TITULARES[l["id"]]
    return l


def _listar_transacoes(e: dict, _c: Contexto) -> dict:
    l = _lojista(e["lojista_id"])
    dias = max(1, min(int(e.get("dias", 7)), 90))
    ts = fx.transacoes(l["id"], dias)
    return {"lojista_id": l["id"], "dias": dias, "quantidade": len(ts),
            "total": round(sum(t["valor"] for t in ts), 2), "transacoes": ts[:50]}


def _listar_chargebacks(e: dict, _c: Contexto) -> dict:
    l = _lojista(e["lojista_id"])
    dias = max(1, min(int(e.get("dias", 30)), 90))
    cs = [t for t in fx.transacoes(l["id"], dias) if t["contestada"]]
    return {"lojista_id": l["id"], "dias": dias, "quantidade": len(cs),
            "valor_total": round(sum(t["valor"] for t in cs), 2), "contestacoes": cs}


def _abrir_chamado(e: dict, c: Contexto) -> dict:
    ch = {"id": fx.novo_id("CH", fx.CHAMADOS), "fila": e["fila"], "titulo": e["titulo"],
          "descricao": e["descricao"], "prioridade": e.get("prioridade", "media"),
          "aberto_por": c.persona_id, "agente_id": c.agente_id, "status": "aberto"}
    fx.CHAMADOS.append(ch)
    return {"chamado_id": ch["id"], "status": "aberto", "fila": ch["fila"]}


_indices_politica: dict[str, Indice] = {}


def _buscar_politica(e: dict, _c: Contexto) -> dict:
    area = e["area"]
    if area not in BASE_INICIAL:
        raise ErroFerramenta("Área sem base de políticas: %s. Use: %s." % (area, ", ".join(BASE_INICIAL)))
    if area not in _indices_politica:
        _indices_politica[area] = Indice([{"id": "%s-%d" % (area, i), **it} for i, it in enumerate(BASE_INICIAL[area])])
    achados = _indices_politica[area].buscar(e["consulta"], 3)
    return {"resultados": [{"pergunta": a["entrada"]["pergunta"], "resposta": a["entrada"]["resposta"],
                            "relevancia": a["nota"]} for a in achados if a["nota"] >= 0.3]}


def _consultar_colaborador(e: dict, _c: Contexto) -> dict:
    col = fx.COLABORADORES.get((e["colaborador_id"] or "").strip().upper())
    if not col:
        raise ErroFerramenta("Colaborador %s não encontrado." % e["colaborador_id"])
    return dict(col)


def _enviar_notificacao(e: dict, c: Contexto) -> dict:
    n = {"id": fx.novo_id("NT", fx.NOTIFICACOES), "canal": e["canal"], "destino": e["destino"],
         "mensagem": e["mensagem"], "enviado_por": c.persona_id, "agente_id": c.agente_id}
    fx.NOTIFICACOES.append(n)
    return {"notificacao_id": n["id"], "status": "enviada (simulado)"}


def _bloquear_repasse(e: dict, c: Contexto) -> dict:
    l = _lojista(e["lojista_id"])
    b = {"id": fx.novo_id("BL", fx.BLOQUEIOS), "lojista_id": l["id"], "motivo": e["motivo"],
         "solicitado_por": c.persona_id, "agente_id": c.agente_id, "status": "repasse retido"}
    fx.BLOQUEIOS.append(b)
    return {"bloqueio_id": b["id"], "status": b["status"]}


_LOJ = {"lojista_id": {"type": "string", "description": "Código do lojista, por exemplo L1001."}}
_DIAS = {"dias": {"type": "integer", "description": "Janela em dias (1 a 90)."}}

CATALOGO: dict[str, Especificacao] = {e.id: e for e in [
    Especificacao(
        "consultar_lojista", "Consultar cadastro do lojista",
        "Busca o cadastro de um lojista: nome, CNPJ, cidade, plano, faturamento médio e titular. "
        "Use quando precisar identificar o cliente ou o porte do negócio.",
        "lojistas", Classificacao.INTERNA, ("atendimento", "risco"), "leitura",
        _LOJ, ("lojista_id",), _consultar_lojista),
    Especificacao(
        "listar_transacoes", "Listar transações do lojista",
        "Lista as vendas de um lojista numa janela de dias, com valor, bandeira, modalidade e se foi contestada.",
        "lojistas", Classificacao.CONFIDENCIAL, ("risco",), "leitura",
        {**_LOJ, **_DIAS}, ("lojista_id",), _listar_transacoes, latencia_ms=380),
    Especificacao(
        "listar_chargebacks", "Listar contestações (chargebacks)",
        "Lista as vendas contestadas de um lojista numa janela de dias, com quantidade e valor total.",
        "lojistas", Classificacao.CONFIDENCIAL, ("risco", "atendimento"), "leitura",
        {**_LOJ, **_DIAS}, ("lojista_id",), _listar_chargebacks, latencia_ms=300),
    Especificacao(
        "abrir_chamado", "Abrir chamado",
        "Abre um chamado numa fila interna (por exemplo: logistica, risco, ti, pessoas). "
        "Use para encaminhar um caso que precisa de ação de outro time.",
        "atendimento", Classificacao.INTERNA, (TODAS,), "escrita",
        {"fila": {"type": "string", "description": "Fila de destino."},
         "titulo": {"type": "string", "description": "Resumo em uma linha."},
         "descricao": {"type": "string", "description": "Detalhes do caso."},
         "prioridade": {"type": "string", "enum": ["baixa", "media", "alta"]}},
        ("fila", "titulo", "descricao"), _abrir_chamado, limite_por_minuto=10),
    Especificacao(
        "buscar_politica", "Buscar política interna",
        "Procura na base de políticas aprovadas de uma área (rh, ti, atendimento, risco) "
        "a orientação oficial mais próxima da consulta.",
        "comunicacao", Classificacao.INTERNA, (TODAS,), "leitura",
        {"area": {"type": "string", "enum": sorted(BASE_INICIAL)},
         "consulta": {"type": "string", "description": "O que procurar, em linguagem natural."}},
        ("area", "consulta"), _buscar_politica, latencia_ms=60),
    Especificacao(
        "consultar_colaborador", "Consultar ficha do colaborador",
        "Consulta dados de RH de um colaborador: área, admissão, saldo de férias e benefícios.",
        "pessoas", Classificacao.CONFIDENCIAL, ("pessoas",), "leitura",
        {"colaborador_id": {"type": "string", "description": "Matrícula, por exemplo C501."}},
        ("colaborador_id",), _consultar_colaborador),
    Especificacao(
        "enviar_notificacao", "Enviar notificação",
        "Envia uma mensagem por e-mail ou Slack interno a uma pessoa ou canal.",
        "comunicacao", Classificacao.INTERNA, (TODAS,), "escrita",
        {"canal": {"type": "string", "enum": ["email", "slack"]},
         "destino": {"type": "string", "description": "E-mail ou canal (#nome)."},
         "mensagem": {"type": "string"}},
        ("canal", "destino", "mensagem"), _enviar_notificacao, limite_por_minuto=10),
    Especificacao(
        "bloquear_repasse", "Reter repasses do lojista",
        "Retém preventivamente os repasses de um lojista sob suspeita. Ação sensível: "
        "só executa depois que um analista humano confirma.",
        "lojistas", Classificacao.RESTRITA, ("risco",), "escrita",
        {**_LOJ, "motivo": {"type": "string", "description": "Justificativa do bloqueio."}},
        ("lojista_id", "motivo"), _bloquear_repasse, exige_aprovacao=True, limite_por_minuto=5),
]}


def obter(conector_id: str) -> Especificacao:
    esp = CATALOGO.get(conector_id)
    if not esp:
        raise KeyError(conector_id)
    return esp
