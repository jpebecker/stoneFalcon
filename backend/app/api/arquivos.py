"""Plugin Arquivos e Planilhas (real): enviar, listar, abrir (prévia), baixar e remover os arquivos da página do plugin."""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlmodel import Session

from ..core.db import sessao
from ..core.identidade import Classificacao, Persona, exigir_aba, usuario_atual
from ..plugins import arquivos
from ..plugins import estado as plugins_estado
from ..plugins.arquivos import ErroArquivo

rotas = APIRouter(prefix="/api/v1/plugins/arquivos", tags=["arquivos"])


def _erro(e: ErroArquivo):
    raise HTTPException(status_code=e.status, detail=str(e))


def _integrado() -> None:
    if not plugins_estado.integrado(arquivos.PLUGIN_ID):
        raise HTTPException(status_code=409, detail="O plugin Arquivos e Planilhas não está integrado. Integre-o na aba Plugins.")


@rotas.get("/arquivos/limites")
def limites(pessoa: Persona = Depends(usuario_atual)):
    exigir_aba(pessoa, "plugins")
    return {**arquivos.LIMITES, "meu_nivel": pessoa.nivel.name.lower(),
            "classificacoes": [c.name.lower() for c in Classificacao if c <= pessoa.nivel]}


@rotas.get("/arquivos")
def listar(pessoa: Persona = Depends(usuario_atual), s: Session = Depends(sessao)):
    exigir_aba(pessoa, "plugins")
    _integrado()
    return [arquivos.publico(a, pessoa) for a in arquivos.listar(s, pessoa)]


class PedidoEnvio(BaseModel):
    nome: str = Field(max_length=200)
    conteudo_base64: str = Field(max_length=4_000_000)       # o limite de verdade (2 MB do arquivo) é conferido ao ler
    classificacao: str = "interna"
    areas: list[str] = Field(default_factory=list, max_length=20)


@rotas.post("/arquivos")
def enviar(pedido: PedidoEnvio, pessoa: Persona = Depends(usuario_atual), s: Session = Depends(sessao)):
    exigir_aba(pessoa, "plugins")
    _integrado()
    nivel = {c.name.lower(): int(c) for c in Classificacao}.get((pedido.classificacao or "").strip().lower())
    if nivel is None:
        raise HTTPException(status_code=422, detail="Escolha uma classificação: pública, interna, confidencial ou restrita.")
    try:
        a = arquivos.enviar_base64(s, pessoa, pedido.nome, pedido.conteudo_base64, nivel, pedido.areas)
    except ErroArquivo as e:
        _erro(e)
    return arquivos.publico(a, pessoa, previa=True)


@rotas.get("/arquivos/{arquivo_id}")
def abrir(arquivo_id: str, pessoa: Persona = Depends(usuario_atual), s: Session = Depends(sessao)):
    exigir_aba(pessoa, "plugins")
    _integrado()
    try:
        return arquivos.publico(arquivos.obter(s, pessoa, arquivo_id), pessoa, previa=True)
    except ErroArquivo as e:
        _erro(e)


@rotas.get("/arquivos/{arquivo_id}/download")
def baixar(arquivo_id: str, pessoa: Persona = Depends(usuario_atual), s: Session = Depends(sessao)):
    exigir_aba(pessoa, "plugins")
    _integrado()
    try:
        conteudo, tipo, nome = arquivos.baixar(s, pessoa, arquivo_id)
    except ErroArquivo as e:
        _erro(e)
    return Response(content=conteudo, media_type=tipo, headers={"Content-Disposition": 'attachment; filename="%s"' % nome.replace('"', "")})


@rotas.delete("/arquivos/{arquivo_id}")
def remover(arquivo_id: str, pessoa: Persona = Depends(usuario_atual), s: Session = Depends(sessao)):
    exigir_aba(pessoa, "plugins")
    _integrado()
    try:
        arquivos.remover(s, pessoa, arquivo_id)
    except ErroArquivo as e:
        _erro(e)
    return {"ok": True}
