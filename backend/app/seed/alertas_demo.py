"""Alertas de demonstração (v8.1, ampliados na v8.3): cada persona entra na demo com uma pequena história de alertas.

NENHUM alerta é inserido direto. O que se molda é o ESTADO que as regras reais leem (o estado de sistemas integrados, o
histórico sintético de execuções, o orçamento de um processo e a queda de um provedor) e depois roda `alertas.avaliar`, a
mesma função que a vigia de 60 segundos usa. Por isso os alertas abrem, atualizam e fecham sozinhos como qualquer outro, e
aparecem na trilha. "Lido" e "em tratamento" passam pelas MESMAS funções que a tela usa (`alertas.marcar_lido` e
`tratamento.assumir`).

Cenário principal de cada persona (o que os roteiros guiados moldam no passo "veja e trate o seu alerta"):

  Marina  — o processo de dúvidas mais lento que o normal (as últimas execuções demoraram bem mais que a mediana)
  Rafael  — a triagem de chargebacks falhando (4 das últimas 10 execuções escaladas: o agente não concluiu)
  Carla   — orçamento do processo de férias a ≈ 88%
  Thiago  — o estoque lento: só o processo de trocas consulta o estoque do modelo
  Lucas   — "Listar transações do lojista" fora do ar: nenhum processo usa, então o alerta é só da Engenharia, e a triagem
            de incidentes do Lucas (que lê o estado dos sistemas) continua de pé para ele triar esse incidente
  Helena  — orçamento do processo de revisão de custo a ≈ 88% (e vê todos os alertas da empresa)

Só o estado inicial (`moldar`) acrescenta o resto da história de cada persona, sempre ligada ao que é dela (os roteiros
guiados começam limpos):

  1. HISTÓRICO: uma condição é moldada, a regra abre o alerta, a condição é desfeita e a regra fecha o alerta sozinha.
     Marina (dúvidas falhando), Rafael (orçamento da triagem), Carla (benefícios lentos), Thiago (trocas lentas) e
     Lucas/Helena (um provedor de IA fora do ar). Os alertas resolvidos guardam a hora real do seed: a trilha é encadeada e
     não aceita hora inventada.
  2. ABERTOS: o principal (não lido) mais um segundo alerta que a pessoa já leu e um terceiro que ela já assumiu, com nota.
     A Helena, que vê tudo e acompanha os outros, só deixa como não lidos os alertas principais.
  3. COMPARTILHADO: o "Registro de incidente de sistema" (Thiago, compartilhado com a Engenharia) está falhando. O mesmo alerta
     chega ao Thiago e ao Lucas, ainda não lido por nenhum dos dois: quem assumir ao vivo aparece "em tratamento" para o outro.

O estado inicial e o passo de cada roteiro contam a MESMA história principal: o roteiro começa limpo (veja
`roteiros/reinicio.py`) e o passo molda só o cenário da persona do roteiro. A moldagem é do sistema (ator "sistema" na trilha),
não de uma pessoa.
"""
from __future__ import annotations

import copy
import uuid
from collections.abc import Callable
from datetime import timedelta

from sqlmodel import Session, select

from ..agents.blueprint import Blueprint
from ..agents.governanca import estimar_custo
from ..audit import trilha
from ..core.identidade import PERSONAS
from ..core.relogio import agora
from ..finance.resumo import gasto_no_mes
from ..llm import balanceador, registro
from ..observability import alertas, tratamento
from ..processos import modelos as pm
from ..runtime import modelos as rm
from ..tools import executor
from . import catalogo, historico
from .historico import _passos

