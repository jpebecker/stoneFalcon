"""Gera os ícones da extensão (16, 32, 48 e 128 px) só com a biblioteca padrão do Python.

    python gerar.py

Desenha a marca do StoneFalcon (falcão em três faces) sobre um quadrado escuro arredondado,
com suavização por superamostragem 4x4.
"""
import struct
import zlib
from pathlib import Path

FUNDO = (16, 32, 26)
VERDE = (31, 179, 122)
CLARO = (232, 243, 238)
ROSA = (224, 66, 143)
# formas no espaço 40x40 da marca da plataforma
FORMAS = [
    (VERDE, [(7, 10), (33, 10), (29.6, 17.4), (10.4, 17.4)]),
    (CLARO, [(12, 20.4), (28, 20.4), (25.1, 26.7), (14.9, 26.7)]),
    (ROSA, [(16.4, 29.6), (23.6, 29.6), (20, 35)]),
]


def dentro(poligono, x, y):
    n, certo = len(poligono), False
    for i in range(n):
        x1, y1 = poligono[i]
        x2, y2 = poligono[(i + 1) % n]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            certo = not certo
    return certo


def quadrado_arredondado(x, y, raio=9.0):
    cx, cy = min(max(x, raio), 40 - raio), min(max(y, raio), 40 - raio)
    return (x - cx) ** 2 + (y - cy) ** 2 <= raio ** 2


def pixel(px, py, tamanho, sub=4):
    esc = 40 / tamanho
    acum = [0.0, 0.0, 0.0, 0.0]
    for sy in range(sub):
        for sx in range(sub):
            x, y = (px + (sx + 0.5) / sub) * esc, (py + (sy + 0.5) / sub) * esc
            if not quadrado_arredondado(x, y):
                continue
            cor = FUNDO
            for c, forma in FORMAS:
                if dentro(forma, x, y):
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
    pasta = Path(__file__).resolve().parent
    for t in (16, 32, 48, 128):
        (pasta / ("icone%d.png" % t)).write_bytes(png(t))
        print("icone%d.png" % t)
