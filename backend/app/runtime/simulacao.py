"""Política do agente no MODO SIMULADO (sem chave, sem internet).

Imita o comportamento de um modelo no loop de raciocínio, de forma determinística:
  1º turno: chama as ferramentas do passo cujos campos obrigatórios dá para preencher
            com a entrada e com o que os passos anteriores trouxeram;
  2º turno (já com os resultados): escreve um resumo com os fatos encontrados.

Ações sensíveis (que exigem aprovação humana) só são propostas quando os dados
trazem sinal de risco: na demo, 5 ou mais contestações. É uma heurística de
demonstração; com a chave ligada, quem decide é o modelo de verdade.
"""
from __future__ import annotations

import json
import re
import uuid

from ..llm.cliente import ChamadaFerramenta, RespostaLLM, simulador
from ..tools.catalogo import CATALOGO
from . import respostas

_ENTRADA = re.compile(r"<entrada>(.*?)</entrada>", re.S)
_PASSO = re.compile(r"<passo>(.*?)</passo>", re.S)
_DADOS = re.compile(r"<dados origem=\"[^\"]*\">\n(.*?)\n</dados>", re.S)


def _texto_inicial(mensagens: list[dict]) -> str:
    c = mensagens[0].get("content") if mensagens else ""
    return c if isinstance(c, str) else ""


def _resultados(mensagens: list[dict]) -> list[str]:
    saida = []
    for msg in mensagens[1:]:
        if msg.get("role") == "user" and isinstance(msg.get("content"), list):
            saida += [b.get("content", "") for b in msg["content"] if isinstance(b, dict) and b.get("type") == "tool_result"]
    return saida


def _json(texto: str) -> dict | list | None:
    achado = _DADOS.search(texto)
    bruto = achado.group(1) if achado else texto
    try:
        return json.loads(bruto)
    except (json.JSONDecodeError, TypeError):
        return None


def _fatos(obj, limite: int = 6) -> list[str]:
    """Campos simples (texto e número) de um resultado, para o resumo."""
    if not isinstance(obj, dict):
        return []
    fatos = []
    for k, v in obj.items():
        if isinstance(v, (str, int, float)) and not isinstance(v, bool):
            fatos.append("%s: %s" % (k.replace("_", " "), v))
        elif isinstance(v, list):
            fatos.append("%s: %d registro(s)" % (k.replace("_", " "), len(v)))
        if len(fatos) >= limite:
            break
    return fatos


def _risco(texto: str) -> bool:
    if "sinais de risco relevantes" in texto:   # conclusão de um passo anterior
        return True
    return any(int(n) >= 5 for n in re.findall(r'"quantidade": (\d+)', texto)) and "contest" in texto


def _preencher(conector: str, entrada: dict, titulo: str, texto: str, area: str | None,
               ctx: "respostas.Contexto | None" = None) -> dict | None:
    esp = CATALOGO[conector]
    valores = {}
    for campo in esp.obrigatorios:
        regra = esp.parametros[campo]
        livre = respostas.campo_para_ferramenta(campo, conector, ctx, titulo) if ctx else None
        if livre:
            valores[campo] = livre
        elif campo in entrada:
            valores[campo] = entrada[campo]
        elif "enum" in regra:
            valores[campo] = area if area in regra["enum"] else regra["enum"][0]
        elif campo in ("titulo",):
            valores[campo] = "%s (%s)" % (titulo, entrada.get("lojista_id") or "caso")
        elif campo in ("descricao", "mensagem", "motivo"):
            valores[campo] = "Registrado pelo agente no passo \"%s\" com base nos dados consultados." % titulo
        elif campo == "fila":
            pedida = re.search(r"fila (\w+)", texto)
            valores[campo] = pedida.group(1) if pedida else ("risco" if "risco" in texto.lower() else "atendimento")
        elif campo == "destino":
            valores[campo] = "#time-responsavel"
        elif campo == "consulta":
            tarefa = re.search(r"Tarefa deste passo: (.*)", texto)
            valores[campo] = tarefa.group(1)[:200] if tarefa else titulo
        else:
            return None
    return valores


def roteiro(chave: str, sistema: str, mensagens: list[dict], ferramentas: list[dict] | None) -> RespostaLLM | None:
    inicial = _texto_inicial(mensagens)
    m_entrada = _ENTRADA.search(inicial)
    if not m_entrada:
        return None   # não é uma chamada do runtime
    entrada = json.loads(m_entrada.group(1))
    titulo = (_PASSO.search(inicial).group(1) if _PASSO.search(inicial) else "passo").strip()
    ja = _resultados(mensagens)
    m_area = re.search(r"da área (\w+)", sistema)
    area = m_area.group(1) if m_area else None

    ctx = respostas.montar(inicial, ja, entrada)
    if ferramentas and not ja:
        chamadas = []
        for f in ferramentas:
            nome = f["name"]
            if CATALOGO[nome].exige_aprovacao and not _risco(inicial):
                continue
            valores = _preencher(nome, entrada, titulo, inicial, area, ctx)
            if valores is not None:
                chamadas.append(ChamadaFerramenta("sim_" + uuid.uuid4().hex[:8], nome, valores))
        if chamadas:
            justificativa = "Com base nos dados consultados, vou %s." % " e ".join(CATALOGO[c.nome].nome.lower() for c in chamadas)
            return RespostaLLM(chave, justificativa, chamadas=chamadas)

    composto = respostas.compor(ctx, titulo, [f["name"] for f in (ferramentas or [])], bool(ja))
    if composto:
        return RespostaLLM(chave, composto)

    fatos = []
    for r in ja:
        fatos += _fatos(_json(r))
    for bloco in _DADOS.findall(inicial):
        fatos += _fatos(_json(bloco), 4)
    erros = [r for r in ja if r.startswith("ERRO")]
    linhas = ["%s (resposta simulada)." % titulo]
    if fatos:
        linhas.append("Dados considerados: " + "; ".join(fatos[:10]) + ".")
    if erros:
        linhas.append("Não consegui usar: " + " | ".join(erros) + ".")
    if _risco(inicial + "".join(ja)):
        linhas.append("Há sinais de risco relevantes; recomendo análise humana antes de qualquer decisão.")
    return RespostaLLM(chave, " ".join(linhas))


simulador().registrar_roteiro(roteiro)
