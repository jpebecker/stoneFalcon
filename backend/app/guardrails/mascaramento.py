"""Guardrails silenciosos: mascaram dados sensíveis antes de qualquer texto sair
para um modelo ou ser gravado na auditoria. O colaborador não configura nada.

O modelo recebe "[CPF_1]" no lugar do CPF. A resposta volta com o marcador e o
valor original é recolocado só na tela de quem perguntou.
"""
import re
import threading


def _cpf_valido(d):
    if len(d) != 11 or d == d[0] * 11:
        return False
    for n in (9, 10):
        soma = sum(int(d[i]) * (n + 1 - i) for i in range(n))
        if (soma * 10) % 11 % 10 != int(d[n]):
            return False
    return True


def _cnpj_valido(d):
    if len(d) != 14 or d == d[0] * 14:
        return False
    for n in (12, 13):
        pesos = list(range(n - 7, 1, -1)) + list(range(9, 1, -1))
        soma = sum(int(d[i]) * pesos[i] for i in range(n))
        resto = soma % 11
        if (0 if resto < 2 else 11 - resto) != int(d[n]):
            return False
    return True


def _luhn(d):
    total = 0
    for i, c in enumerate(reversed(d)):
        n = int(c)
        if i % 2 == 1:
            n = n * 2 - 9 if n > 4 else n * 2
        total += n
    return total % 10 == 0


def _so_digitos(s):
    return re.sub(r"\D", "", s)


# (tipo, rótulo para a tela, expressão, validador)
_REGRAS = [
    ("SEGREDO", "senha ou chave", re.compile(r"(?i)\b((?:senha|password|token|api[ _-]?key|chave de api)\s*[:=]\s*)(\S+)"), None),
    ("SEGREDO", "senha ou chave", re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b"), None),
    ("CARTAO", "número de cartão", re.compile(r"\b(?:\d[ -]?){12,18}\d\b"), lambda s: 13 <= len(_so_digitos(s)) <= 19 and _luhn(_so_digitos(s))),
    ("CNPJ", "CNPJ", re.compile(r"\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b"), lambda s: _cnpj_valido(_so_digitos(s)) or "/" in s),
    ("CPF", "CPF", re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b"), lambda s: _cpf_valido(_so_digitos(s)) or "." in s),
    ("EMAIL", "e-mail", re.compile(r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b"), None),
    ("TELEFONE", "telefone", re.compile(r"(?<![\d\]])(?:\+?55[ ]?)?\(?\d{2}\)?[ ]?9?\d{4}[- ]?\d{4}(?!\d)"), lambda s: len(_so_digitos(s)) >= 10),
]


_trava_mapa = threading.Lock()


def mascarar(texto, mapa=None):
    """Devolve (texto_mascarado, mapa {marcador: original}, resumo [{tipo, rotulo, quantidade}]).

    `mapa` opcional: o mapa de uma execução inteira. Passado, ele é estendido no lugar,
    o mesmo dado mantém o mesmo marcador e a numeração continua (dois resultados de
    ferramenta nunca usam [CPF_1] para pessoas diferentes). Seguro entre threads.
    """
    mapa = {} if mapa is None else mapa
    usados = {}     # tipo -> marcadores encontrados NESTE texto
    rotulos = {}

    def aplicar(tipo, rotulo, regex, validar, t):
        def troca(m):
            alvo = m.group(0)
            prefixo = ""
            if m.lastindex and m.lastindex >= 2:      # regra "senha: valor": mascara só o valor
                prefixo, alvo = m.group(1), m.group(2)
            if validar and not validar(alvo):
                return m.group(0)
            rotulos[tipo] = rotulo
            for marcador, original in mapa.items():   # mesmo dado, mesmo marcador
                if original == alvo and marcador.startswith("[" + tipo + "_"):
                    usados.setdefault(tipo, set()).add(marcador)
                    return prefixo + marcador
            n = sum(1 for k in mapa if k.startswith("[" + tipo + "_")) + 1
            marcador = "[%s_%d]" % (tipo, n)
            mapa[marcador] = alvo
            usados.setdefault(tipo, set()).add(marcador)
            return prefixo + marcador
        return regex.sub(troca, t)

    t = texto or ""
    with _trava_mapa:
        for tipo, rotulo, regex, validar in _REGRAS:
            t = aplicar(tipo, rotulo, regex, validar, t)
    resumo = [{"tipo": k, "rotulo": rotulos[k], "quantidade": len(v)} for k, v in usados.items()]
    return t, mapa, resumo


def restaurar(texto, mapa):
    """Recoloca os valores originais, só para mostrar a quem perguntou."""
    for marcador, original in mapa.items():
        texto = texto.replace(marcador, original)
    return texto


def restaurar_seletivo(texto, mapa, pode):
    """Recoloca só os valores cujo marcador `pode(marcador)` libera. Devolve (texto, marcadores_retidos)."""
    retidos = []
    for marcador, original in mapa.items():
        if marcador in texto:
            if pode(marcador):
                texto = texto.replace(marcador, original)
            else:
                retidos.append(marcador)
    return texto, retidos


def limpar_saida(texto):
    """Guardrail de saída: se o modelo devolver um dado sensível que não veio do
    usuário, ele é removido antes de aparecer na tela."""
    limpo, mapa, resumo = mascarar(texto)
    for marcador in mapa:
        limpo = limpo.replace(marcador, "[dado removido]")
    return limpo, sum(r["quantidade"] for r in resumo)
