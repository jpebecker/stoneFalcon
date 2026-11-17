"""v6: toda persona tem foto, servida pela própria plataforma; foto sem persona é erro."""
import struct
from pathlib import Path

from app.core.identidade import PERSONAS

PASTA = Path(__file__).resolve().parents[1] / "app" / "static" / "avatares"
LIMITE_KB = 200


def _dimensoes(arq: Path) -> tuple[int, int]:
    cab = arq.read_bytes()[:24]
    assert cab[:8] == b"\x89PNG\r\n\x1a\n", "%s não é um PNG" % arq.name
    return struct.unpack(">II", cab[16:24])


def test_toda_persona_tem_foto_e_nenhuma_foto_sobra():
    arquivos = {a.stem for a in PASTA.iterdir() if a.is_file()}
    assert set(PERSONAS) - arquivos == set(), "persona sem foto: %s" % (set(PERSONAS) - arquivos)
    assert arquivos - set(PERSONAS) == set(), "foto que não corresponde a nenhuma persona: %s" % (arquivos - set(PERSONAS))


def test_fotos_quadradas_e_leves():
    for pid in PERSONAS:
        arq = PASTA / (pid + ".png")
        largura, altura = _dimensoes(arq)
        assert largura == altura, "%s não é quadrada (%dx%d)" % (arq.name, largura, altura)
        assert arq.stat().st_size <= LIMITE_KB * 1024, "%s passa de %d KB" % (arq.name, LIMITE_KB)


def test_foto_e_servida_pela_propria_plataforma(api):
    perfis = {p["id"]: p for p in api.get("/api/v1/perfis").json()}
    for pid, p in perfis.items():
        assert p["foto"] == "/avatares/%s.png" % pid          # caminho local, nunca endereço externo
        r = api.get(p["foto"])
        assert r.status_code == 200 and r.headers["content-type"] == "image/png"
    assert api.get("/avatares/inexistente.png").status_code == 404
