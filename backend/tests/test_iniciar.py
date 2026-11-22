"""v7/12: decisões dos scripts de início (iniciar.bat e iniciar.sh), em scripts/iniciar_ajuda.py."""
import importlib.util
import shutil
import socket
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]


def _ajuda():
    spec = importlib.util.spec_from_file_location("iniciar_ajuda", RAIZ / "scripts" / "iniciar_ajuda.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture()
def copia(tmp_path):
    """Uma cópia mínima do projeto: versão, requirements e o código das telas."""
    for rel in ("backend/app/core/versao.py", "backend/requirements.txt", "frontend/index.html", "frontend/package.json",
                "frontend/package-lock.json", "frontend/vite.config.ts", "frontend/tailwind.config.js"):
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(RAIZ / rel, tmp_path / rel)
    (tmp_path / "frontend/src").mkdir(parents=True)
    (tmp_path / "frontend/src/App.tsx").write_text("export default function App() { return null }", encoding="utf-8")
    return tmp_path


def _compilado(raiz: Path):
    (raiz / "frontend/dist").mkdir(parents=True, exist_ok=True)
    (raiz / "frontend/dist/index.html").write_text("<html></html>", encoding="utf-8")


# ---------- telas: pasta que já rodou a v6 abre as telas antigas se não recompilar ----------
def test_sem_telas_compiladas_precisa_compilar(copia):
    assert _ajuda().front_precisa_compilar(copia) is True


def test_pasta_que_ja_rodou_a_v6_recompila(copia):
    """dist/ da versão anterior (sem a marca da v7): o script da v7 compila de novo e só depois grava a marca."""
    a = _ajuda()
    _compilado(copia)
    assert a.front_precisa_compilar(copia) is True            # tinha dist/, mas nunca foi marcado pela v7
    a.marcar_front(copia)
    assert a.front_precisa_compilar(copia) is False


def test_mudou_a_versao_ou_o_codigo_das_telas_recompila(copia):
    a = _ajuda()
    _compilado(copia)
    a.marcar_front(copia)
    (copia / "frontend/src/App.tsx").write_text("export default function App() { return 1 }", encoding="utf-8")
    assert a.front_precisa_compilar(copia) is True
    a.marcar_front(copia)
    v = copia / "backend/app/core/versao.py"
    v.write_text(v.read_text(encoding="utf-8").replace('"8.2.0"', '"8.3.0"'), encoding="utf-8")
    assert a.front_precisa_compilar(copia) is True


def test_nova_tela_tambem_conta(copia):
    a = _ajuda()
    _compilado(copia)
    a.marcar_front(copia)
    (copia / "frontend/src/Nova.tsx").write_text("export const x = 1", encoding="utf-8")
    assert a.front_precisa_compilar(copia) is True


# ---------- dependências do back ----------
def test_mudar_as_dependencias_faz_reinstalar(copia, tmp_path):
    a = _ajuda()
    venv = tmp_path / "venv"
    assert a.deps_precisam_instalar(venv, copia) is True       # ainda não existe
    venv.mkdir()
    assert a.deps_precisam_instalar(venv, copia) is True       # existe (de uma versão anterior) mas sem a marca
    a.marcar_deps(venv, copia)
    assert a.deps_precisam_instalar(venv, copia) is False
    with open(copia / "backend/requirements.txt", "a", encoding="utf-8") as f:
        f.write("\nnova-dependencia==1.0\n")
    assert a.deps_precisam_instalar(venv, copia) is True


# ---------- mensagens claras em português ----------
@pytest.mark.parametrize("versao", [(3, 9, 18), (3, 10, 4), (2, 7, 18)])
def test_python_abaixo_de_3_11_gera_mensagem_clara(versao):
    msg = _ajuda().python_ok(versao)
    assert msg and "3.11" in msg and "python.org" in msg and "antigo" in msg


@pytest.mark.parametrize("versao", [(3, 11, 0), (3, 12, 3), (3, 14, 7)])
def test_python_3_11_ou_mais_novo_passa(versao):
    assert _ajuda().python_ok(versao) is None


def test_porta_ocupada_gera_mensagem_clara():
    a = _ajuda()
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as ocupando:
        ocupando.bind(("127.0.0.1", 0))
        ocupando.listen(1)
        porta = ocupando.getsockname()[1]
        msg = a.porta_livre(porta)
        assert msg and str(porta) in msg and "em uso" in msg and "STONEFALCON_PORTA" in msg
    assert a.porta_livre(porta) is None        # liberada, volta a passar


def test_versao_vem_da_fonte_unica():
    from app.core.versao import VERSAO
    assert _ajuda().versao(RAIZ) == VERSAO


# ---------- os scripts ----------
def test_os_dois_scripts_usam_o_mesmo_ajudante_e_a_mesma_porta():
    bat = (RAIZ / "iniciar.bat").read_text(encoding="utf-8")
    sh = (RAIZ / "iniciar.sh").read_text(encoding="utf-8")
    for script in (bat, sh):
        for chamada in ("iniciar_ajuda.py python", "iniciar_ajuda.py porta", "iniciar_ajuda.py front", "marcar-front",
                        "iniciar_ajuda.py deps", "marcar-deps", "STONEFALCON_PORTA", "STONEFALCON_SEM_NAVEGADOR"):
            assert chamada in script, chamada
    assert "STONEFALCON_SEM_PAUSA" in bat


def test_o_bat_tem_crlf_e_o_sh_tem_lf():
    assert b"\r\n" in (RAIZ / "iniciar.bat").read_bytes() or "eol=crlf" in (RAIZ / ".gitattributes").read_text(encoding="utf-8")
    assert b"\r\n" not in (RAIZ / "iniciar.sh").read_bytes()
    atributos = (RAIZ / ".gitattributes").read_text(encoding="utf-8")
    assert "*.bat text eol=crlf" in atributos and "*.sh text eol=lf" in atributos
