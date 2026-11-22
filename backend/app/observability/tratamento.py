"""Tratamento de alertas (v8.1): assumir com uma nota, devolver e executar a ação de cada regra.

Um alerta pode ser ASSUMIDO por quem o recebe (ou pela Helena, que vê todos): fica "em tratamento · por X", com a nota e a
hora, para todos os destinatários. Dá para devolver. O fechamento continua automático (a regra fecha quando a condição some) e
guarda quem estava tratando. Cada regra oferece UMA ação primária, respeitando o perfil, que usa as mesmas funções das telas
atuais (pausa de emergência, orçamento, provedor, Saúde, a página do processo ou do agente) e assume o alerta sozinha. Alerta
assumido por outra pessoa só tem ação para o CoE de IA, que então o assume no lugar dela. Tudo vai para a trilha.
"""
from __future__ import annotations

from sqlmodel import Session

from ..agents.ciclo import ErroCiclo
from ..audit import trilha
from ..core.identidade import ENGENHARIA_PLATAFORMA, GESTOR_IA, PERSONAS, Persona
from ..core.relogio import agora
from ..llm import balanceador, registro
from .alertas import Alerta


class ErroTratamento(Exception):
    def __init__(self, msg: str, status: int = 409):
        super().__init__(msg)
        self.status = status


def _dono_tipo(al: Alerta) -> str:
    return "processo" if al.processo_id else "agente"


def _ref(al: Alerta) -> str | None:
    return al.processo_id or al.agente_id


def _nome(pessoa_id: str | None) -> str:
    return PERSONAS[pessoa_id].nome if pessoa_id in PERSONAS else (pessoa_id or "")


def _ciclo(al: Alerta):
    from ..agents.ciclo import ciclo as agentes
    from ..processos.tipo import ciclo as processos
    return processos if al.processo_id else agentes


def _com_outra_pessoa(al: Alerta, pessoa: Persona) -> bool:
    """O alerta está em tratamento por outra pessoa e `pessoa` não é do CoE de IA (que pode assumir no lugar)."""
    return bool(al.tratando_por) and al.tratando_por != pessoa.id and not pessoa.tem(GESTOR_IA)


# ---------- assumir e devolver ----------
def assumir(s: Session, al: Alerta, pessoa: Persona, nota: str = "", tomar: bool = False) -> Alerta:
    """Assume o alerta. Com `tomar` (só a ação do CoE de IA usa), assume no lugar de quem estava tratando; a trilha guarda quem era."""
    if al.resolvido_em:
        raise ErroTratamento("Este alerta já foi resolvido.")
    antes = al.tratando_por if al.tratando_por != pessoa.id else None
    if antes and not tomar:
        raise ErroTratamento("Este alerta já está em tratamento por %s." % _nome(al.tratando_por))
    al.tratando_por, al.tratando_nota, al.tratando_desde = pessoa.id, (nota or "").strip()[:300] or None, agora().isoformat()
    s.add(al)
    s.commit()
    dados = {"alerta": al.id, "regra": al.regra, "nota": al.tratando_nota}
    if antes:
        dados["tratando_antes"] = antes
    trilha.registrar(s, "alerta_assumido", pessoa.id, _ref(al), dados, dono_tipo=_dono_tipo(al))
    s.refresh(al)
    return al


def devolver(s: Session, al: Alerta, pessoa: Persona) -> Alerta:
    if not al.tratando_por:
        raise ErroTratamento("Este alerta não está em tratamento.")
    if al.tratando_por != pessoa.id and not pessoa.tem(GESTOR_IA):
        raise ErroTratamento("Só quem assumiu (ou o CoE de IA) devolve o alerta.", 403)
    antes = al.tratando_por
    al.tratando_por, al.tratando_nota, al.tratando_desde = None, None, None
    s.add(al)
    s.commit()
    trilha.registrar(s, "alerta_devolvido", pessoa.id, _ref(al), {"alerta": al.id, "regra": al.regra, "tratando_antes": antes},
                     dono_tipo=_dono_tipo(al))
    s.refresh(al)
    return al


# ---------- a ação primária de cada regra ----------
def _pode_pausar(s: Session, al: Alerta, pessoa: Persona) -> str | None:
    """"Pausar o processo/agente" se ainda estiver no ar e o perfil puder operá-lo (mesma regra da pausa de emergência)."""
    ref = _ref(al)
    if not ref:
        return None
    ciclo = _ciclo(al)
    try:
        a = ciclo.obter(s, ref)
    except ErroCiclo:
        return None
    from ..agents import modelos as am
    if a.estado != am.PUBLICADO or not ciclo.pode_operar(pessoa, a):
        return None
    return _dono_tipo(al)