USO_DO_ORCAMENTO = 0.88      # entre 80% (atenção) e 100% (corte)
ESCALADAS_NA_JANELA = 4      # de 10: 40% (>= 30% abre "falhando", < 60% fica em atenção)
FATOR_LENTO = 3.0            # as execuções recentes demoram 3x: o p95 passa de 2x a mediana histórica
SISTEMA_LENTO_THIAGO = "consultar_estoque"   # só o processo de trocas usa
SISTEMA_FORA_LUCAS = "listar_transacoes"     # nenhum processo usa: alerta só da Engenharia
SISTEMA_LENTO_RAFAEL = "listar_chargebacks"  # só a triagem de chargebacks usa
PROVEDOR_DO_HISTORICO = "google"             # a queda que já passou (provedor de IA simulado)
NOME_COMPARTILHADO = "Registro de incidente de sistema"   # o processo do Thiago compartilhado com a Engenharia (Lucas)
MOLDAGEM = "cenário de demonstração"
CAMPOS_FALHA = ("status", "motivo", "resultado", "custo_usd", "custo_tudo_forte_usd", "por_modelo", "passos")

Desfazer = Callable[[], None]   # desfaz uma moldagem; a regra fecha o alerta na próxima avaliação


def _nada() -> None:
    pass


def _processo(s: Session, chave: str) -> pm.Processo | None:
    return _por_nome(s, catalogo.NOME_PROCESSO[chave])


def _por_nome(s: Session, nome: str) -> pm.Processo | None:
    return s.exec(select(pm.Processo).where(pm.Processo.nome == nome)).first()


def _janela(s: Session, p: pm.Processo) -> list[rm.Execucao]:
    """As últimas execuções que a regra avalia (mais recente primeiro)."""
    return s.exec(select(rm.Execucao).where(rm.Execucao.dono_tipo == "processo").where(rm.Execucao.dono_id == p.id)
                  .where(rm.Execucao.status != rm.AGUARDANDO)
                  .order_by(rm.Execucao.inicio.desc()).limit(alertas.JANELA_EXECUCOES)).all()


def _com_historico(s: Session, p: pm.Processo) -> None:
    """O processo criado ao vivo num roteiro ainda não tem histórico: gera o sintético dele (marcado como demonstração), o
    mesmo do estado inicial, para a regra ter sobre o que se apoiar."""
    tem = s.exec(select(rm.Execucao.id).where(rm.Execucao.dono_tipo == "processo").where(rm.Execucao.dono_id == p.id)
                 .where(rm.Execucao.demo == True)).first()  # noqa: E712
    if tem is None:
        historico.gerar(s, apenas={p.id})


def _guardar(e: rm.Execucao, campos: tuple[str, ...]) -> dict:
    return {c: copy.deepcopy(getattr(e, c)) for c in campos}


def _devolver(s: Session, antigos: dict[str, dict]) -> None:
    for eid, valores in antigos.items():
        e = s.get(rm.Execucao, eid)
        for campo, valor in valores.items():
            setattr(e, campo, valor)
        s.add(e)
    s.commit()


def _ligar_falhando(s: Session, p: pm.Processo) -> Desfazer:
    """Molda 4 das últimas 10 execuções SINTÉTICAS do processo como escaladas, pelo motivo que o histórico já usa. As execuções
    reais da pessoa (fora do histórico) nunca são tocadas. Devolve como desfazer."""
    _com_historico(s, p)
    if "processo_falhando" in alertas.regras_que_valem(s, p, "processo"):
        return _nada
    demo = [e for e in _janela(s, p) if e.demo]
    if len(demo) < alertas.MIN_EXECUCOES:
        return _nada
    motivo = "O agente não concluiu em 6 tentativas."
    antigos: dict[str, dict] = {}
    for e in demo[1::2][:ESCALADAS_NA_JANELA]:
        antigos[e.id] = _guardar(e, CAMPOS_FALHA)
        bp = Blueprint.model_validate(e.blueprint)
        e.status, e.motivo, e.resultado = rm.ESCALADA, motivo, None
        e.custo_usd = round(e.custo_usd * 0.4, 8)
        e.custo_tudo_forte_usd = round(e.custo_tudo_forte_usd * 0.4, 8)
        e.por_modelo = {k: {**v, "custo_usd": round(v["custo_usd"] * 0.4, 8)} for k, v in (e.por_modelo or {}).items()}
        e.passos = _passos(bp, estimar_custo(bp), e.custo_usd, rm.ESCALADA, motivo)
        s.add(e)
    s.commit()
    return lambda: _devolver(s, antigos)


