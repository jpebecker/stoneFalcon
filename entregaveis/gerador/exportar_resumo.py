"""F9.2: lê a aba 'Resumo para slides' do Excel RECALCULADO e grava resumo.json para o deck.

Os slides só usam números deste JSON, que só vem da aba Resumo (fonte única).
Uso:  .venv/Scripts/python.exe exportar_resumo.py
"""
import json
from pathlib import Path

from openpyxl import load_workbook

AQUI = Path(__file__).resolve().parent
ARQ = AQUI.parent / "analise-financeira.xlsx"
wb = load_workbook(ARQ, data_only=True)
ws = wb["Resumo para slides"]

numeros, origem = {}, {}
r = 5
while ws["A%d" % r].value:
    chave = ws["A%d" % r].value
    v = ws["C%d" % r].value
    if v is None:
        raise SystemExit("Célula sem valor (%s). Rode recalcular.py antes." % chave)
    numeros[chave] = v
    origem[chave] = {"rotulo": ws["B%d" % r].value, "celula": "Resumo para slides!C%d" % r, "origem": ws["D%d" % r].value}
    r += 1


def tabela(nome):
    """Lê um intervalo nomeado res_gN como lista de linhas (a 1ª é o cabeçalho)."""
    dn = wb.defined_names[nome]
    (aba, ref), = list(dn.destinations)
    return [[c.value for c in linha] for linha in wb[aba][ref.replace("$", "")]]


premissas = []
wp = wb["Premissas"]
for linha in range(8, wp.max_row + 1):
    desc, nome, valor, status, fonte = (wp["B%d" % linha].value, wp["C%d" % linha].value, wp["D%d" % linha].value,
                                        wp["J%d" % linha].value, wp["K%d" % linha].value)
    if desc and valor is not None and status and status != "Fórmula":
        premissas.append({"descricao": desc, "nome": nome, "valor": valor, "unidade": wp["I%d" % linha].value,
                          "status": status, "fonte": fonte, "linha": linha})

saida = {"numeros": numeros, "origem": origem, "g1": tabela("res_g1"), "g2": tabela("res_g2"), "g3": tabela("res_g3"),
         "g4": tabela("res_g4"), "premissas": premissas}
(AQUI / "resumo.json").write_text(json.dumps(saida, ensure_ascii=False, indent=1), encoding="utf-8")
print("ok: %d números, %d premissas" % (len(numeros), len(premissas)))
