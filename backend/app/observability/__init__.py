"""Saúde e observabilidade nativas dos agentes."""
import logging

from sqlmodel import Session

log = logging.getLogger("stonefalcon.observabilidade")


def avaliar_seguro(s: Session) -> None:
    """Reavalia os alertas sem nunca derrubar quem chamou (execução, painel, ciclo periódico)."""
    from . import alertas
    try:
        alertas.avaliar(s)
    except Exception:  # alerta é efeito colateral: falha aqui não pode quebrar a execução
        log.exception("Falha ao avaliar alertas")
        s.rollback()