def _ligar_lento(s: Session, p: pm.Processo) -> Desfazer:
    """Molda as últimas execuções SINTÉTICAS do processo para demorarem FATOR_LENTO vezes mais (a regra compara o p95 recente
    com a mediana das antigas). As execuções reais da pessoa nunca são tocadas. Devolve como desfazer."""
    _com_historico(s, p)
    if "processo_lento" in alertas.regras_que_valem(s, p, "processo"):
        return _nada
    antigos: dict[str, dict] = {}
    for e in (e for e in _janela(s, p) if e.demo):
        antigos[e.id] = _guardar(e, ("duracao_estimada_ms",))
        e.duracao_estimada_ms = int(e.duracao_estimada_ms * FATOR_LENTO)
        s.add(e)
    s.commit()
    return lambda: _devolver(s, antigos)


def _ao_menos_um_gasto_no_mes(s: Session, p: pm.Processo) -> None:
    """No primeiro dia do mês o histórico (que termina ontem) ainda não gastou nada: repete a execução sintética mais recente
    do processo, agora, para a razão do orçamento ter sobre o que se apoiar."""
    if gasto_no_mes(s, p.id, "processo") > 0:
        return
    ultima = s.exec(select(rm.Execucao).where(rm.Execucao.dono_tipo == "processo").where(rm.Execucao.dono_id == p.id)
                    .where(rm.Execucao.demo == True).order_by(rm.Execucao.inicio.desc())).first()  # noqa: E712
    if ultima is None:
        return
    quando = (agora() - timedelta(minutes=5)).isoformat()
    s.add(rm.Execucao(**{**ultima.model_dump(), "id": uuid.uuid4().hex[:12], "inicio": quando, "fim": quando}))
    s.commit()


def _ligar_orcamento(s: Session, p: pm.Processo) -> Desfazer:
    """Põe o orçamento do processo em USO_DO_ORCAMENTO do gasto do mês. Desfazer: volta ao orçamento anterior."""
    if "orcamento" in alertas.regras_que_valem(s, p, "processo"):
        return _nada
    _ao_menos_um_gasto_no_mes(s, p)
    gasto = gasto_no_mes(s, p.id, "processo")
    if gasto <= 0:
        return _nada
    anterior = p.orcamento_mensal_brl

    def definir(valor: float | None) -> None:
        proc = s.get(pm.Processo, p.id)
        antes = proc.orcamento_mensal_brl
        proc.orcamento_mensal_brl = valor
        proc.atualizado_em = agora().isoformat()
        s.add(proc)
        s.commit()
        trilha.registrar(s, "orcamento_definido", "sistema", proc.id, {"de": antes, "para": valor, "origem": MOLDAGEM}, dono_tipo="processo")

    definir(round(gasto / USO_DO_ORCAMENTO, 4))   # a tela arredonda em centavos; o gasto simulado é de centavos
    return lambda: definir(anterior)


# os roteiros guiados chamam estas (sem desfazer): moldam e deixam
def _falhando(s: Session, p: pm.Processo) -> None:
    _ligar_falhando(s, p)


def _lento(s: Session, p: pm.Processo) -> None:
    _ligar_lento(s, p)


def _orcamento_a_88(s: Session, p: pm.Processo) -> None:
    _ligar_orcamento(s, p)


