"""Onboarding guiado: descrição do processo em português -> agente pronto para testar.

Com os modelos reais, o Sonnet propõe o blueprint usando SÓ as ferramentas que a
pessoa pode usar. No modo simulado (ou se o modelo falhar), o Estúdio escolhe o
padrão da galeria mais parecido com a descrição. Nos dois casos a plataforma:
  - mascara dados pessoais da descrição antes de qualquer envio;
  - remove ferramentas que a pessoa não pode usar e avisa por quê;
  - calcula risco, custo estimado e explica cada passo em linguagem simples.
"""
from __future__ import annotations

import copy
import json
import re
from dataclasses import dataclass, field

from pydantic import ValidationError

from .. import guardrails
from ..agents.blueprint import Blueprint
from ..agents.governanca import Estimativa, Risco, avaliar_risco, estimar_custo
from ..core.identidade import Persona
from ..llm import precos
from ..llm.cliente import ClienteSimulado, ErroModelo, obter_cliente
from ..seed.agentes_exemplo import DUVIDA_LOJISTA
from ..texto.semelhanca import Indice
from ..tools.catalogo import CATALOGO
from ..tools.permissoes import avaliar
from .modelos_prontos import PADROES

LIMIAR_PADRAO = 0.25
AREA_POLITICA = {"pessoas": "rh", "engenharia": "ti", "risco": "risco", "atendimento": "atendimento"}


@dataclass
class Sugestao:
    blueprint: Blueprint
    origem: str                                   # "modelo" | "padrao:<id>" | "basico"
    explicacao: list[dict]
    removidas: dict[str, str]
    risco: Risco
    estimativa: Estimativa
    alertas: list[str] = field(default_factory=list)
    custo_sugestao_brl: float = 0.0

    def publico(self) -> dict:
        return {
            "blueprint": self.blueprint.model_dump(), "origem": self.origem, "explicacao": self.explicacao,
            "ferramentas_removidas": self.removidas, "alertas": self.alertas,
            "risco": {"nivel": self.risco.nivel, "motivos": self.risco.motivos,
                      "exige_revisao_seguranca": self.risco.exige_revisao},
            "estimativa": {"custo_por_execucao_brl": self.estimativa.custo_brl,
                           "chamadas_modelo": self.estimativa.chamadas_modelo,
                           "por_passo": self.estimativa.por_passo},
            "niveis": self.blueprint.niveis(), "custo_sugestao_brl": self.custo_sugestao_brl,
        }


# =============================================================
# Peças comuns
# =============================================================
def extrair_minutos(descricao: str) -> float | None:
    """'levo uns 20 minutos', '1 hora', '2h' -> minutos (linha de base do ROI)."""
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*(minutos?|min\b|horas?|h\b)", descricao.lower())
    if not m:
        return None
    valor = float(m.group(1).replace(",", "."))
    return valor * 60 if m.group(2).startswith("h") else valor


def _filtrar_permissoes(pessoa: Persona, dados: dict) -> tuple[dict, dict[str, str]]:
    """Tira do blueprint o que a pessoa não pode usar. Passo de ferramenta proibida sai inteiro."""
    removidas: dict[str, str] = {}
    fora = set()
    for p in dados["passos"]:
        for fid in ([p["ferramenta"]] if p.get("ferramenta") else []) + list(p.get("ferramentas", [])):
            v = avaliar(pessoa, CATALOGO[fid])
            if not v.permitido:
                removidas[fid] = v.motivo
                fora.add(fid)
    passos = []
    tirados = set()
    for p in dados["passos"]:
        if p["tipo"] == "ferramenta" and p.get("ferramenta") in fora:
            tirados.add(p["id"])
            continue
        p = dict(p)
        p["ferramentas"] = [f for f in p.get("ferramentas", []) if f not in fora]
        passos.append(p)
    for p in passos:
        p["depende_de"] = [d for d in p.get("depende_de", []) if d not in tirados]
    dados = dict(dados, passos=passos)
    return dados, removidas


