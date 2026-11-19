"""Gestão financeira: custos, retorno, orçamento, calculadora e indicadores da banca."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session

from ..agents import ciclo
from ..core.db import sessao
from ..core.identidade import GESTOR_IA, Persona, exigir, exigir_aba, usuario_atual
from ..finance import calculadora, resumo
from ..finance.premissas import Premissas
from ..llm import registro
from ..observability import avaliar_seguro
from ..seed import historico

rotas = APIRouter(prefix="/api/v1", tags=["financas"])


@rotas.get("/financas/resumo")
def financas_resumo(dias: int = 30, pessoa: Persona = Depends(usuario_atual), s: Session = Depends(sessao)):
    return resumo.resumo(s, pessoa, min(max(dias, 1), 365))


@rotas.post("/financas/exportar-planilha")
def financas_exportar(dias: int = 30, pessoa: Persona = Depends(usuario_atual), s: Session = Depends(sessao)):
    """Helena: grava o resumo de Finanças (por processo e agente) num arquivo novo do plugin Arquivos e Planilhas, que ela vê e baixa lá."""
    from ..core.relogio import agora
    from ..plugins import arquivos
    from ..plugins import estado as plugins_estado
    exigir(pessoa, GESTOR_IA)
    if not plugins_estado.integrado(arquivos.PLUGIN_ID):
        raise HTTPException(status_code=409, detail="Integre o plugin Arquivos e Planilhas (aba Plugins) para exportar a planilha.")
    r = resumo.resumo(s, pessoa, min(max(dias, 1), 365))
    colunas = ["tipo", "nome", "area", "execucoes", "concluidas", "custo_brl", "ganho_brl", "horas_liberadas", "roi"]
    linhas = [{"tipo": x["tipo"], "nome": x["nome"], "area": x["area"], "execucoes": x["execucoes"], "concluidas": x["concluidas"],
               "custo_brl": x["custo_brl"], "ganho_brl": x["ganho_brl"], "horas_liberadas": x["horas_liberadas"],
               "roi": "" if x["roi"] is None else x["roi"]} for x in r["por_agente"]]
    quando = agora()
    nome = "financas-%s.csv" % quando.strftime("%Y-%m-%d-%H%M%S")
    try:
        a = arquivos.criar_pelo_sistema(s, pessoa, nome, colunas, linhas, 1, ["gestao"])
    except arquivos.ErroArquivo as e:
        raise HTTPException(status_code=e.status, detail=str(e))
    return {"arquivo": arquivos.publico(a, pessoa), "linhas": len(linhas), "dias": r["dias"]}


@rotas.get("/financas/comparativo")
def financas_comparativo(modelo: str | None = None, dias: int = 30, pessoa: Persona = Depends(usuario_atual),
                         s: Session = Depends(sessao)):
    """"E se tudo rodasse em X?" (sem `modelo`, devolve o cenário de todos os modelos do registro)."""
    if modelo and not registro.existe(modelo):
        raise HTTPException(status_code=404, detail="Modelo desconhecido.")
    return resumo.comparativo(s, pessoa, min(max(dias, 1), 365), modelo)


@rotas.get("/financas/indicadores")
def financas_indicadores(dias: int = 30, pessoa: Persona = Depends(usuario_atual), s: Session = Depends(sessao)):
    """Os 5 indicadores do Painel executivo: só o CoE de IA (Finanças e a Calculadora usam resumo e premissas)."""
    exigir_aba(pessoa, "painel")
    return resumo.indicadores(s, pessoa, min(max(dias, 1), 365))


@rotas.get("/financas/premissas")
def premissas(pessoa: Persona = Depends(usuario_atual), s: Session = Depends(sessao)):
    """Valores iniciais do documento de custos + o que a plataforma já mediu (tempo da tarefa e custo por execução)."""
    pr = Premissas()
    i = resumo.indicadores(s, pessoa, 30)
    medidas = {}
    if i["execucoes"]:
        medidas = {"minutos_por_tarefa": i["tempo_execucao"]["manual_min"],
                   "custo_por_execucao": i["custo_operacional"]["agente_brl"]}
    return {"valores": pr.model_dump(), "medidas": medidas, "medidas_demo": i["tem_demo"],
            "descricoes": {k: f.description for k, f in Premissas.model_fields.items() if f.description}}


@rotas.post("/financas/calculadora")
def calcular(pr: Premissas, _p: Persona = Depends(usuario_atual)):
    r = calculadora.projetar(pr)
    r["ponto_de_equilibrio_execucoes_mes"] = calculadora.ponto_de_equilibrio(pr)
    return r


class PedidoOrcamento(BaseModel):
    valor_brl: float = Field(ge=0, le=1_000_000)


@rotas.put("/agentes/{agente_id}/orcamento")
def orcamento(agente_id: str, pedido: PedidoOrcamento, pessoa: Persona = Depends(usuario_atual), s: Session = Depends(sessao)):
    try:
        a = ciclo.definir_orcamento(s, pessoa, agente_id, pedido.valor_brl)
    except ciclo.ErroCiclo as e:
        raise HTTPException(status_code=e.status, detail=str(e))
    avaliar_seguro(s)
    s.refresh(a)
    return a.model_dump()


@rotas.put("/processos/{processo_id}/orcamento")
def orcamento_processo(processo_id: str, pedido: PedidoOrcamento, pessoa: Persona = Depends(usuario_atual), s: Session = Depends(sessao)):
    from ..processos.tipo import ciclo as ciclo_processos
    try:
        p = ciclo_processos.definir_orcamento(s, pessoa, processo_id, pedido.valor_brl)
    except ciclo.ErroCiclo as e:
        raise HTTPException(status_code=e.status, detail=str(e))
    avaliar_seguro(s)
    s.refresh(p)
    return p.model_dump()


@rotas.post("/demo/historico")
def demo_historico(pessoa: Persona = Depends(usuario_atual), s: Session = Depends(sessao)):
    exigir(pessoa, GESTOR_IA)
    historico.apagar(s)
    return {"execucoes": historico.gerar(s)}


@rotas.post("/demo/reiniciar")
def demo_reiniciar(pessoa: Persona = Depends(usuario_atual), s: Session = Depends(sessao)):
    """Volta a plataforma ao estado inicial da demonstração (antes de gravar ou apresentar)."""
    exigir(pessoa, GESTOR_IA)
    from ..roteiros.reinicio import reiniciar
    return reiniciar(s)


@rotas.delete("/demo/historico")
def demo_apagar(pessoa: Persona = Depends(usuario_atual), s: Session = Depends(sessao)):
    exigir(pessoa, GESTOR_IA)
    return {"apagadas": historico.apagar(s)}
