"""Balanceador de modelos por nível de esforço (v7).

Cada passo "auto" recebe um NÍVEL DE ESFORÇO (leve, moderado, alto, crítico), calculado de quatro sinais:
a complexidade do texto, as ferramentas que o passo usa, o tamanho do contexto e o risco do agente.
Uma POLÍTICA legível (REQUISITOS) diz o que cada nível exige do modelo; o balanceador escolhe entre os modelos
do registro que atendem, e explica a escolha (nível, candidatos, escolhido, motivo) na trilha "como o agente decidiu".

Regras de escolha (todas aparecem nos motivos):
  - normal:   o provedor homologado (Claude, o único que roda de verdade) vale se custar até TOLERANCIA_HOMOLOGADO
              vezes o modelo capaz mais barato; senão vai ao mais barato capaz.
  - economia: agente com 80% ou mais do orçamento do mês gasto vai SEMPRE ao modelo capaz mais barato.
  - delegação: provedor indisponível (queda simulada pela Helena, ou falha na chamada) é descartado e o passo vai ao
              próximo capaz de outro provedor.
  - fixado:   modelo escolhido pelo criador do agente é respeitado (como na v6).
  - modo real (com chave): só entram candidatos que rodam de verdade (o Claude); os demais são simulados.

Esta é uma DEMONSTRAÇÃO de capacidade: só o Claude roda de verdade; os outros provedores são simulados.
"""
from __future__ import annotations

import random
import threading
from dataclasses import dataclass, field

from ..core import config
from . import precos, registro

NIVEIS = registro.ESFORCOS                  # ("leve", "moderado", "alto", "critico")
NIVEL_AUTO = "auto"
PROVEDOR_HOMOLOGADO = "anthropic"
TOLERANCIA_HOMOLOGADO = 3.0                 # o homologado vale até 3x o preço do mais barato capaz
LIMITE_CONTEXTO_LONGO = 100_000             # acima disso o passo exige modelo de contexto longo
ORCAMENTO_APERTADO = 0.80                   # uso do orçamento mensal a partir do qual vale a economia

ROTULO = {"leve": "Leve", "moderado": "Moderado", "alto": "Alto", "critico": "Crítico"}

# A política, legível na tela: o que cada nível exige do modelo.
REQUISITOS = {
    "leve": {"raciocinio_min": 1, "descricao": "Redação e classificação simples, sem análise."},
    "moderado": {"raciocinio_min": 2, "descricao": "Consulta e resumo com um ou dois fatores."},
    "alto": {"raciocinio_min": 3, "descricao": "Análise com vários fatores, muito contexto ou agente de risco."},
    "critico": {"raciocinio_min": 4, "descricao": "Texto muito complexo ou agente de risco alto com muitas ferramentas."},
}

_trava = threading.Lock()
_fora: set[str] = set()                     # provedores com queda simulada (só na memória: reiniciar a demo desfaz)
_ultima_carga: dict | None = None


# =============================================================
# Estado simulado (queda de provedor, última carga de teste)
# =============================================================
def marcar_fora(provedor: str, fora: bool) -> None:
    if provedor not in registro.PROVEDORES:
        raise KeyError(provedor)
    with _trava:
        (_fora.add if fora else _fora.discard)(provedor)


def fora_do_ar() -> set[str]:
    with _trava:
        return set(_fora)


def ultima_carga() -> dict | None:
    return _ultima_carga


def zerar() -> None:
    """Reiniciar a demo desfaz a queda simulada e a carga de teste."""
    global _ultima_carga
    with _trava:
        _fora.clear()
        _ultima_carga = None


