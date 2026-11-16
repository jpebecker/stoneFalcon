"""Premissas financeiras. Fonte: docs/custos-estimados.txt (documento de custos da equipe)
e premissas próprias marcadas como A VALIDAR num piloto. Tudo editável na calculadora."""
from pydantic import BaseModel, Field


class Premissas(BaseModel):
    # ---- investimento (docs/custos-estimados.txt) ----
    investimento_inicial: float = Field(690_000, ge=0, description="Desenvolvimento + implantação, com 15% de contingência")
    modulos_integracao: float = Field(300_000, ge=0, description="Pacote de 4 módulos de integração (conectores do catálogo)")
    incluir_modulos: bool = True
    # ---- custo fixo mensal (docs/custos-estimados.txt, valores no teto) ----
    hospedagem_mensal: float = Field(6_900, ge=0, description="Hospedagem + domínio + n8n (teto da faixa R$ 2,8 a 6,9 mil)")
    sustentacao_mensal: float = Field(16_000, ge=0, description="Time de sustentação")
    # ---- uso (premissas a validar) ----
    usuarios: int = Field(6_000, ge=0, description="Colaboradores com acesso")
    adocao_alvo: float = Field(0.25, ge=0, le=1, description="Fração que usa agentes ao fim da rampa")
    meses_rampa: int = Field(12, ge=1, le=36)
    tarefas_por_usuario_dia: float = Field(1.0, ge=0, description="Execuções de agente por usuário ativo por dia útil")
    dias_uteis: int = Field(22, ge=1, le=31)
    # ---- valor (premissas a validar) ----
    minutos_por_tarefa: float = Field(10, ge=0, description="Tempo da tarefa feita à mão (média dos agentes, se houver)")
    minutos_revisao_humana: float = Field(2, ge=0, description="Tempo que a pessoa ainda gasta conferindo o resultado do agente")
    custo_hora: float = Field(45.0, ge=0, description="R$ por hora de trabalho (salário + encargos, média estimada)")
    aproveitamento: float = Field(0.5, ge=0, le=1, description="Fração do tempo liberado que vira ganho real")
    custo_por_execucao: float = Field(0.03, ge=0, description="R$ em tokens por execução (medido, se houver dados)")
    # ---- análise ----
    meses: int = Field(36, ge=6, le=60)
    taxa_desconto_anual: float = Field(0.12, ge=0, le=1)
    taxa_erro_manual: float = Field(0.08, ge=0, le=1, description="Retrabalho no processo manual (premissa a validar)")

    @property
    def investimento_total(self) -> float:
        return self.investimento_inicial + (self.modulos_integracao if self.incluir_modulos else 0)

    @property
    def custo_fixo_mensal(self) -> float:
        return self.hospedagem_mensal + self.sustentacao_mensal

    @property
    def ganho_por_tarefa(self) -> float:
        return max(self.minutos_por_tarefa - self.minutos_revisao_humana, 0) / 60 * self.custo_hora * self.aproveitamento
