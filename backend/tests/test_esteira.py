"""A esteira de CI é código: as checagens dela têm teste (scripts/ na raiz do repositório)."""
import importlib.util
import json
import shutil
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]


def _carregar(nome: str):
    spec = importlib.util.spec_from_file_location(nome, RAIZ / "scripts" / f"{nome}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_extensao_do_repositorio_passa(tmp_path):
    assert _carregar("verifica_extensao").verificar(RAIZ / "extensao") == []


def test_manifesto_invalido_falha(tmp_path):
    v = _carregar("verifica_extensao")
    (tmp_path / "manifest.json").write_text("{ não é json", encoding="utf-8")
    assert any("inválido" in p for p in v.verificar(tmp_path))


def test_manifesto_sem_pasta_falha(tmp_path):
    assert _carregar("verifica_extensao").verificar(tmp_path / "nada")


def test_manifesto_que_cita_arquivo_inexistente_falha(tmp_path):
    v = _carregar("verifica_extensao")
    copia = tmp_path / "ext"
    shutil.copytree(RAIZ / "extensao", copia)
    (copia / "fundo.js").unlink()
    problemas = v.verificar(copia)
    assert any("fundo.js" in p for p in problemas)


def test_html_que_cita_script_inexistente_falha(tmp_path):
    v = _carregar("verifica_extensao")
    copia = tmp_path / "ext"
    shutil.copytree(RAIZ / "extensao", copia)
    (copia / "painel.js").unlink()
    assert any("painel.js" in p for p in v.verificar(copia))


def test_manifesto_sem_campo_obrigatorio_falha(tmp_path):
    v = _carregar("verifica_extensao")
    copia = tmp_path / "ext"
    shutil.copytree(RAIZ / "extensao", copia)
    m = json.loads((copia / "manifest.json").read_text(encoding="utf-8"))
    del m["version"]
    (copia / "manifest.json").write_text(json.dumps(m), encoding="utf-8")
    assert any("version" in p for p in v.verificar(copia))
