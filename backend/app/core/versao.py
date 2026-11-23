"""Versão da plataforma: fonte única. A API, o rodapé do hub e a esteira de CI leem daqui.
A extensão (manifest.json), o pyproject e o package.json do front repetem o número porque o Chrome e as
ferramentas de build exigem; scripts/verifica_versao.py falha a esteira se algum divergir."""
VERSAO = "8.3.0"
VERSAO_CURTA = ".".join(VERSAO.split(".")[:2])   # "8.1", como aparece para as pessoas