def acao_para(s: Session, al: Alerta, pessoa: Persona) -> dict | None:
    """A ação que `pessoa` pode executar neste alerta, ou None (quem não pode não vê o botão)."""
    if al.resolvido_em or _com_outra_pessoa(al, pessoa):
        return None
    r = al.regra
    if r in ("processo_falhando", "agente_falhando") or (r == "conector_fora" and not pessoa.tem(ENGENHARIA_PLATAFORMA)):
        tipo = _pode_pausar(s, al, pessoa)
        if tipo:
            return {"id": "pausar", "rotulo": "Pausar o %s" % tipo, "pede": "motivo",
                    "ajuda": "A pausa de emergência também barra ações já pendentes."}
        return None
    if r in ("processo_lento", "agente_lento") and _ref(al):
        tipo = _dono_tipo(al)
        return {"id": "abrir", "rotulo": "Abrir o %s" % tipo, "pede": None,
                "rota": "/%s/%s" % ("processos" if tipo == "processo" else "agentes", _ref(al))}
    if r in ("conector_fora", "conector_lento"):
        return {"id": "abrir_sistema", "rotulo": "Abrir o sistema em Saúde", "pede": None, "rota": "/saude"}
    if r == "orcamento":
        ref = _ref(al)
        try:
            a = _ciclo(al).obter(s, ref) if ref else None
        except ErroCiclo:
            return None
        if a is not None and (pessoa.id == a.dono or pessoa.tem(GESTOR_IA)):
            return {"id": "revisar_orcamento", "rotulo": "Revisar o orçamento", "pede": "valor_brl", "atual": a.orcamento_mensal_brl}
        return None
    if r == "provedor_fora" and pessoa.tem(GESTOR_IA):
        return {"id": "restaurar_provedor", "rotulo": "Restaurar o provedor", "pede": None}
    return None


def executar_acao(s: Session, al: Alerta, pessoa: Persona, motivo: str = "", valor_brl: float | None = None) -> dict:
    """Executa a ação de `acao_para` e assume o alerta. Tudo o que pode recusar é checado ANTES da ação, para nunca agir
    e depois responder erro."""
    if _com_outra_pessoa(al, pessoa):
        raise ErroTratamento("Este alerta já está em tratamento por %s." % _nome(al.tratando_por))
    acao = acao_para(s, al, pessoa)
    if acao is None:
        raise ErroTratamento("Não há ação disponível para o seu perfil neste alerta.", 403)
    if acao["id"] == "revisar_orcamento" and valor_brl is None:
        raise ErroTratamento("Informe o novo orçamento mensal.", 422)
    ciclo = _ciclo(al)
    resposta: dict = {"acao": acao["id"]}
    try:
        if acao["id"] == "pausar":
            ciclo.pausar(s, pessoa, _ref(al), (motivo or "").strip() or "Pausa de emergência pelo alerta: %s" % al.titulo)
        elif acao["id"] == "revisar_orcamento":
            ciclo.definir_orcamento(s, pessoa, _ref(al), float(valor_brl))
        elif acao["id"] == "restaurar_provedor":
            pid = al.chave.split("::", 1)[-1]
            if pid in registro.PROVEDORES:
                balanceador.marcar_fora(pid, False)
                trilha.registrar(s, "provedor_normalizado", pessoa.id, None, {"provedor": pid})
        elif "rota" in acao:   # abrir o sistema em Saúde, abrir o processo ou o agente
            resposta["rota"] = acao["rota"]
    except ErroCiclo as e:
        raise ErroTratamento(str(e), e.status)
    if al.tratando_por != pessoa.id:
        assumir(s, al, pessoa, "Ação: %s." % acao["rotulo"], tomar=True)   # o CoE de IA pode ter agido no lugar de alguém
    trilha.registrar(s, "alerta_acao", pessoa.id, _ref(al), {"alerta": al.id, "regra": al.regra, "acao": acao["id"]},
                     dono_tipo=_dono_tipo(al))
    from . import avaliar_seguro
    avaliar_seguro(s)
    s.refresh(al)
    return resposta