def _basico(pessoa: Persona) -> dict:
    area = AREA_POLITICA.get(pessoa.area, "atendimento")
    return {
        "nome": "Assistente de %s" % pessoa.area_nome, "area": pessoa.area, "minutos_manual": 5,
        "objetivo": "Responder dúvidas da área %s com base na política oficial." % pessoa.area_nome,
        "instrucoes": "", "campos_entrada": ["pergunta"],
        "passos": [
            {"id": "politica", "titulo": "Buscar a política aplicável", "tipo": "ferramenta",
             "ferramenta": "buscar_politica", "entrada": {"area": area, "consulta": "{{entrada.pergunta}}"}},
            {"id": "resposta", "titulo": "Responder", "tipo": "agente", "modelo": "rapido", "depende_de": ["politica"],
             "instrucao": "Responda à pergunta usando a política encontrada; se ela não cobrir o caso, diga isso."},
        ],
    }


def explicar(bp: Blueprint, estimativa: Estimativa) -> list[dict]:
    paralelos = {pid for camada in bp.niveis() if len(camada) > 1 for pid in camada}
    saida = []
    for p in bp.passos:
        if p.tipo == "ferramenta":
            texto = "Consulta \"%s\" automaticamente, sem IA e sem custo de modelo." % CATALOGO[p.ferramenta].nome
        elif p.tipo == "aprovacao":
            texto = "Pausa e espera a confirmação de uma pessoa da área antes de seguir."
        else:
            modelo = estimativa.por_passo[p.id]["modelo"]
            texto = "Usa o %s para: %s" % (modelo, p.instrucao.rstrip("."))
            if p.ferramentas:
                texto += ". Pode acionar: %s" % ", ".join(CATALOGO[f].nome for f in p.ferramentas)
            texto += "."
        if p.id in paralelos:
            texto += " Roda em paralelo com outros passos."
        if any(CATALOGO[f].exige_aprovacao for f in ([p.ferramenta] if p.ferramenta else []) + p.ferramentas):
            texto += " Ações sensíveis só acontecem depois da sua confirmação."
        saida.append({"passo": p.id, "titulo": p.titulo, "explicacao": texto})
    return saida


# =============================================================
# Modo simulado: escolhe o padrão mais parecido
# =============================================================
_indice = Indice([{"id": p["id"], "pergunta": p["exemplos"][0], "variacoes": p["exemplos"][1:]} for p in PADROES])


def _por_padrao(pessoa: Persona, descricao: str) -> tuple[dict, str, list[str]]:
    candidatos = _indice.buscar(descricao, len(PADROES))
    for c in candidatos:   # padrões da própria área ganham um empurrão
        padrao = next(p for p in PADROES if p["id"] == c["entrada"]["id"])
        if padrao["area"] == pessoa.area:
            c["nota"] += 0.08
    candidatos.sort(key=lambda c: -c["nota"])
    if candidatos and candidatos[0]["nota"] >= LIMIAR_PADRAO:
        padrao = next(p for p in PADROES if p["id"] == candidatos[0]["entrada"]["id"])
        return copy.deepcopy(padrao["blueprint"]), "padrao:" + padrao["id"], []
    return _basico(pessoa), "basico", [
        "Não reconheci um processo parecido na galeria; montei um agente básico de perguntas e respostas. "
        "Ajuste os passos no canvas ou descreva com mais detalhes (o que você consulta e o que faz no fim)."]


# =============================================================
# Modo real: o Sonnet propõe o blueprint
# =============================================================
_FORMATO = """Formato do agente (JSON):
{"nome": str, "objetivo": str, "area": str, "instrucoes": str, "campos_entrada": [str],
 "minutos_manual": número, "passos": [Passo]}
Passo:
{"id": "snake_case", "titulo": str, "tipo": "ferramenta"|"agente"|"aprovacao", "depende_de": [ids],
 // tipo "ferramenta": chamada direta, sem IA
 "ferramenta": id, "entrada": {campo: valor ou "{{entrada.campo}}" ou "{{passos.ID.saida.campo}}"},
 // tipo "agente": loop de raciocínio
 "instrucao": str, "ferramentas": [ids], "modelo": "auto"|"rapido"|"forte"}
Regras:
- Use SOMENTE as ferramentas listadas. Consultas fixas viram passo "ferramenta"; julgamento vira "agente".
- Passos independentes NÃO dependem entre si (rodam em paralelo).
- Prefira "rapido" para redação e classificação simples; "forte" só para análise com vários fatores.
- Ações de escrita sensíveis já pedem confirmação humana sozinhas; não invente ferramentas.
- Responda APENAS com o JSON, sem comentários."""


