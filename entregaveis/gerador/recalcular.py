"""Recalcula a planilha no próprio Excel (via COM) e lista células com erro de fórmula.

Uso:  .venv/Scripts/python.exe recalcular.py [arquivo.xlsx]
Sai com código 1 se houver erro. (Substitui o LibreOffice, que não está instalado nesta máquina.)
"""
import json
import sys
from pathlib import Path

import win32com.client as win32
from openpyxl import load_workbook

ARQ = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parents[1] / "analise-financeira.xlsx").resolve()
ERROS = ("#REF!", "#VALUE!", "#DIV/0!", "#NAME?", "#N/A", "#NUM!", "#NULL!", "#SPILL!", "#CALC!")

xl = win32.DispatchEx("Excel.Application")
xl.Visible = False
xl.DisplayAlerts = False
try:
    wb = xl.Workbooks.Open(str(ARQ))
    xl.CalculateFull()
    wb.Save()
    wb.Close(False)
finally:
    xl.Quit()

vals = load_workbook(ARQ, data_only=True)
forms = load_workbook(ARQ)
total, achados = 0, {}
for ws in forms.worksheets:
    wv = vals[ws.title]
    for linha in ws.iter_rows():
        for c in linha:
            if isinstance(c.value, str) and c.value.startswith("="):
                total += 1
                v = wv[c.coordinate].value
                if isinstance(v, str) and v in ERROS:
                    achados.setdefault(v, []).append("%s!%s" % (ws.title, c.coordinate))
print(json.dumps({"arquivo": str(ARQ), "formulas": total, "erros": sum(len(v) for v in achados.values()),
                  "onde": {k: v[:30] for k, v in achados.items()}}, ensure_ascii=False, indent=1))
sys.exit(1 if achados else 0)
