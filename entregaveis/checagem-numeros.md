# Checagem dos números da apresentação

Gerado por `entregaveis/gerador/gerar_apresentacao.js`. Cada número do deck aponta para uma célula da planilha `analise-financeira.xlsx`.

| Slide | Texto no slide | Número | Célula de origem | Calculado em |
|---|---|---|---|---|
| 9 | 1% | Tokens no custo total: menor entre os cenários | Resumo para slides!C11 | Cenários (linha 20) |
| 9 | 4% | Tokens no custo total: maior entre os cenários | Resumo para slides!C12 | Cenários (linha 20) |
| 9 | R$ 0,99 mi | Investimento total | Resumo para slides!C7 | Motor (Base) |
| 9 | R$ 690 mil | Investimento inicial (desenvolvimento + implantação + 15%) | Resumo para slides!C5 | Investimento (CAPEX)!D14 |
| 9 | R$ 300 mil | Módulos de integração (4 conectores) | Resumo para slides!C6 | Investimento (CAPEX)!E24 |
| 9 | R$ 22,9 mil | Operação mensal (hospedagem + sustentação) | Resumo para slides!C8 | Operação (OPEX)!C10 |
| 9 | 70% | Economia do roteador (mix de agentes da demo) | Resumo para slides!C13 | Tokens!E31 |
| 9 | R$ 0,017 | Custo de tokens por execução: modelado (agentes da demo) | Resumo para slides!C10 | Tokens!D40 |
| 9 | R$ 0,030 | Custo de tokens por execução: premissa do Base | Resumo para slides!C9 | Premissas |
| 10 | mês 21 | Payback do cenário Base (mês) | Resumo para slides!C14 | Cenários!B13 |
| 10 | R$ 0,77 mi | VPL do cenário Base (36 meses, 12% a.a.) | Resumo para slides!C15 | Cenários!B14 |
| 10 | 57% | TIR anual do cenário Base | Resumo para slides!C16 | Cenários!B15 |
| 10 | mês 17 | Payback do Base medido (mês) | Resumo para slides!C18 | Cenários!E13 |
| 10 | R$ 1,41 mi | VPL do Base medido | Resumo para slides!C19 | Cenários!E14 |
| 10 | mês 11 | Payback do Otimista (mês) | Resumo para slides!C23 | Cenários!D13 |
| 10 | R$ 4,22 mi | VPL do Otimista | Resumo para slides!C22 | Cenários!D14 |
| 10 | −R$ 0,77 mi | VPL do Conservador | Resumo para slides!C20 | Cenários!C14 |
| 10 | 15% | Adoção mínima para se pagar em 36 meses (acumulado ≥ 0) | Resumo para slides!C24 | Cenários!B35 |
| 11 | R$ 5 mil | Δ VPL com custo de tokens +20% | Resumo para slides, tabela do gráfico 3 (Sensibilidade!L) | Sensibilidade |
| 11 | R$ 0,24 mi | diferença 36m | derivado de Resumo para slides!C27, Resumo para slides!C28 | conta simples no slide |
| 11 | R$ 0,53 | Copilot Studio: custo por execução | Resumo para slides!C30 | Construir × comprar!C6 |
| 11 | 31× | múltiplo | derivado de Resumo para slides!C30, Resumo para slides!C10 | conta simples no slide |
| 11 | 1,5× | Volume em que construir empata com o Copilot (× o Base) | Resumo para slides!C29 | Construir × comprar!C17 |
| 12 | 70% | Economia do roteador (mix de agentes da demo) | Resumo para slides!C13 | Tokens!E31 |
| 13 | 3 | Duração do piloto (meses) | Resumo para slides!C32 | Premissas |
| 15 | R$ 0,91 mi | Pedido: tranche 1 (plataforma + 2 conectores + piloto) | Resumo para slides!C31 | Investimento (CAPEX)!E32 |
| 15 | 3 | Duração do piloto (meses) | Resumo para slides!C32 | Premissas |
| 15 | 15% | Adoção mínima para se pagar em 36 meses (acumulado ≥ 0) | Resumo para slides!C24 | Cenários!B35 |
| 15 | 7 min | meta minutos | derivado de Resumo para slides!C26 | conta simples no slide |
| 15 | 6,9 | Minutos mínimos por tarefa para se pagar em 36 meses | Resumo para slides!C26 | Cenários!B36 |
| 16 | R$ 690.000 | Desenvolvimento + implantação, com contingência | Premissas!D9 | Documento da equipe |
| 16 | R$ 300.000 | Pacote de módulos de integração (conectores do catálogo) | Premissas!D10 | Documento da equipe |
| 16 | R$ 6.900 | Hospedagem + domínio + n8n (teto da faixa R$ 2,8 a 6,9 mil) | Premissas!D14 | Documento da equipe |
| 16 | R$ 16.000 | Time de sustentação | Premissas!D15 | Documento da equipe |
| 16 | 6.000 pessoas | Colaboradores com acesso | Premissas!D18 | Documento da equipe |
| 16 | 25,0% | Fração que usa agentes ao fim da rampa | Premissas!D19 | Premissa a validar |
| 16 | 12 meses | Meses até atingir a adoção-alvo | Premissas!D20 | Premissa a validar |
| 16 | 1 exec/dia | Execuções de agente por usuário ativo por dia útil | Premissas!D21 | Premissa a validar |
| 16 | 22 dias | Dias úteis por mês | Premissas!D22 | Documento da equipe |
| 16 | 10 min | Tempo da tarefa feita à mão (média) | Premissas!D25 | Premissa a validar |
| 16 | 2 min | Tempo que a pessoa ainda gasta conferindo o resultado | Premissas!D26 | Premissa a validar |
| 16 | R$ 45,00 | Custo da hora de trabalho (salário + encargos, média) | Premissas!D27 | Premissa a validar |
| 16 | 50,0% | Fração do tempo liberado que vira ganho real | Premissas!D28 | Premissa a validar |
| 16 | R$ 0,030 | Custo de tokens por execução de agente | Premissas!D29 | Premissa a validar |
| 16 | 12,0% | Taxa de desconto (custo de capital) | Premissas!D33 | Premissa a validar |
| 16 | R$ 5,52 | Dólar usado no modelo (igual ao protótipo) | Premissas!D43 | Documento da equipe |

Os 5 indicadores aparecem no slide 12 com os nomes exatos dos critérios: Tempo de execução, Custo operacional, Produtividade, Taxa de erros e ROI.
