# Entregáveis F8 e F9

| Arquivo | O que é |
|---|---|
| `analise-financeira.xlsx` | **F8.** 13 abas com fórmulas vivas (Leia-me, Premissas, CAPEX, OPEX, Tokens, **Multimodelo (v7)**, Benefícios, Fluxo de caixa, Cenários, Sensibilidade, Construir × comprar, Resumo para slides, Motor). Fonte única de premissas na aba Premissas. |
| `apresentacao.pptx` | **F9.** 17 slides + 3 anexos (v7: 2 slides novos, 9 e 10), com notas do apresentador (texto falado e tempo). Gráficos nativos, números só da aba "Resumo para slides". |
| `checagem-numeros.md` | Cada número do deck → célula de origem no Excel (gerado junto com o deck). |
| `telas/` | Prints do protótipo (v6: personas, Roteiros, Perguntas e Plugins; v7: telas 14 a 19, extensão, vários provedores, balanceador, Mapa de IA e Finanças por provedor) seguindo o roteiro do LEIA-ME, depois de "Reiniciar a demo". |
| `gerador/` | Scripts que reproduzem tudo a partir das premissas. |

> **Versão dos entregáveis:** planilha, deck e `telas/` foram gerados na **v7** (18/11/2026) e não mostram o que veio na v8 (processos em blocos, alertas tratáveis, falcão). Os números continuam valendo: a calculadora e as premissas não mudaram até a 8.3.1 (payback no mês 21, VPL de R$ 773.842 e TIR de 57,4% conferidos com `projetar()` em 24/11/2026). Os prints atuais do produto ficam em [`docs/prints/`](../docs/prints/).

## Números principais (cenário base)

Payback no **mês 21**, VPL de **R$ 0,77 mi** (36 meses, 12% a.a.), TIR de **57% a.a.**: iguais aos da calculadora do protótipo.
Base medido: mês 17. Otimista: mês 11. **Conservador: não se paga em 36 meses.** Equilíbrio: adoção ≥ 15%.
Tokens são 1% a 4% do custo total; o roteador corta 70% do custo de tokens no mix de agentes da demo.

## Regerar

Pré-requisitos: Windows com Excel e PowerPoint (o recálculo usa o Excel via COM; não há LibreOffice nesta máquina), Python 3.11+, Node 18+.

```bash
cd entregaveis/gerador
uv venv .venv && uv pip install --python .venv/Scripts/python.exe openpyxl pydantic pywin32 selenium requests
npm install
.venv/Scripts/python.exe gerar_excel.py           # escreve o .xlsx (fórmulas)
.venv/Scripts/python.exe recalcular.py            # recalcula no Excel e falha se houver erro de fórmula
.venv/Scripts/python.exe testar_consistencia.py   # Excel × calculadora.projetar(), mês a mês, tolerância R$ 1
.venv/Scripts/python.exe capturar_telas.py        # opcional: app ligado em localhost:8765
.venv/Scripts/python.exe exportar_resumo.py       # aba Resumo -> resumo.json
node gerar_apresentacao.js                        # deck + checagem-numeros.md
```

## Decisões tomadas sem a equipe (as "decisões em aberto" do plano)

1. **Tempo:** deck para 10 a 12 min + 2 min de demo (15 slides na v6; 17 + 3 anexos desde a v7). Cortar os slides 2 e 4 se o tempo for menor.
2. **Demo:** ao vivo, com vídeo como reserva. **O vídeo não foi gravado.**
3. **Modelos reais:** sem chave. O cenário "Base medido" usa o tamanho dos passos e o roteador do código, e o histórico de 30 dias do protótipo é **sintético**, não medição.
4. **Construir × comprar:** Microsoft Copilot Studio, Zapier Agents e n8n Business, com preços públicos de 15/11/2026.
5. **Cenário de vitrine:** base com as premissas da equipe (mês 21); o base medido (mês 17) aparece como "o que o piloto confirma".
6. **Modelo de slides:** identidade do StoneFalcon (verde-pedra e rosa PinkFalcon), sem marca da Stone. Fonte Calibri, para abrir igual no PowerPoint e no Google Slides (Bricolage/Instrument não vêm instaladas).

## Achados que a equipe precisa saber

- **Tokens do documento:** recalculado com as premissas do próprio documento dá ≈ R$ 7,7 mil/mês. Os R$ 8,5 mil reaparecem convertendo pela cotação do **euro** (6,12): provável troca de moeda.
- **Câmbio:** o modelo usa R$ 5,52 (igual ao protótipo). A PTAX de 13/11/2026 foi R$ 5,6518; o efeito é pequeno porque tokens pesam 1% a 4%.
- **Construir × comprar não é vitória de custo no base:** com o volume do cenário base, Copilot Studio e Zapier saem R$ 0,24 a 0,28 mi mais baratos em 36 meses (não há desenvolvimento). Construir fica mais barato a partir de ~1,5× o volume do base, e o argumento principal é governança, dados e integração. O deck diz isso abertamente.
- **Economia do roteador:** o painel do protótipo mostra 79% (histórico sintético); a planilha calcula 70% pela estrutura dos agentes. O deck usa 70% e as notas do slide 12 explicam a diferença.
- **Limite do modelo:** como a calculadora, o fluxo põe o investimento no mês 0 e o benefício desde o mês 1; os 5 meses de construção atrasariam o payback.

## Falta fazer (pessoas)

- Nomes da equipe na capa.
- Revisão das premissas com a equipe (F8.6) e ensaio cronometrado (F9.6).
- Gravar o vídeo da demo (~2 min) seguindo as notas do slide 7.
- Conferir preços e câmbio na véspera e rodar de novo os geradores.
