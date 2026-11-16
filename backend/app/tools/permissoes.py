"""Quem pode usar cada ferramenta.

Duas condições, as duas obrigatórias:
  1. a ÁREA da pessoa está entre as áreas do conector (ou o conector é para todos);
  2. o NÍVEL de acesso da pessoa cobre a CLASSIFICAÇÃO do conector.

A mesma checagem vale em dois momentos:
  - ao VINCULAR a ferramenta a um agente (permissão de quem cria);
  - a cada EXECUÇÃO (permissão de quem disparou). Um agente criado por alguém com
    mais acesso nunca vira porta dos fundos para quem tem menos.
"""
from dataclasses import dataclass

from ..core.identidade import Persona
from .catalogo import TODAS, Especificacao


@dataclass(frozen=True)
class Veredito:
    permitido: bool
    motivo: str


def avaliar(pessoa: Persona, esp: Especificacao) -> Veredito:
    if TODAS not in esp.areas and pessoa.area not in esp.areas:
        return Veredito(False, "A área %s não está autorizada a usar \"%s\"." % (pessoa.area_nome, esp.nome))
    if pessoa.nivel < esp.classificacao:
        return Veredito(False, "\"%s\" toca dados %s e o nível de acesso de %s é %s." % (
            esp.nome, esp.classificacao.name.lower(), pessoa.nome.split()[0], pessoa.nivel.name.lower()))
    return Veredito(True, "Permitido para %s (%s)." % (pessoa.nome.split()[0], pessoa.area_nome))
