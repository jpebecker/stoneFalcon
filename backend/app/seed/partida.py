"""O que a partida faz com o banco: semeia se vazio, mantém se atual, refaz o estado inicial se antigo (v8.3).

`STONEFALCON_SEMEAR=0` desliga tudo isto (quem chama não chega aqui). Refazer apaga o banco, inclusive a trilha de auditoria:
é o mesmo "Reiniciar a demonstração" da tela, por isso só acontece quando o selo do seed falta ou é mais antigo.
"""
import logging

from sqlmodel import Session

from . import selo
from .demo import semear

registro = logging.getLogger("stonefalcon.semente")


def preparar(s: Session) -> str:
    """Devolve "semeado" (banco vazio), "mantido" (selo atual) ou "reiniciado" (sem selo ou selo antigo)."""
    if semear(s):
        registro.info("Banco vazio: demonstração semeada (versão do seed %s).", selo.VERSAO_SEMENTE)
        return "semeado"
    if selo.atualizado(s):
        return "mantido"
    antes = selo.ler(s)
    registro.warning(
        "Este banco foi semeado por uma versão antiga da demonstração (selo do seed: %s; atual: %s). Refazendo o estado inicial, "
        "como o \"Reiniciar a demonstração\": os alertas e os processos de demonstração novos passam a existir.",
        antes if antes is not None else "ausente", selo.VERSAO_SEMENTE)
    from ..roteiros.reinicio import reiniciar
    reiniciar(s)
    return "reiniciado"
