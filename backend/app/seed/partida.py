"""O que a partida faz com o banco: semeia se vazio, mantém se atual, refaz a demonstração completa se antigo ou vindo de um roteiro.

`STONEFALCON_SEMEAR=0` desliga tudo isto (quem chama não chega aqui). `STONEFALCON_DEMO_NOVA=1` força uma demonstração limpa a cada
partida. Refazer apaga o banco, inclusive a trilha de auditoria: é o mesmo "Reiniciar a demonstração" da tela, por isso só
acontece quando o selo do seed falta, é mais antigo, veio de um roteiro guiado (que começa sem alertas) ou quando se pede.
"""
import logging
import os

from sqlmodel import Session

from . import selo
from .demo import semear

registro = logging.getLogger("stonefalcon.semente")

DEMO_NOVA = "STONEFALCON_DEMO_NOVA"


def demo_nova_pedida() -> bool:
    return os.environ.get(DEMO_NOVA, "") not in ("", "0")


def preparar(s: Session) -> str:
    """Devolve "semeado" (banco vazio), "mantido" (selo atual, demonstração completa) ou "reiniciado" (refeito: sem selo, selo antigo,
    semeado por um roteiro guiado ou pedido com STONEFALCON_DEMO_NOVA=1)."""
    if semear(s):
        registro.info("Banco vazio: demonstração semeada (versão do seed %s).", selo.VERSAO_SEMENTE)
        return "semeado"
    if demo_nova_pedida():
        registro.warning("%s=1: refazendo a demonstração completa do zero (o banco e a trilha de auditoria foram apagados).", DEMO_NOVA)
    elif selo.atualizado(s):
        return "mantido"
    else:
        antes = selo.ler(s)
        de = selo.origem(s)
        if antes is not None and antes >= selo.VERSAO_SEMENTE and de != selo.ORIGEM_DEMO:
            registro.warning(
                "Este banco foi reiniciado por um roteiro guiado (%s), que começa sem alertas. Refazendo a demonstração completa, "
                "como o \"Reiniciar a demonstração\": os alertas voltam. (Reiniciar o servidor no meio de um roteiro perde o estado dele; "
                "o roteiro pode ser refeito em Roteiros.)", de)
        else:
            registro.warning(
                "Este banco foi semeado por uma versão antiga da demonstração (selo do seed: %s; atual: %s). Refazendo o estado inicial, "
                "como o \"Reiniciar a demonstração\": os alertas e os processos de demonstração novos passam a existir.",
                antes if antes is not None else "ausente", selo.VERSAO_SEMENTE)
    from ..roteiros.reinicio import reiniciar
    reiniciar(s)
    return "reiniciado"


def descrever(resultado: str) -> str:
    """Uma frase em português simples para o console de quem ligou o servidor (iniciar.bat / iniciar.sh)."""
    return {
        "semeado": "Demonstração criada do zero, com alertas para as 6 pessoas.",
        "mantido": "Demonstração mantida como estava (nada foi apagado).",
        "reiniciado": "Demonstração refeita do zero, com alertas para as 6 pessoas (o banco anterior e a trilha de auditoria foram apagados).",
    }[resultado]
