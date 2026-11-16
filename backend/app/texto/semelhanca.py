"""Camada 1 · reconhecer o significado de uma pergunta sem chamar nenhum modelo.

Como funciona, em ordem:
  1. normaliza (minúsculas, sem acento, sem pontuação);
  2. troca expressões e sinônimos por um termo único ("contracheque" -> "holerite");
  3. reduz cada palavra ao radical ("solicitar", "solicito", "solicitação" -> "solicit");
  4. compara por radicais (peso maior para termos raros) e por pedaços de 3 letras.

É uma aproximação de "busca por significado" que roda em qualquer computador,
sem biblioteca extra. Em produção, esta etapa usaria embeddings.
"""
import math
import re
import unicodedata

from . import lexico as config

_SUFIXOS = [
    "amentos", "imentos", "amento", "imento", "mente", "acoes", "acao", "icoes", "icao",
    "idades", "idade", "ando", "endo", "indo", "aram", "eram", "iram", "avam",
    "aria", "eria", "iria", "ado", "ido", "ada", "ida", "ar", "er", "ir", "ou", "ei", "am", "em",
]


def normalizar(texto):
    texto = unicodedata.normalize("NFD", (texto or "").lower())
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    texto = re.sub(r"\[[a-z_]+_\d+\]", " ", texto)   # ignora marcadores de dado mascarado
    return re.sub(r"[^a-z0-9]+", " ", texto).strip()


def _radical(palavra):
    if palavra.isdigit() or len(palavra) <= 3:
        return palavra
    p = palavra
    for fim, troca in (("oes", "ao"), ("aes", "ao"), ("ais", "al"), ("eis", "el"), ("ns", "m")):
        if p.endswith(fim) and len(p) > len(fim) + 2:
            p = p[: -len(fim)] + troca
            break
    else:
        if p.endswith("s") and not p.endswith("ss") and len(p) > 4:
            p = p[:-1]
    for suf in _SUFIXOS:
        if p.endswith(suf) and len(p) - len(suf) >= 3:
            return p[: -len(suf)]
    if p[-1] in "aeo" and len(p) > 4:
        p = p[:-1]
    return p


def radicais(texto):
    """Lista de radicais de conteúdo de um texto (sem palavras vazias)."""
    t = " " + normalizar(texto) + " "
    for expr, troca in config.EXPRESSOES.items():
        t = t.replace(" " + expr + " ", " " + troca + " ")
    saida = []
    for palavra in t.split():
        if palavra in config.PALAVRAS_VAZIAS:
            continue
        # sinônimo pela palavra exata ou pelo radical ("coloco" -> "colocar" -> "incluir")
        palavra = config.SINONIMOS.get(palavra) or _SINONIMOS_POR_RADICAL.get(_radical(palavra), palavra)
        if palavra in config.PALAVRAS_VAZIAS:
            continue
        saida.append(_radical(palavra))
    return saida


_SINONIMOS_POR_RADICAL = {}
for _k, _v in config.SINONIMOS.items():
    if len(_k) > 3:
        _SINONIMOS_POR_RADICAL.setdefault(_radical(_k), _v)


def _trigramas(rads):
    s = " ".join(rads)
    return {s[i : i + 3] for i in range(max(len(s) - 2, 1))}


class Indice:
    """Índice das perguntas aprovadas de um agente."""

    def __init__(self, entradas):
        # entradas: [{"id", "pergunta", "variacoes", ...}]
        self.itens = []   # (entrada, texto_original, radicais)
        for e in entradas:
            if e.get("removida"):
                continue
            for frase in [e["pergunta"]] + list(e.get("variacoes", [])):
                self.itens.append((e, frase, radicais(frase)))
        n = len(self.itens) or 1
        df = {}
        for _, _, rads in self.itens:
            for r in set(rads):
                df[r] = df.get(r, 0) + 1
        self.idf = {r: math.log((n + 1) / (c + 0.5)) + 0.3 for r, c in df.items()}
        # termo desconhecido pesa como um termo raro, mas não como o mais raro
        self.idf_desconhecido = math.log((n + 1) / 1.0) + 0.3

    def _peso(self, r):
        return self.idf.get(r, self.idf_desconhecido)

    def _semelhanca(self, q, c):
        if not q or not c:
            return 0.0
        sq, sc = set(q), set(c)
        comum = sq & sc
        ponto = sum(self._peso(r) ** 2 for r in comum)
        nq = math.sqrt(sum(self._peso(r) ** 2 for r in sq))
        nc = math.sqrt(sum(self._peso(r) ** 2 for r in sc))
        cosseno = ponto / (nq * nc) if nq and nc else 0.0
        tq, tc = _trigramas(q), _trigramas(c)
        dice = 2 * len(tq & tc) / (len(tq) + len(tc)) if tq and tc else 0.0
        return 0.78 * cosseno + 0.22 * dice

    def buscar(self, pergunta, quantos=3):
        """Devolve os melhores candidatos: [{"entrada", "frase", "nota"}], sem repetir entrada."""
        q = radicais(pergunta)
        melhores = {}
        for entrada, frase, rads in self.itens:
            nota = self._semelhanca(q, rads)
            # Verificador contra falso positivo: se a pergunta traz um termo que não
            # existe em nenhuma pergunta aprovada E a candidata tem um termo que a
            # pergunta não tem, provavelmente o assunto mudou ("prazo de estorno" x
            # "prazo de antecipação"). A nota fica na zona de dúvida, nunca acima.
            if nota >= config.LIMIAR_BASE and any(r not in self.idf for r in q) and set(rads) - set(q):
                nota = config.LIMIAR_BASE - 0.01
            atual = melhores.get(entrada["id"])
            if atual is None or nota > atual["nota"]:
                melhores[entrada["id"]] = {"entrada": entrada, "frase": frase, "nota": round(nota, 3)}
        return sorted(melhores.values(), key=lambda x: -x["nota"])[:quantos]


def complexidade(pergunta, contexto=""):
    """Nota de 0 a 1 de quão trabalhosa a pergunta parece, com os motivos."""
    norm = " " + normalizar(pergunta) + " "
    palavras = norm.split()
    nota = min(len(palavras) / 170.0, 0.30)
    motivos = []
    achados = [t for t in config.TERMOS_DE_ANALISE if " " + t + " " in norm]
    if achados:
        nota += min(0.22 * len(achados), 0.50)
        motivos.append("pede análise (" + ", ".join(achados[:3]) + ")")
    if re.search(r"\d", pergunta):
        nota += 0.10
        motivos.append("envolve números")
    if pergunta.count("?") > 1 or ";" in pergunta:
        nota += 0.08
        motivos.append("mais de uma pergunta")
    if len(contexto or "") > 400:
        nota += 0.12
        motivos.append("trecho longo anexado")
    if len(palavras) > 30:
        motivos.append("pergunta longa")
    return round(min(nota, 1.0), 2), motivos


def estimar_tokens(texto):
    """Estimativa usada no modo simulado e para comparar cenários (aprox. 3,6 letras por token)."""
    return max(1, int(len(texto or "") / 3.6))
