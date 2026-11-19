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


# ---------- versão única (ticket 02) ----------
def test_saude_responde_a_versao_da_plataforma(api):
    from app.core.versao import VERSAO
    r = api.get("/api/v1/saude").json()
    assert r["versao"] == VERSAO == "8.0.0"


def test_api_openapi_usa_a_mesma_versao(api):
    from app.core.versao import VERSAO
    assert api.get("/openapi.json").json()["info"]["version"] == VERSAO


def test_versoes_do_repositorio_batem():
    assert _carregar("verifica_versao").verificar(RAIZ) == []


def _copia_minima(tmp_path):
    for rel in ("backend/app/core/versao.py", "backend/pyproject.toml", "extensao/manifest.json",
                "frontend/package.json", "frontend/package-lock.json"):
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(RAIZ / rel, tmp_path / rel)
    return tmp_path


def test_versao_divergente_da_extensao_falha(tmp_path):
    v = _carregar("verifica_versao")
    raiz = _copia_minima(tmp_path)
    m = json.loads((raiz / "extensao/manifest.json").read_text(encoding="utf-8"))
    m["version"] = "5.0.0"
    (raiz / "extensao/manifest.json").write_text(json.dumps(m), encoding="utf-8")
    assert any("manifest.json" in p and "5.0.0" in p for p in v.verificar(raiz))


def test_nome_da_extensao_sem_a_versao_falha(tmp_path):
    v = _carregar("verifica_versao")
    raiz = _copia_minima(tmp_path)
    m = json.loads((raiz / "extensao/manifest.json").read_text(encoding="utf-8"))
    m["name"] = "StoneFalcon"
    (raiz / "extensao/manifest.json").write_text(json.dumps(m), encoding="utf-8")
    assert any("StoneFalcon 8.0" in p for p in v.verificar(raiz))


def test_versao_divergente_do_front_e_do_pacote_do_back_falha(tmp_path):
    v = _carregar("verifica_versao")
    raiz = _copia_minima(tmp_path)
    p = raiz / "frontend/package.json"
    p.write_text(p.read_text(encoding="utf-8").replace('"8.0.0"', '"6.0.0"'), encoding="utf-8")
    t = raiz / "backend/pyproject.toml"
    t.write_text(t.read_text(encoding="utf-8").replace('version = "8.0.0"', 'version = "4.0.0"'), encoding="utf-8")
    problemas = v.verificar(raiz)
    assert any("package.json" in x for x in problemas) and any("pyproject" in x for x in problemas)


def test_npm_roda_de_dentro_do_frontend_e_nunca_com_prefix():
    """O npm 10.9 (o do Node 22 na esteira) ignora --prefix em install/ci e procura o package.json na raiz do repositório:
    a fumaça do Windows quebrou assim. Scripts de início e esteira rodam o npm de dentro de frontend."""
    for nome in ("iniciar.bat", "iniciar.sh", ".github/workflows/ci.yml"):
        texto = (RAIZ / nome).read_text(encoding="utf-8")
        comandos = [l for l in texto.splitlines() if "npm " in l and not l.lstrip().startswith(("rem ", "#"))]
        assert comandos, nome
        assert not any("--prefix" in l for l in comandos), nome
    assert "pushd frontend" in (RAIZ / "iniciar.bat").read_text(encoding="utf-8")
    assert "cd frontend" in (RAIZ / "iniciar.sh").read_text(encoding="utf-8")