# =============================================================
# Nível de esforço
# =============================================================
def classificar_esforco(nota: float, n_ferramentas: int, tokens_contexto: int, risco: str) -> tuple[int, list[str]]:
    """Devolve (nível de 1 a 4, motivos). `nota` é a complexidade do texto (0 a 1)."""
    if nota >= 0.85:
        idx, motivos = 4, ["texto muito complexo (%.2f)" % nota]
    elif nota >= config.COMPLEXIDADE_FORTE:
        idx, motivos = 3, ["texto complexo (%.2f)" % nota]
    elif nota >= 0.30:
        idx, motivos = 2, ["complexidade média (%.2f)" % nota]
    else:
        idx, motivos = 1, ["texto simples (%.2f)" % nota]
    # o risco vem antes das ferramentas: assim o resultado não depende da ordem das regras
    # (texto médio + risco alto + 3 ferramentas dá "crítico", como texto complexo + risco alto + 3 ferramentas)
    if risco == "alto" and idx == 2:
        idx = 3
        motivos.append("agente de risco alto")
    if n_ferramentas >= 3 and idx == 2:
        idx = 3
        motivos.append("usa %d ferramentas" % n_ferramentas)
    elif n_ferramentas >= 3 and idx == 3 and risco == "alto":
        idx = 4
        motivos.append("agente de risco alto com %d ferramentas" % n_ferramentas)
    if tokens_contexto > LIMITE_CONTEXTO_LONGO and idx < 3:
        idx = 3
        motivos.append("contexto longo (%d mil tokens)" % (tokens_contexto // 1000))
    elif tokens_contexto > LIMITE_CONTEXTO_LONGO:
        motivos.append("contexto longo (%d mil tokens)" % (tokens_contexto // 1000))
    return idx, motivos


# =============================================================
# Escolha
# =============================================================
@dataclass
class Escolha:
    modelo: registro.Modelo
    modo: str                                # normal | economia | delegado | emergencia
    motivo: str
    candidatos: list[dict] = field(default_factory=list)


def _ordem_provedores() -> dict[str, int]:
    return {pid: i for i, pid in enumerate(registro.PROVEDORES)}


def _ficha(m: registro.Modelo, descartado: str | None) -> dict:
    return {"chave": m.chave, "nome": m.nome, "provedor": m.provedor, "preco_ref_usd": round(m.peso, 4),
            "simulado": not registro.roda_de_verdade(m.chave), "descartado": descartado}


def escolher(idx: int, *, n_ferramentas: int = 0, tokens_contexto: int = 0, economia: bool = False,
             so_reais: bool = False, excluir: frozenset[str] | set[str] = frozenset()) -> Escolha:
    """O modelo mais barato que atende o nível `idx` (1 a 4), com os candidatos e o motivo."""
    fora = fora_do_ar()
    reais_fora = so_reais and any(registro.PROVEDORES[p].real for p in fora if p in registro.PROVEDORES)
    if reais_fora:
        # Modo real com o provedor real em queda simulada: sem isto nenhum candidato sobra e a escolha cairia de novo
        # no Claude (emergência), ou seja, a queda não teria efeito. Delega a um provedor simulado, como no modo simulado.
        so_reais = False
    candidatos, capazes = [], []
    for m in registro.todos():
        if m.provedor in excluir:
            motivo = "falhou nesta execução"
        elif m.provedor in fora:
            motivo = "provedor indisponível"
        elif so_reais and not registro.roda_de_verdade(m.chave):
            motivo = "modo real: só o Claude roda de verdade"
        elif m.capacidades.raciocinio < idx:
            motivo = "raciocínio abaixo do exigido (%s)" % NIVEIS[idx - 1]
        elif n_ferramentas and not m.capacidades.ferramentas:
            motivo = "não usa ferramentas"
        elif tokens_contexto > LIMITE_CONTEXTO_LONGO and not m.capacidades.contexto_longo:
            motivo = "contexto longo demais"
        else:
            motivo = None
        candidatos.append(_ficha(m, motivo))
        if motivo is None:
            capazes.append(m)
    ordem = _ordem_provedores()
    capazes.sort(key=lambda m: (m.peso, 0 if registro.roda_de_verdade(m.chave) else 1, ordem[m.provedor], m.chave))

    if not capazes:
        # nenhum candidato atende: o Claude entra como emergência, para o agente não parar
        m = registro.obter("forte" if idx >= 3 else "rapido")
        return Escolha(m, "emergencia", "nenhum provedor atende o nível; usei o Claude como reserva", candidatos)

    barato = capazes[0]
    quedas = [p for p in sorted(fora | set(excluir)) if p in registro.PROVEDORES]
    sufixo = " (provedor %s indisponível)" % ", ".join(registro.PROVEDORES[p].nome for p in quedas) if quedas else ""
    if economia:
        return Escolha(barato, "economia", "orçamento do mês apertado: o modelo capaz mais barato" + sufixo, candidatos)
    homologado = next((m for m in capazes if m.provedor == PROVEDOR_HOMOLOGADO), None)
    if homologado and homologado.peso <= TOLERANCIA_HOMOLOGADO * barato.peso:
        motivo = ("o mais barato capaz, e já é o provedor homologado" if homologado is barato
                  else "provedor homologado, a até %.0fx do mais barato capaz" % TOLERANCIA_HOMOLOGADO)
        return Escolha(homologado, "normal", motivo, candidatos)
    if homologado is None:
        motivo = ("o provedor homologado está indisponível: o mais barato capaz" if PROVEDOR_HOMOLOGADO in quedas
                  else "o provedor homologado não atende o nível: o mais barato capaz")
    else:
        motivo = "o mais barato capaz (o homologado custa mais de %.0fx)" % TOLERANCIA_HOMOLOGADO
    if reais_fora and not registro.roda_de_verdade(barato.chave):
        motivo += " (simulado: o provedor real está fora do ar)"
    return Escolha(barato, "delegado" if quedas else "normal", motivo + (sufixo if quedas and PROVEDOR_HOMOLOGADO not in quedas else ""), candidatos)


# =============================================================
# Carga de teste (só Helena): distribuição e custo, sem chamar nada
# =============================================================
_PESO_NIVEL = (0.45, 0.30, 0.20, 0.05)       # leve, moderado, alto, crítico


def simular_carga(passos: int = 300, semente: int = 11) -> dict:
    """Roda um lote de passos sintéticos pelo balanceador e compara o custo com 'tudo no modelo forte'."""
    global _ultima_carga
    rnd = random.Random(semente)
    por_nivel = {n: {"passos": 0, "custo_usd": 0.0} for n in NIVEIS}
    por_provedor: dict[str, dict] = {}
    por_modelo: dict[str, dict] = {}
    total = base = 0.0
    forte = registro.obter("forte")
    for _ in range(passos):
        idx = rnd.choices(range(1, 5), weights=_PESO_NIVEL)[0]
        n_ferr = rnd.randint(0, 3)
        t_in = int(rnd.uniform(900, 2600) * (1 + 0.25 * (idx - 1)))
        t_out = int(rnd.uniform(200, 600) * (1 + 0.2 * (idx - 1)))
        e = escolher(idx, n_ferramentas=n_ferr, tokens_contexto=t_in)
        custo = precos.custo_usd(e.modelo.chave, t_in, t_out)
        total += custo
        base += precos.custo_usd(forte.chave, t_in, t_out)
        n = por_nivel[NIVEIS[idx - 1]]
        n["passos"] += 1
        n["custo_usd"] += custo
        p = por_provedor.setdefault(e.modelo.provedor, {"passos": 0, "custo_usd": 0.0})
        p["passos"] += 1
        p["custo_usd"] += custo
        mo = por_modelo.setdefault(e.modelo.chave, {"passos": 0, "custo_usd": 0.0})
        mo["passos"] += 1
        mo["custo_usd"] += custo
    r = {
        "passos": passos, "semente": semente, "fora": sorted(fora_do_ar()),
        "custo_brl": round(precos.usd_para_brl(total), 4),
        "custo_tudo_forte_brl": round(precos.usd_para_brl(base), 4),
        "economia_pct": round(1 - total / base, 4) if base else None,
        "por_nivel": [{"nivel": n, "rotulo": ROTULO[n], "passos": v["passos"],
                       "custo_brl": round(precos.usd_para_brl(v["custo_usd"]), 4)} for n, v in por_nivel.items()],
        "por_provedor": [{"provedor": k, "nome": registro.PROVEDORES[k].nome, "passos": v["passos"],
                          "custo_brl": round(precos.usd_para_brl(v["custo_usd"]), 4)}
                         for k, v in sorted(por_provedor.items(), key=lambda kv: -kv[1]["passos"])],
        "por_modelo": [{"chave": k, "nome": registro.obter(k).nome, "provedor": registro.obter(k).provedor,
                        "passos": v["passos"], "custo_brl": round(precos.usd_para_brl(v["custo_usd"]), 4)}
                       for k, v in sorted(por_modelo.items(), key=lambda kv: -kv[1]["passos"])],
    }
    with _trava:
        _ultima_carga = r
    return r
