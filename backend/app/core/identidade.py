"""Identidade e papéis (login simulado).

Em produção, isto vem do SSO da Stone: o token traz a pessoa, a área e os grupos.
No protótipo, o front envia o cabeçalho `X-Usuario` com o id de uma persona.

Dois eixos de permissão, de propósito separados:
  - PAPÉIS dizem o que a pessoa pode FAZER na plataforma (criar agente, revisar...).
  - NÍVEL DE ACESSO diz até que classificação de DADO ela pode tocar. Uma ferramenta
    só roda se o nível de quem DISPAROU o agente cobre a classificação da ferramenta.
"""
from dataclasses import dataclass, field
from enum import IntEnum

from fastapi import Header, HTTPException


class Classificacao(IntEnum):
    """Classificação da informação (ordem importa: maior = mais sensível)."""
    PUBLICA = 0
    INTERNA = 1
    CONFIDENCIAL = 2
    RESTRITA = 3


# Papéis na plataforma
CRIADOR = "criador"                    # cria e mantém agentes da própria área
USUARIO = "usuario"                    # executa agentes publicados a que tem acesso
CURADOR = "curador"                    # aprova respostas para a base de conhecimento da área
REVISOR_SEGURANCA = "revisor_seguranca"  # aprova publicação de agentes de risco alto
ENGENHARIA_PLATAFORMA = "engenharia"   # registra conectores no catálogo
CONSULTA_COLABORADORES = "consulta_colaboradores"   # busca outros colaboradores por nome (RH)
GESTOR_IA = "gestor_ia"                # vê custos, ROI, saúde e auditoria de toda a empresa


@dataclass(frozen=True)
class Persona:
    id: str
    nome: str
    area: str
    area_nome: str
    cargo: str
    nivel: Classificacao
    papeis: frozenset = field(default_factory=frozenset)
    matricula: str = ""            # a pessoa também é colaboradora: "Eu mesmo" nos campos de colaborador
    cor: str = "#1FB37A"           # avatar
    descricao: str = ""            # o que a pessoa faz na plataforma (tela "Quem é você hoje?")
    roteiro_id: str | None = None  # roteiro de demonstração dela

    def tem(self, papel: str) -> bool:
        return papel in self.papeis

    def publico(self) -> dict:
        return {
            "id": self.id, "nome": self.nome, "area": self.area, "area_nome": self.area_nome,
            "cargo": self.cargo, "nivel": self.nivel.name.lower(), "papeis": sorted(self.papeis),
            "matricula": self.matricula, "cor": self.cor, "descricao": self.descricao, "roteiro_id": self.roteiro_id,
            "iniciais": "".join(x[0] for x in self.nome.split()[:2]).upper(),
        }


def _p(id, nome, area, area_nome, cargo, nivel, *papeis, matricula="", cor="#1FB37A", descricao="", roteiro=None):
    return Persona(id, nome, area, area_nome, cargo, nivel, frozenset((USUARIO,) + papeis),
                   matricula, cor, descricao, roteiro)


# Pessoas e áreas FICTÍCIAS (as mesmas do v3, com papéis novos).
PERSONAS = {p.id: p for p in [
    _p("marina", "Marina Duarte", "atendimento", "Atendimento", "Analista de atendimento",
       Classificacao.INTERNA, CRIADOR, CURADOR, matricula="C601", cor="#1FB37A", roteiro="marina",
       descricao="Responde dúvidas de lojistas e cria o próprio agente, sem código."),
    _p("rafael", "Rafael Lima", "risco", "Prevenção a Fraudes", "Analista de risco",
       Classificacao.RESTRITA, CRIADOR, CURADOR, matricula="C602", cor="#E0428F", roteiro="rafael",
       descricao="Tria chargebacks e decide ações sensíveis, sempre com confirmação."),
    _p("carla", "Carla Nogueira", "pessoas", "Pessoas (RH)", "Business partner de RH",
       Classificacao.CONFIDENCIAL, CRIADOR, CURADOR, CONSULTA_COLABORADORES, matricula="C603", cor="#4A7BD0", roteiro="carla",
       descricao="Orienta férias e benefícios com dado confidencial protegido."),
    _p("thiago", "Thiago Moreira", "logistica", "Logística", "Analista de operações",
       Classificacao.INTERNA, CRIADOR, CURADOR, matricula="C604", cor="#E08A2E", roteiro="thiago",
       descricao="Troca de maquininha: cadastro, regra e estoque em paralelo."),
    _p("lucas", "Lucas Prado", "engenharia", "Engenharia de Plataforma", "Engenheiro de segurança",
       Classificacao.CONFIDENCIAL, REVISOR_SEGURANCA, ENGENHARIA_PLATAFORMA, matricula="C605", cor="#6B5BD0",
       roteiro="lucas", descricao="Governa o catálogo e revisa só os agentes de risco alto."),
    _p("helena", "Helena Castro", "gestao", "CoE de IA", "Gestora do CoE de IA",
       Classificacao.INTERNA, GESTOR_IA, matricula="C606", cor="#10201A", roteiro="helena",
       descricao="Prova o retorno e controla o custo da IA na empresa."),
]}


def obter_persona(persona_id: str) -> Persona:
    p = PERSONAS.get((persona_id or "").strip().lower())
    if not p:
        raise HTTPException(status_code=401, detail="Pessoa desconhecida. Entre com um dos perfis de demonstração.")
    return p


def usuario_atual(x_usuario: str = Header(default="", alias="X-Usuario")) -> Persona:
    """Dependência FastAPI: quem está chamando (SSO simulado)."""
    return obter_persona(x_usuario)


def exigir(persona: Persona, papel: str) -> None:
    if not persona.tem(papel):
        raise HTTPException(status_code=403, detail="Seu perfil não tem permissão para esta ação.")
