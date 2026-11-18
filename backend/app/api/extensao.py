"""Extensão copiloto: dado o trecho selecionado, sugere o agente e já preenche os campos detectados.

A extensão não tem lógica de IA: esta rota só lê o texto, procura lojistas e colaboradores citados e ordena
os agentes que a pessoa pode executar pela semelhança com o trecho. Quem roda o agente continua sendo a
plataforma, com as permissões de quem está logado.
"""
import re
import secrets
import threading
import time
import unicodedata

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from ..agents import ciclo
from ..agents import modelos as am
from ..agents.blueprint import Blueprint
from ..audit import trilha
from ..core.db import sessao
from ..core.identidade import CONSULTA_COLABORADORES, PERSONAS, Persona, exigir_aba, usuario_atual
from ..texto.semelhanca import Indice
from ..tools import dados_ficticios as fx

rotas = APIRouter(prefix="/api/v1/extensao", tags=["extensao"])


def _norm(t: str) -> str:
    n = unicodedata.normalize("NFD", (t or "").lower())
    return "".join(c for c in n if unicodedata.category(c) != "Mn")


def detectar_lojista(trecho: str) -> dict | None:
    alvo = _norm(trecho)
    digitos = re.sub(r"\D", "", trecho)
    for l in fx.LOJISTAS.values():
        cnpj = re.sub(r"\D", "", l["cnpj"])
        if _norm(l["nome"]) in alvo or l["id"].lower() in alvo or (len(cnpj) == 14 and cnpj in digitos):
            return {"id": l["id"], "nome": l["nome"], "origem": "citado no trecho"}
    return None


def detectar_colaborador(trecho: str, pessoa: Persona) -> dict | None:
    alvo = _norm(trecho)
    if not pessoa.tem(CONSULTA_COLABORADORES):
        return None
    for c in fx.COLABORADORES.values():
        if _norm(c["nome"]) in alvo or c["id"].lower() in alvo:
            return {"id": c["id"], "nome": c["nome"], "origem": "citado no trecho"}
    return None


_cache_indice: dict[tuple, Indice] = {}


def _indice(executaveis) -> Indice:
    """O índice só muda quando muda o conjunto de agentes/versões publicados."""
    chave = tuple(sorted((a.id, a.versao_publicada) for a, _ in executaveis))
    if chave not in _cache_indice:
        if len(_cache_indice) > 32:
            _cache_indice.clear()
        _cache_indice[chave] = Indice([{"id": a.id, "pergunta": "%s. %s" % (a.nome, bp.objetivo),
                                        "variacoes": [p.titulo for p in bp.passos]} for a, bp in executaveis])
    return _cache_indice[chave]


class PedidoAnalise(BaseModel):
    trecho: str = Field(default="", max_length=8000)


@rotas.post("/analisar")
def analisar(pedido: PedidoAnalise, pessoa: Persona = Depends(usuario_atual), s: Session = Depends(sessao)):
    trecho = pedido.trecho.strip()
    lojista = detectar_lojista(trecho)
    colaborador = detectar_colaborador(trecho, pessoa)
    publicados = [a for a in s.exec(select(am.Agente).where(am.Agente.estado == am.PUBLICADO)).all()
                  if ciclo.pode_executar(pessoa, a)]
    ids = ["%s-v%d" % (a.id, a.versao_publicada) for a in publicados]
    versoes = {v.id: v for v in s.exec(select(am.VersaoAgente).where(am.VersaoAgente.id.in_(ids))).all()} if ids else {}
    executaveis = [(a, Blueprint.model_validate(versoes["%s-v%d" % (a.id, a.versao_publicada)].blueprint)) for a in publicados]

    ordem: dict[str, float] = {}
    similaridade: dict[str, float] = {}
    if trecho and executaveis:
        for achado in _indice(executaveis).buscar(trecho, len(executaveis)):
            ordem[achado["entrada"]["id"]] = similaridade[achado["entrada"]["id"]] = achado["nota"]
        for a, bp in executaveis:   # citar um lojista favorece agentes que pedem um lojista
            if lojista and any(c.tipo == "lojista" for c in bp.campos):
                ordem[a.id] = ordem.get(a.id, 0) + 0.1

    saida = []
    for a, bp in executaveis:
        preenchido, detectado = {}, []
        for c in bp.campos:
            valor = None
            if c.tipo == "lojista" and lojista:
                valor, detectado = lojista["id"], detectado + ["Lojista: " + lojista["nome"]]
            elif c.tipo == "colaborador":
                if colaborador:
                    valor, detectado = colaborador["id"], detectado + ["Colaborador: " + colaborador["nome"]]
                elif pessoa.matricula in fx.COLABORADORES:
                    valor = pessoa.matricula
                    detectado.append("Colaborador: eu mesmo")
            elif c.tipo == "texto_longo" and trecho:
                valor = trecho[:3000]
            elif c.tipo == "opcao":
                valor = next((o for o in c.opcoes if _norm(o) in _norm(trecho)), None)
            if valor:
                preenchido[c.id] = valor
        saida.append({"id": a.id, "nome": a.nome, "objetivo": bp.objetivo, "risco": a.risco,
                      "pontuacao": round(ordem.get(a.id, 0.0), 3), "campos": [c.model_dump() for c in bp.campos],
                      "preenchido": preenchido, "detectado": detectado})
    saida.sort(key=lambda x: -x["pontuacao"])
    # só sugere quando o texto se parece com o agente (citar um lojista sozinho só desempata)
    # (com um lojista citado e algum assunto em comum, ou com semelhança clara)
    sim = similaridade.get(saida[0]["id"], 0) if saida else 0
    sugerido = saida[0]["id"] if saida and (sim >= 0.1 or (sim > 0 and lojista)) else None
    return {"agentes": saida, "sugerido": sugerido, "lojista": lojista, "colaborador": colaborador}


