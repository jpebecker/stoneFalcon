"""F8.5: o Excel recalculado bate com calculadora.projetar()?

Compara, para os cenários Base, Conservador, Otimista e Base medido, o fluxo e o acumulado
mês a mês (tolerância de R$ 1), além de VPL, TIR e payback. Depois muda uma premissa no
próprio Excel (cópia temporária), recalcula e confere de novo: prova que as fórmulas estão vivas.

Uso:  .venv/Scripts/python.exe testar_consistencia.py   (rodar depois de recalcular.py)
"""
from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

from openpyxl import load_workbook

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "backend"))
from app.finance.calculadora import projetar  # noqa: E402
from app.finance.premissas import Premissas  # noqa: E402

ARQ = RAIZ / "entregaveis" / "analise-financeira.xlsx"
TOL = 1.0
CAMPOS = ["investimento_inicial", "modulos_integracao", "incluir_modulos", "hospedagem_mensal", "sustentacao_mensal", "usuarios",
          "adocao_alvo", "meses_rampa", "tarefas_por_usuario_dia", "dias_uteis", "minutos_por_tarefa", "minutos_revisao_humana",
          "custo_hora", "aproveitamento", "custo_por_execucao", "meses", "taxa_desconto_anual", "taxa_erro_manual"]
COLS = {"Base": "E", "Conservador": "F", "Otimista": "G", "Base medido": "H"}


def premissas_do_excel(wb, col: str) -> Premissas:
    ws = wb["Premissas"]
    linha = {ws["C%d" % r].value: r for r in range(1, ws.max_row + 1)}
    v = {c: ws["%s%d" % (col, linha[c])].value for c in CAMPOS}
    v["incluir_modulos"] = bool(v["incluir_modulos"])
    for c in ("usuarios", "meses_rampa", "dias_uteis", "meses"):
        v[c] = int(round(v[c]))
    return Premissas(**v)


def conferir(wb, rotulo: str) -> list[str]:
    falhas = []
    m = wb["Motor"]
    col_de = {m.cell(3, c).value: c for c in range(2, m.max_column + 1)}
    for nome, col in COLS.items():
        p = premissas_do_excel(wb, col)
        r = projetar(p)
        c = col_de[nome]
        for mes in r["meses"]:
            fx, ax = m.cell(36 + mes["mes"], c).value, m.cell(98 + mes["mes"], c).value
            if abs(fx - mes["fluxo"]) > TOL or abs(ax - mes["acumulado"]) > TOL:
                falhas.append("%s/%s mês %d: Excel %.2f/%.2f × calc %.2f/%.2f" % (rotulo, nome, mes["mes"], fx, ax, mes["fluxo"], mes["acumulado"]))
        vpl, tir, pay = m.cell(22, c).value, m.cell(24, c).value, m.cell(25, c).value
        pay = None if isinstance(pay, str) else int(pay)
        if abs(vpl - r["vpl"]) > TOL:
            falhas.append("%s/%s VPL: %.2f × %.2f" % (rotulo, nome, vpl, r["vpl"]))
        if pay != r["payback_mes"]:
            falhas.append("%s/%s payback: %s × %s" % (rotulo, nome, pay, r["payback_mes"]))
        if r["tir_anual"] is not None and (isinstance(tir, str) or abs(tir - r["tir_anual"]) > 0.0005):
            falhas.append("%s/%s TIR: %s × %s" % (rotulo, nome, tir, r["tir_anual"]))
        print("  %-12s %-12s payback %-12s VPL R$ %12s  TIR %7s  | calculadora: %s, R$ %s, %s" % (
            rotulo, nome, pay or "não se paga", "{:,.0f}".format(vpl), "{:.1%}".format(tir) if not isinstance(tir, str) else tir,
            r["payback_mes"], "{:,.0f}".format(r["vpl"]), r["tir_anual"]))
    # a aba Fluxo de caixa (cenário em uso) também precisa bater
    f = wb["Fluxo de caixa"]
    ativo = wb["Premissas"]["D4"].value
    r = projetar(premissas_do_excel(wb, COLS[ativo]))
    for mes in r["meses"]:
        if abs(f["J%d" % (16 + mes["mes"])].value - mes["fluxo"]) > TOL:
            falhas.append("%s/Fluxo de caixa mês %d" % (rotulo, mes["mes"]))
    if abs(f["B5"].value - r["vpl"]) > TOL or abs(f["B10"].value - r["custo_total"]) > TOL or abs(f["B12"].value - r["beneficio_total"]) > TOL:
        falhas.append("%s/Fluxo de caixa: VPL, custo ou benefício total" % rotulo)
    return falhas


def recalcular(caminho: Path, mudancas: dict[str, object]) -> None:
    import win32com.client as win32
    xl = win32.DispatchEx("Excel.Application")
    xl.Visible = False
    xl.DisplayAlerts = False
    try:
        wb = xl.Workbooks.Open(str(caminho))
        for ref, v in mudancas.items():
            aba, cel = ref.split("!")
            wb.Worksheets(aba).Range(cel).Value = v
        xl.CalculateFull()
        wb.Save()
        wb.Close(False)
    finally:
        xl.Quit()


def main() -> int:
    print("1) Arquivo entregue")
    falhas = conferir(load_workbook(ARQ, data_only=True), "entregue")
    print("2) Premissa alterada no Excel (adoção do Base 25% -> 20%, sustentação -> R$ 12 mil, cenário em uso = Otimista)")
    ws = load_workbook(ARQ)["Premissas"]
    linha = {ws["C%d" % r].value: r for r in range(1, ws.max_row + 1)}
    with tempfile.TemporaryDirectory() as tmp:
        copia = Path(tmp) / "copia.xlsx"
        shutil.copy(ARQ, copia)
        recalcular(copia, {"Premissas!E%d" % linha["adocao_alvo"]: 0.20, "Premissas!E%d" % linha["sustentacao_mensal"]: 12000,
                           "Premissas!D4": "Otimista"})
        falhas += conferir(load_workbook(copia, data_only=True), "alterado")
    if falhas:
        print("FALHOU (%d):" % len(falhas))
        for f in falhas[:40]:
            print("  -", f)
        return 1
    print("OK: Excel e calculadora.projetar() batem mês a mês (tolerância R$ %.0f), inclusive depois de mudar premissas." % TOL)
    return 0


if __name__ == "__main__":
    sys.exit(main())
