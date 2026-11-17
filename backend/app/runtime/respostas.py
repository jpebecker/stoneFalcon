"""Respostas pré-determinadas dos agentes (modo simulado e reserva do modo real).

O simulador deixa de devolver "Dados considerados: ..." e passa a escrever como um
analista escreveria, usando os dados que as ferramentas trouxeram. É determinístico:
a mesma entrada produz sempre o mesmo texto, então os roteiros da demonstração não
dependem de chave nem de sorte.

Entrada: um `Contexto` montado a partir da conversa do passo (dados dos passos
anteriores e resultados de ferramentas já chamadas).
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import date

_DADOS = re.compile(r"<dados origem=\"([^\"]*)\">\n(.*?)\n</dados>", re.S)
_HOJE = date(2026, 11, 15)


def _brl(v: float) -> str:
    return "R$ " + ("%.2f" % v).replace(".", ",") if v < 1000 else "R$ " + "{:,.0f}".format(v).replace(",", ".")


def _carregar(texto: str):
    try:
        return json.loads(texto)
    except (json.JSONDecodeError, TypeError):
        return None


@dataclass
class Contexto:
    entrada: dict = field(default_factory=dict)
    lojista: dict | None = None
    chargebacks: dict | None = None
    politicas: list[dict] = field(default_factory=list)
    colaborador: dict | None = None
    estoque: dict | None = None
    chamado: dict | None = None
    bloqueio: dict | None = None
    notificacao: dict | None = None
    slack: dict | None = None
    zendesk: dict | None = None
    instrucao: str = ""          # a tarefa do passo (o que o criador escreveu), para campos como o canal do Slack
    analise: str = ""            # conclusão de um passo anterior (texto)
    erros: list[str] = field(default_factory=list)

    def absorver(self, obj) -> None:
        """Classifica um resultado de ferramenta pelo formato dos campos."""
        if isinstance(obj, dict):
            if "cnpj" in obj and "plano" in obj:
                self.lojista = obj
            elif "contestacoes" in obj:
                self.chargebacks = obj
            elif "resultados" in obj:
                self.politicas += obj["resultados"]
            elif "saldo_ferias_dias" in obj:
                self.colaborador = obj
            elif "disponivel" in obj and "centro" in obj:
                self.estoque = obj
            elif "mensagem_id" in obj:
                self.slack = obj
            elif "chamado_id" in obj and ("assunto" in obj or "respostas" in obj):   # ler / responder no Zendesk
                self.zendesk = obj
            elif "chamado_id" in obj:
                self.chamado = obj
            elif "bloqueio_id" in obj:
                self.bloqueio = obj
            elif "notificacao_id" in obj:
                self.notificacao = obj


def montar(inicial: str, resultados: list[str], entrada: dict) -> Contexto:
    ctx = Contexto(entrada=entrada)
    tarefa = re.search(r"Tarefa deste passo: (.*)", inicial)
    ctx.instrucao = tarefa.group(1) if tarefa else ""
    for origem, bruto in _DADOS.findall(inicial):
        obj = _carregar(bruto)
        if obj is not None:
            ctx.absorver(obj)
        elif origem.startswith("passo:") and bruto.strip():
            ctx.analise += bruto.strip() + "\n"
    for r in resultados:
        if r.startswith("ERRO"):
            ctx.erros.append(r)
            continue
        achado = _DADOS.search(r)
        obj = _carregar(achado.group(2) if achado else r)
        if obj is not None:
            ctx.absorver(obj)
    return ctx


# ---------------------------------------------------------------- peças
def _primeiro_nome(nome: str) -> str:
    return (nome or "").split()[0] if nome else ""


def _meses_de_conta(l: dict) -> int:
    try:
        d = date.fromisoformat(l["cliente_desde"])
    except (KeyError, ValueError):
        return 0
    return max(0, (_HOJE.year - d.year) * 12 + _HOJE.month - d.month)


def _regra(ctx: Contexto) -> str:
    return ctx.politicas[0]["resposta"].strip() if ctx.politicas else ""


def nivel_risco(ctx: Contexto) -> str:
    q = int((ctx.chargebacks or {}).get("quantidade", 0))
    return "alto" if q >= 5 else "medio" if q >= 2 else "baixo"


# ---------------------------------------------------------------- textos
def _analise_risco(ctx: Contexto) -> str:
    l, c = ctx.lojista or {}, ctx.chargebacks or {}
    nome = "%s (%s)" % (l.get("nome", "O lojista"), l.get("id", ctx.entrada.get("lojista_id", "")))
    q, total, dias = int(c.get("quantidade", 0)), float(c.get("valor_total", 0)), c.get("dias", 7)
    fat = float(l.get("faturamento_mensal", 0))
    meses = _meses_de_conta(l)
    nivel = nivel_risco(ctx)
    peso = " (%d%% do faturamento mensal de %s)" % (round(total / fat * 100), _brl(fat)) if fat else ""
    if nivel == "alto":
        sinais = ["%d contestações em %d dias somando %s%s" % (q, dias, _brl(total), peso)]
        if meses and meses <= 6:
            sinais.append("conta aberta há apenas %d meses (desde %s)" % (meses, l.get("cliente_desde")))
        if fat:
            sinais.append("faturamento mensal declarado de %s no plano %s (segmento %s)" % (
                _brl(fat), l.get("plano", ""), (l.get("segmento") or "").lower()))
        texto = ("Há sinais de risco relevantes em %s: %s. " % (nome, "; ".join(sinais)))
        texto += "Risco ALTO."
        if ctx.politicas:
            texto += " Pela política de risco: " + _regra(ctx)
        texto += " Recomendo abrir chamado na fila risco e reter preventivamente os repasses, com a sua confirmação."
        return texto
    if nivel == "medio":
        return ("%s teve %d contestações em %d dias (%s). Risco MÉDIO: vale acompanhar na próxima semana, "
                "sem retenção de repasse por enquanto." % (nome, q, dias, _brl(total)))
    return ("%s teve %d contestações em %d dias (%s), dentro do esperado para o porte do negócio. "
            "Risco BAIXO: nenhuma ação além do acompanhamento de rotina." % (nome, q, dias, _brl(total)))


def _encaminhamento(ctx: Contexto) -> str:
    l = ctx.lojista or {}
    nome = l.get("nome") or "o lojista"
    partes = []
    if ctx.chamado:
        partes.append("Abri o chamado %s na fila %s para acompanhar %s." % (
            ctx.chamado["chamado_id"], ctx.chamado.get("fila", "risco"), nome))
    if ctx.bloqueio:
        partes.append("Retenção preventiva dos repasses registrada (%s), depois da confirmação do analista." %
                      ctx.bloqueio["bloqueio_id"])
    elif "sinais de risco relevantes" in ctx.analise:
        partes.append("Propus a retenção preventiva dos repasses; ela só vale depois da confirmação do analista.")
    else:
        partes.append("Sem sinais de risco relevantes, não propus retenção de repasse.")
    return " ".join(partes)


def _resposta_lojista(ctx: Contexto) -> str:
    l = ctx.lojista or {}
    pergunta = str(ctx.entrada.get("pergunta") or "").strip()
    saudacao = "Olá, equipe da %s!" % l["nome"] if l.get("nome") else "Olá!"
    if not ctx.politicas:
        return ("%s Obrigado pelo contato. Não encontrei na política uma regra que cubra exatamente esta dúvida; "
                "vou encaminhar para um especialista e retornamos pelo chat do aplicativo." % saudacao)
    plano = (" Como o seu plano é o %s, nada muda para você." % l["plano"]) if l.get("plano") else ""
    return ("%s Sobre a sua dúvida: %s%s Se precisar de mais alguma coisa, é só chamar pelo chat do aplicativo."
            % (saudacao, _regra(ctx), plano))


def _resposta_ferias(ctx: Contexto) -> str:
    c = ctx.colaborador or {}
    if not c:
        return "Não consegui localizar a ficha do colaborador; confira a matrícula e tente de novo."
    nome = _primeiro_nome(c.get("nome", ""))
    benef = ", ".join(c.get("beneficios", []))
    texto = "Olá, %s! Você tem %s dias de férias disponíveis (admissão em %s)." % (
        nome, c.get("saldo_ferias_dias"), c.get("admissao"))
    if ctx.politicas:
        texto += " " + _regra(ctx)
    if benef:
        texto += " Seus benefícios ativos: %s." % benef
    return texto


def _chamado_troca(ctx: Contexto) -> str:
    l, e = ctx.lojista or {}, ctx.estoque or {}
    texto = ""
    if ctx.chamado:
        texto = "Abri o chamado %s na fila %s para a troca da maquininha de %s." % (
            ctx.chamado["chamado_id"], ctx.chamado.get("fila", "logistica"), l.get("nome", "o lojista"))
    if e:
        baixo = " (estoque baixo: ofereça um modelo equivalente se preciso)" if int(e["disponivel"]) < 10 else ""
        texto += " Há %s unidades do %s em estoque no %s%s; o envio sai em até %s dia(s) útil(eis) para %s." % (
            e["disponivel"], e["modelo"], e["centro"], baixo, e["prazo_envio_dias"], l.get("cidade", "o endereço cadastrado"))
    return texto.strip() or "Chamado de troca registrado."


def _aviso_lojista(ctx: Contexto) -> str:
    l = ctx.lojista or {}
    texto = "Avisei %s por e-mail" % l.get("nome", "o lojista")
    if ctx.notificacao:
        texto += " (%s)" % ctx.notificacao["notificacao_id"]
    return texto + ": a troca foi solicitada e o equipamento novo sai do centro de distribuição em breve, com código de rastreio por mensagem."


def _aviso_canal(ctx: Contexto) -> str:
    s = ctx.slack or {}
    l, e = ctx.lojista or {}, ctx.estoque or {}
    texto = "Avisei o canal %s no Slack%s" % (s.get("canal", "#logistica"), " (%s)" % s["mensagem_id"] if s.get("mensagem_id") else "")
    if e:
        texto += ": troca de %s para %s" % (e.get("modelo", "maquininha"), l.get("nome", "o lojista"))
    return texto + "."


def compor(ctx: Contexto, titulo: str, tools_passo: list[str], usou_ferramentas: bool) -> str | None:
    """Texto final do passo, ou None para deixar o texto genérico. Escolhe pelo que há nos dados."""
    f = set(tools_passo)
    if f and not usou_ferramentas:
        return None   # ainda vai chamar as ferramentas; o texto final vem depois
    if "slack_enviar_mensagem" in f:
        return _aviso_canal(ctx)
    if "zendesk_responder_chamado" in f:
        z = ctx.zendesk or {}
        return "Respondi o chamado %s no Zendesk." % z.get("chamado_id", ctx.entrada.get("chamado_id", ""))
    if "enviar_notificacao" in f:
        return _aviso_lojista(ctx)
    if "abrir_chamado" in f and ctx.estoque is not None:
        return _chamado_troca(ctx)
    if f & {"abrir_chamado", "bloquear_repasse"}:
        return _encaminhamento(ctx)
    if ctx.chargebacks is not None and ctx.lojista is not None:
        return _analise_risco(ctx)
    if ctx.colaborador is not None:
        return _resposta_ferias(ctx)
    if ctx.lojista is not None and ("pergunta" in ctx.entrada or ctx.politicas):
        return _resposta_lojista(ctx)
    return None


def campo_para_ferramenta(campo: str, ferramenta: str, ctx: Contexto, titulo: str) -> str | None:
    """Texto realista para os campos livres de uma ferramenta (título e descrição do chamado, aviso...)."""
    l, e = ctx.lojista or {}, ctx.estoque or {}
    nome = "%s (%s)" % (l.get("nome", "lojista"), l.get("id", ctx.entrada.get("lojista_id", "")))
    if ferramenta == "slack_enviar_mensagem":
        if campo == "canal":
            achado = re.search(r"#[\w-]+", ctx.instrucao)
            return achado.group(0) if achado else None
        if campo == "mensagem":
            protocolo = re.search(r"chamado (CH-\d+)", ctx.analise)
            prazo = re.search(r"em até (\d+) dia", ctx.analise)
            baixo = e and int(e.get("disponivel", 99)) < 10
            return ("Troca de %s para %s%s.%s%s" % (
                e.get("modelo", "maquininha"), nome, " (chamado %s)" % protocolo.group(1) if protocolo else "",
                " Estoque baixo (%s unidade(s)): avaliar modelo equivalente." % e["disponivel"] if baixo else "",
                " Envio em até %s dia(s) útil(eis)." % prazo.group(1) if prazo else ""))
    if ferramenta == "zendesk_responder_chamado" and campo == "resposta":
        z = ctx.zendesk or {}
        regra = _regra(ctx)
        return "Olá, equipe da %s! %s Qualquer dúvida, é só responder por aqui." % (
            z.get("solicitante", "loja"), regra or "Estamos verificando o seu caso e retornamos em breve.")
    if ferramenta == "enviar_notificacao":
        if campo == "destino" and l.get("email"):
            return l["email"]
        if campo == "mensagem":
            protocolo = re.search(r"chamado (CH-\d+)", ctx.analise)
            prazo = re.search(r"em até (\d+) dia", ctx.analise)
            return ("Olá! Sua solicitação de troca de maquininha foi registrada%s. O equipamento novo sai em até %s dia(s) útil(eis) "
                    "e você receberá o código de rastreio por mensagem."
                    % (" (protocolo %s)" % protocolo.group(1) if protocolo else "", prazo.group(1) if prazo else "alguns"))
    if ferramenta in ("abrir_chamado", "bloquear_repasse"):
        if ctx.chargebacks is not None:
            c = ctx.chargebacks
            if campo == "titulo":
                return "Triagem de chargebacks: %s" % nome
            if campo in ("descricao", "motivo"):
                return ("%s teve %d contestações em %d dias (%s). Nível de risco: %s. Conta desde %s."
                        % (nome, c["quantidade"], c["dias"], _brl(float(c["valor_total"])),
                           nivel_risco(ctx).upper(), l.get("cliente_desde", "?")))
        if "sinais de risco relevantes" in ctx.analise and campo == "motivo":
            achado = re.search(r"em ([^:]+): (\d+ contestações[^.]*)", ctx.analise)
            return ("Retenção preventiva: %s." % achado.group(2)) if achado else None
        if "sinais de risco relevantes" in ctx.analise and campo in ("titulo", "descricao"):
            achado = re.search(r"sinais de risco relevantes em ([^:]+):", ctx.analise)
            quem = achado.group(1) if achado else "lojista"
            return ("Triagem de chargebacks: %s" % quem) if campo == "titulo" else                 ("Análise do agente: " + ctx.analise.strip()[:380])
        if e:
            relato = str(ctx.entrada.get("relato") or "").strip()
            if campo == "titulo":
                return "Troca de %s: %s" % (e["modelo"], nome)
            if campo == "descricao":
                return ("Troca por defeito. Relato do lojista: %s Estoque do modelo: %s unidade(s) em %s."
                        % (relato or "(sem relato).", e["disponivel"], e["centro"]))
    return None