def _extrair_json(texto: str) -> dict:
    ini, fim = texto.find("{"), texto.rfind("}")
    if ini < 0 or fim < ini:
        raise ValueError("A resposta não trouxe um JSON.")
    return json.loads(texto[ini:fim + 1])


def _com_modelo(pessoa: Persona, descricao: str) -> tuple[dict, float]:
    permitidas = [CATALOGO[f].para_modelo() for f in CATALOGO if avaliar(pessoa, CATALOGO[f]).permitido]
    sistema = "\n\n".join([
        "Você é o Estúdio do StoneFalcon. Transforma a descrição de um processo de trabalho em um agente "
        "de IA executável, para pessoas sem conhecimento técnico.",
        _FORMATO,
        "Ferramentas disponíveis para esta pessoa:\n" + json.dumps(
            [{"id": f["name"], "descricao": f["description"], "parametros": f["input_schema"]["properties"],
              "obrigatorios": f["input_schema"]["required"]} for f in permitidas], ensure_ascii=False),
        "Exemplo de agente bem montado:\n" + DUVIDA_LOJISTA.model_dump_json(),
    ])
    pedido = "Área da pessoa: %s.\nDescrição do processo:\n%s" % (pessoa.area, descricao)
    cliente = obter_cliente()
    msgs = [{"role": "user", "content": pedido}]
    custo = 0.0
    for _tentativa in range(2):
        r = cliente.gerar("forte", sistema, msgs, None, max_tokens=4000)
        custo += precos.custo_usd("forte", r.tokens_entrada, r.tokens_saida, r.tokens_cache_leitura)
        try:
            dados = _extrair_json(r.texto)
            Blueprint.model_validate(dict(dados, area=pessoa.area))
            return dados, custo
        except (ValueError, ValidationError) as e:
            msgs += [{"role": "assistant", "content": r.texto or "{}"},
                     {"role": "user", "content": "O JSON não passou na validação: %s. Corrija e devolva só o JSON." % str(e)[:800]}]
    raise ValueError("O modelo não gerou um agente válido.")


# =============================================================
# Entrada principal
# =============================================================
def sugerir(pessoa: Persona, descricao: str, simulado: bool | None = None) -> Sugestao:
    descricao_masc, _, resumo = guardrails.mascarar(descricao.strip())
    alertas: list[str] = []
    if resumo:
        alertas.append("Tirei dados pessoais da descrição antes de usá-la (%s)."
                       % ", ".join("%d %s" % (r["quantidade"], r["rotulo"]) for r in resumo))
    custo_usd = 0.0
    real = (simulado is False) or (simulado is None and not isinstance(obter_cliente(), ClienteSimulado))
    dados = None
    origem = "modelo"
    if real:
        try:
            dados, custo_usd = _com_modelo(pessoa, descricao_masc)
        except (ErroModelo, ValueError) as e:
            alertas.append("O modelo não conseguiu montar o agente (%s); usei a galeria de padrões." % e)
    if dados is None:
        dados, origem, avisos = _por_padrao(pessoa, descricao_masc)
        alertas += avisos

    dados["area"] = pessoa.area
    minutos = extrair_minutos(descricao)
    if minutos:
        dados["minutos_manual"] = minutos
    dados, removidas = _filtrar_permissoes(pessoa, dados)
    if removidas:
        alertas.append("Algumas ferramentas ficaram de fora porque o seu perfil não pode usá-las. "
                       "Se o processo precisar delas, peça acesso à Engenharia de Plataforma.")
    try:
        bp = Blueprint.model_validate(dados)
    except ValidationError:
        bp = Blueprint.model_validate(_basico(pessoa))
        origem = "basico"
        alertas.append("Sem as ferramentas permitidas o processo não fecha; montei um agente básico.")
    estimativa = estimar_custo(bp)
    return Sugestao(bp, origem, explicar(bp, estimativa), removidas, avaliar_risco(bp), estimativa,
                    alertas, round(precos.usd_para_brl(custo_usd), 4))