def _cenario(s: Session, persona: str) -> None:
    """Molda o cenário principal de `persona` (o mesmo no estado inicial e no passo do roteiro)."""
    if persona == "marina":
        p = _processo(s, "duvida")
        if p is not None:
            _lento(s, p)
    elif persona == "rafael":
        p = _processo(s, "triagem")
        if p is not None:
            _falhando(s, p)
    elif persona in ("carla", "helena"):
        p = _processo(s, "ferias" if persona == "carla" else "custo_ia")
        if p is not None:
            _orcamento_a_88(s, p)
    elif persona == "thiago":
        executor.definir_falha(s, SISTEMA_LENTO_THIAGO, "lento", "sistema")
    elif persona == "lucas":
        executor.definir_falha(s, SISTEMA_FORA_LUCAS, "fora_do_ar", "sistema")


def moldar_persona(s: Session, persona: str) -> dict:
    """O passo "veja e trate o seu alerta" de um roteiro guiado: molda SÓ o cenário da persona (o roteiro começa limpo) e roda
    as regras. É idempotente: repetir não molda de novo nem abre alerta novo."""
    _cenario(s, persona)
    return alertas.avaliar(s)


# =============================================================
# A história completa do estado inicial (só `moldar`; os roteiros guiados começam limpos)
# =============================================================
def _aberto(s: Session, regra: str, processo: pm.Processo | None = None, conector: str | None = None) -> alertas.Alerta | None:
    q = select(alertas.Alerta).where(alertas.Alerta.regra == regra).where(alertas.Alerta.resolvido_em.is_(None))
    if processo is not None:
        q = q.where(alertas.Alerta.processo_id == processo.id)
    if conector is not None:
        q = q.where(alertas.Alerta.conector == conector)
    return s.exec(q).first()


def _historico_resolvido(s: Session, *ligar: Callable[[], Desfazer]) -> None:
    """Molda tudo, deixa as regras ABRIREM os alertas, desfaz e deixa as regras FECHÁ-LOS (duas rodadas para todas as
    histórias, que tocam coisas diferentes). Nada é escrito no alerta à mão."""
    desfazeres = [l() for l in ligar]
    alertas.avaliar(s)
    for desfazer in desfazeres:
        desfazer()
    alertas.avaliar(s)


def _provedor_que_caiu() -> Desfazer:
    if PROVEDOR_DO_HISTORICO not in registro.PROVEDORES:
        return _nada
    balanceador.marcar_fora(PROVEDOR_DO_HISTORICO, True)
    return lambda: balanceador.marcar_fora(PROVEDOR_DO_HISTORICO, False)


def _historias_resolvidas(s: Session) -> None:
    """Primeiro o que já passou, enquanto nada mais está moldado."""
    duvida, triagem, troca = _processo(s, "duvida"), _processo(s, "triagem"), _processo(s, "troca")
    beneficios = _por_nome(s, "Consulta de benefícios do colaborador")
    historias: list[Callable[[], Desfazer]] = [_provedor_que_caiu]             # Lucas e Helena: um provedor de IA caiu e voltou
    if duvida is not None:
        historias.append(lambda: _ligar_falhando(s, duvida))                   # Marina: o fluxo de dúvidas falhou e voltou
    if triagem is not None:
        historias.append(lambda: _ligar_orcamento(s, triagem))                 # Rafael: o orçamento da triagem foi revisto
    if beneficios is not None:
        historias.append(lambda: _ligar_lento(s, beneficios))                  # Carla: a consulta de benefícios ficou lenta e normalizou
    if troca is not None:
        historias.append(lambda: _ligar_lento(s, troca))                       # Thiago: as trocas ficaram lentas e normalizaram
    _historico_resolvido(s, *historias)


def _lido(s: Session, al: alertas.Alerta | None, pessoa: str) -> None:
    if al is not None:
        alertas.marcar_lido(s, al, PERSONAS[pessoa])


def _assumido(s: Session, al: alertas.Alerta | None, pessoa: str, nota: str) -> None:
    """A pessoa leu e assumiu: "em tratamento" com nota, pela mesma função que a tela usa."""
    if al is not None:
        alertas.marcar_lido(s, al, PERSONAS[pessoa])
        tratamento.assumir(s, al, PERSONAS[pessoa], nota)


