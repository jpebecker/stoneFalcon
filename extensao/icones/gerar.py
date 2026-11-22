"""Gera os ícones da extensão (16, 32, 48 e 128 px) só com a biblioteca padrão do Python.

    python gerar.py

Desenha o rosto do falcão do StoneFalcon sobre um quadrado escuro arredondado, com suavização por
superamostragem 4x4. Os polígonos vêm de rosto.json, gerado por scripts/gera_falcao.mjs (não edite à mão).
"""
import json
import struct
import zlib
from pathlib import Path

PASTA = Path(__file__).resolve().parent


def _cor(hexa):
    return tuple(int(hexa[i:i + 2], 16) for i in (1, 3, 5))


ROSTO = json.loads((PASTA / "rosto.json").read_text(encoding="utf-8"))
LADO = ROSTO["lado"]
RAIO = ROSTO["raio"]
FUNDO = _cor(ROSTO["cores"]["fundo"])
# ordem de pintura do rosto: rosa, verde, claro
FORMAS = [(_cor(ROSTO["cores"][f["cor"]]), f["poligonos"]) for f in ROSTO["formas"]]


def dentro(poligono, x, y):
    """Regra do enrolamento não nulo, a mesma do preenchimento padrão do SVG."""
    volta = 0
    n = len(poligono)
    for i in range(n):
        x1, y1 = poligono[i]
        x2, y2 = poligono[(i + 1) % n]
        lado = (x2 - x1) * (y - y1) - (x - x1) * (y2 - y1)
        if y1 <= y < y2 and lado > 0:
            volta += 1
        elif y2 <= y < y1 and lado < 0:
            volta -= 1
    return volta != 0


def quadrado_arredondado(x, y, raio=RAIO):
    cx, cy = min(max(x, raio), LADO - raio), min(max(y, raio), LADO - raio)
    return (x - cx) ** 2 + (y - cy) ** 2 <= raio ** 2


def pixel(px, py, tamanho, sub=4):
    esc = LADO / tamanho
    acum = [0.0, 0.0, 0.0, 0.0]
    for sy in range(sub):
        for sx in range(sub):
            x, y = (px + (sx + 0.5) / sub) * esc, (py + (sy + 0.5) / sub) * esc
            if not quadrado_arredondado(x, y):
                continue
            cor = FUNDO
            for c, poligonos in FORMAS:
                if any(dentro(p, x, y) for p in poligonos):
                    cor = c
            for k in range(3):
                acum[k] += cor[k]
            acum[3] += 1
    total = sub * sub
    if not acum[3]:
        return (0, 0, 0, 0)
    return tuple(round(acum[k] / acum[3]) for k in range(3)) + (round(255 * acum[3] / total),)


def png(tamanho):
    linhas = []
    for y in range(tamanho):
        linhas.append(b"\x00" + b"".join(bytes(pixel(x, y, tamanho)) for x in range(tamanho)))
    bruto = b"".join(linhas)

    def bloco(tipo, dados):
        corpo = tipo + dados
        return struct.pack(">I", len(dados)) + corpo + struct.pack(">I", zlib.crc32(corpo) & 0xFFFFFFFF)

    return (b"\x89PNG\r\n\x1a\n" + bloco(b"IHDR", struct.pack(">IIBBBBB", tamanho, tamanho, 8, 6, 0, 0, 0))
            + bloco(b"IDAT", zlib.compress(bruto, 9)) + bloco(b"IEND", b""))


if __name__ == "__main__":
    pasta = PASTA
    for t in (16, 32, 48, 128):
        (pasta / ("icone%d.png" % t)).write_bytes(png(t))
        print("icone%d.png" % t)
