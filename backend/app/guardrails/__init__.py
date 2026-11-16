"""Guardrails silenciosos: o criador do agente não configura nada."""
from .mascaramento import limpar_saida, mascarar, restaurar, restaurar_seletivo

__all__ = ["mascarar", "restaurar", "restaurar_seletivo", "limpar_saida"]
