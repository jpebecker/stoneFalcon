"""Busca por nome de lojistas e colaboradores: ninguém digita código nos campos do agente."""
import unicodedata

from fastapi import APIRouter, Depends

from ..core.identidade import CONSULTA_COLABORADORES, PERSONAS, Persona, usuario_atual
from ..tools import dados_ficticios as fx

rotas = APIRouter(prefix="/api/v1", tags=["cadastros"])


def _norm(texto: str) -> str:
    t = unicodedata.normalize("NFD", (texto or "").lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


@rotas.get("/lojistas")
def lojistas(q: str = "", limite: int = 20, _p: Persona = Depends(usuario_atual)):
    """Lojistas por nome, cidade ou código. O código aparece como detalhe, não como pergunta."""
    alvo = _norm(q)
    achados = [l for l in fx.LOJISTAS.values()
               if not alvo or alvo in _norm(l["nome"]) or alvo in _norm(l["cidade"]) or alvo in l["id"].lower()
               or alvo in _norm(l["segmento"])]
    return [{"id": l["id"], "nome": l["nome"], "cidade": l["cidade"], "segmento": l["segmento"], "plano": l["plano"]}
            for l in achados[:max(1, min(limite, 50))]]


@rotas.get("/areas")
def areas(_p: Persona = Depends(usuario_atual)):
    """As áreas da empresa (as que têm gente na demo), para escolher com quem compartilhar um processo."""
    vistas: dict[str, str] = {}
    for p in PERSONAS.values():
        vistas.setdefault(p.area, p.area_nome)
    return [{"id": i, "nome": n} for i, n in sorted(vistas.items(), key=lambda x: x[1])]


@rotas.get("/colaboradores")
def colaboradores(q: str = "", limite: int = 20, pessoa: Persona = Depends(usuario_atual)):
    """"Eu mesmo" sempre vem primeiro. Buscar outra pessoa por nome exige o papel de consulta a colaboradores (RH)."""
    eu = fx.COLABORADORES.get(pessoa.matricula)
    saida = []
    if eu:
        saida.append({"id": eu["id"], "nome": eu["nome"], "area": eu["area"], "eu": True})
    if pessoa.tem(CONSULTA_COLABORADORES):
        alvo = _norm(q)
        for c in fx.COLABORADORES.values():
            if c["id"] != pessoa.matricula and (not alvo or alvo in _norm(c["nome"]) or alvo in c["id"].lower()):
                saida.append({"id": c["id"], "nome": c["nome"], "area": c["area"], "eu": False})
    return {"itens": saida[:max(1, min(limite, 50))], "pode_buscar_outros": pessoa.tem(CONSULTA_COLABORADORES)}