def _historias_abertas(s: Session) -> list[alertas.Alerta]:
    """Além do principal, cada persona tem um alerta aberto que já leu e outro que assumiu. Devolve esses alertas
    (a Helena, que acompanha tudo, também já os leu)."""
    faq, decisao = _por_nome(s, "Consulta ao FAQ de atendimento"), _por_nome(s, "Registro da decisão de triagem")
    beneficios, pedidos = _por_nome(s, "Consulta de benefícios do colaborador"), _por_nome(s, "Pedidos de troca pendentes")
    compartilhado = _por_nome(s, NOME_COMPARTILHADO)
    ferias, troca, incidente, custo = _processo(s, "ferias"), _processo(s, "troca"), _processo(s, "incidente"), _processo(s, "custo_ia")
    # 1) molda tudo (o principal de cada persona já está moldado) e deixa as regras abrirem. Os processos que só leem arquivos
    #    não gastam com modelo, então a regra de orçamento só vale para os que têm um passo de IA.
    duvida = _processo(s, "duvida")
    if duvida is not None:
        _ligar_orcamento(s, duvida)
    for p in (faq, decisao, incidente, custo, ferias):
        if p is not None:
            _ligar_lento(s, p)
    for p in (beneficios, pedidos, compartilhado):
        if p is not None:
            _ligar_falhando(s, p)
    if troca is not None:
        _ligar_orcamento(s, troca)
    executor.definir_falha(s, SISTEMA_LENTO_RAFAEL, "lento", "sistema")
    alertas.avaliar(s)
    # 2) o que cada pessoa já fez com eles: ler (segundo alerta) e assumir com nota (terceiro)
    lidos = [
        (_aberto(s, "orcamento", duvida), "marina"), (_aberto(s, "processo_falhando", beneficios), "carla"),
        (_aberto(s, "conector_lento", conector=SISTEMA_LENTO_RAFAEL), "rafael"), (_aberto(s, "processo_falhando", pedidos), "thiago")]
    assumidos = [
        (_aberto(s, "processo_lento", faq), "marina", "Vendo se o arquivo do FAQ cresceu além do normal."),
        (_aberto(s, "processo_lento", ferias), "carla", "Pedi ao RH para conferir a fila de férias do mês."),
        (_aberto(s, "processo_lento", decisao), "rafael", "Conferindo se a lista de chargebacks cresceu além do normal."),
        (_aberto(s, "orcamento", troca), "thiago", "Conferindo o custo das trocas com a Logística."),
        (_aberto(s, "processo_lento", incidente), "lucas", "Investigando a demora na triagem de incidentes."),
        (_aberto(s, "processo_lento", custo), "helena", "Normal no fim do mês: a revisão lê o arquivo inteiro.")]
    # o estoque lento é o alerta principal do Thiago e só o segundo do Lucas (Engenharia): a Helena não o lê
    _lido(s, _aberto(s, "conector_lento", conector=SISTEMA_LENTO_THIAGO), "lucas")
    for al, pessoa in lidos:
        _lido(s, al, pessoa)
    for al, pessoa, nota in assumidos:
        _assumido(s, al, pessoa, nota)
    return [al for al, *_ in (*lidos, *assumidos) if al is not None]


def moldar(s: Session) -> dict:
    """Deixa o estado inicial como a história descrita no topo e roda as regras. Devolve o que a última rodada abriu."""
    _historias_resolvidas(s)
    for persona in ("marina", "rafael", "carla", "thiago", "lucas", "helena"):
        _cenario(s, persona)
    alertas.avaliar(s)                          # o alerta principal de cada persona abre, ainda não lido
    for al in _historias_abertas(s):
        _lido(s, al, "helena")                  # a Helena acompanha tudo: só os principais ficam como novidade para ela
    return alertas.avaliar(s)