# ---------- passe de uso único: a extensão abre o hub já logada no mesmo perfil ----------
# A extensão pede à plataforma um passe curto (60 s, vale uma vez) para o perfil dela e abre o hub com ele.
# O hub troca o passe pela pessoa. Digitar ?perfil= num endereço direto continua não trocando o perfil de ninguém.
# O trecho selecionado viaja no corpo do pedido (nunca no endereço, que iria para os logs) e volta na troca.
PASSE_VALIDADE_S = 60
_MAX_PASSES = 500
_relogio = time.monotonic          # trocável nos testes para controlar o tempo
_passes: dict[str, dict] = {}      # um processo só, como o resto do protótipo (em produção: SSO / cofre com expiração)
_trava = threading.Lock()


def zerar_passes() -> None:
    with _trava:
        _passes.clear()


class PedidoPasse(BaseModel):
    trecho: str = Field(default="", max_length=8000)
    fonte: dict | None = None      # reservado: de onde veio o trecho (ex.: uma planilha aberta, ticket 10)


class PedidoTroca(BaseModel):
    passe: str = Field(max_length=200)


@rotas.post("/passe")
def emitir_passe(pedido: PedidoPasse, pessoa: Persona = Depends(usuario_atual), s: Session = Depends(sessao)):
    exigir_aba(pessoa, "estudio")        # só quem tem a aba Estúdio cria agentes (a regra é a mesma lista de abas)
    agora = _relogio()
    with _trava:
        for k in [k for k, v in _passes.items() if v["expira"] <= agora]:
            del _passes[k]
        if len(_passes) >= _MAX_PASSES:
            raise HTTPException(status_code=429, detail="Muitos acessos pendentes. Espere um minuto e tente de novo.")
        passe = secrets.token_urlsafe(24)
        _passes[passe] = {"pessoa": pessoa.id, "expira": agora + PASSE_VALIDADE_S,
                          "trecho": pedido.trecho.strip(), "fonte": pedido.fonte}
    trilha.registrar(s, "passe_extensao_emitido", pessoa.id, None, {"com_trecho": bool(pedido.trecho.strip())})
    return {"passe": passe, "valido_por_s": PASSE_VALIDADE_S}


@rotas.post("/passe/trocar")
def trocar_passe(pedido: PedidoTroca, s: Session = Depends(sessao)):
    """Sem X-Usuario: o passe é a credencial. Vale uma vez; usado ou vencido, volta 410."""
    with _trava:
        dados = _passes.pop(pedido.passe, None)
    if not dados or dados["expira"] <= _relogio():
        raise HTTPException(status_code=410, detail="Este acesso pela extensão já foi usado ou venceu (vale uma vez e por "
                            "%d segundos). Escolha seu perfil abaixo ou peça de novo pela extensão." % PASSE_VALIDADE_S)
    pessoa = PERSONAS[dados["pessoa"]]
    trilha.registrar(s, "passe_extensao_usado", pessoa.id, None, {})
    return {"pessoa": pessoa.publico(), "rascunho": dados["trecho"], "fonte": dados["fonte"]}
