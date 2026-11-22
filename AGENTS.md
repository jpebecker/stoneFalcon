# AGENTS.md — guia para agentes de código e pessoas novas

Como trabalhar neste repositório sem ler a história das versões. Comece pelos três documentos abaixo; este arquivo diz **como ligar, testar e entregar**.

| Documento | Para quê |
|---|---|
| [ARCHITECTURE.md](ARCHITECTURE.md) | Como o StoneFalcon é montado: back, front, extensão, fluxo de execução, acesso, modo simulado. |
| [REQUIREMENTS.md](REQUIREMENTS.md) | O que a plataforma precisa fazer e respeitar: personas, matriz de acesso, requisitos, critérios de todo ticket. |
| [DESIGN.md](DESIGN.md) | Linguagem visual: cores, tipografia, componentes, a roda de personas, acessibilidade e movimento. |

Outros: [LEIA-ME.md](LEIA-ME.md) (visão do produto e uso), [PLAN-V8.md](PLAN-V8.md) (plano entregue da v8), `docs/` (planos de trabalho).

> Protótipo acadêmico (UFSC) para o desafio StoneLab. Não é um produto da Stone. Pessoas, áreas e dados são fictícios.

## 1. Mapa do repositório

```
backend/    API FastAPI, runtime de agentes e processos, plugins, auditoria  (Python 3.11+)
frontend/   telas em React + Vite + Tailwind + TypeScript
extensao/   copiloto para Chrome/Edge (Manifest V3, sem lógica de IA)
scripts/    verificações da CI e ajudantes de iniciar.bat / iniciar.sh
docs/       planos de trabalho (um .md por plano; tickets dentro dele)
.github/    esteira de CI
```

## 2. Ligar

- **Uso normal:** `iniciar.bat` (Windows) ou `sh iniciar.sh` (Mac/Linux). Compila as telas, prepara o `.venv` do back e abre `http://localhost:8765`. Variáveis: `STONEFALCON_PORTA`, `STONEFALCON_SEM_NAVEGADOR=1`, `STONEFALCON_SEM_PAUSA=1` (Windows).
- **Desenvolvimento**, em dois terminais:

```bash
cd backend && uv run uvicorn app.main:app --reload --port 8765
```

```bash
cd frontend && npm install && npm run dev
```

O front (porta 5173) repassa `/api`, `/demo` e `/avatares` ao back; se o back estiver em outra porta, defina `STONEFALCON_API` (ex.: `http://127.0.0.1:8769`) antes de `npm run dev`. Sem `uv`, use um ambiente virtual com `pip install -r backend/requirements.txt` e `python -m uvicorn --app-dir backend app.main:app --port 8765`.
- **Um processo só:** não use `--workers`. A trava da auditoria e o cache dos plugins vivem na memória.
- **Modo simulado por padrão:** sem `ANTHROPIC_API_KEY` tudo roda sem chave, custo ou internet. Para modelos reais, copie `backend/.env.exemplo` para `backend/.env`. Para um banco descartável: `STONEFALCON_DB=sqlite:///caminho/teste.db`; para não semear, `STONEFALCON_SEMEAR=0`; para desligar tarefas de fundo, `STONEFALCON_VIGIA=0` e `STONEFALCON_AGENDADOR=0`.

## 3. Testar e verificar

Rode as mesmas checagens da CI, na raiz do repositório. Aqui o back usa `uv` por comodidade; a CI instala com `pip` (`python -m pip install -r backend/requirements.txt pytest httpx`) e roda `python -m pytest -q` dentro de `backend/` com `MODO_SIMULADO=1`. Os testes são os mesmos.

```bash
cd backend && MODO_SIMULADO=1 uv run pytest -q
```

```bash
cd frontend && npm run build
```

```bash
python scripts/verifica_extensao.py
```

```bash
python scripts/verifica_versao.py
```

```bash
python scripts/fumaca_iniciar.py
```

- **Back:** `pytest` em `backend/tests`, em modo simulado, sem chave nem internet (`conftest.py` já força isso). Todo comportamento novo do back ganha teste.
- **Front:** não há testes automatizados. Os critérios de tela se cumprem com `npm run build` (checagem de tipos + compilação) **mais** verificação no navegador: suba back e front, exercite os estados da tela (inclusive repouso, ativo e foco quando houver) e junte uma captura de tela ao PR.
- **Extensão:** `scripts/verifica_extensao.py` confere o manifesto e os arquivos citados.
- **Versão:** a fonte única é `backend/app/core/versao.py`; `manifest.json`, `pyproject.toml` e `package.json` repetem o número e `scripts/verifica_versao.py` falha se divergirem. Mudar a versão só quando o plano pedir.
- **Início:** `scripts/fumaca_iniciar.py` sobe `iniciar.sh` (Ubuntu) ou `iniciar.bat` (Windows) e confere `/api/v1/saude`. É o mais lento; rode ao mexer nos scripts de início.

## 4. Fluxo de entrega

1. Um **ticket = um branch = um PR** a partir de `main`. Nome do branch: `v8/NN-nome-curto` ou o prefixo do plano em andamento.
2. O PR leva o número do ticket no título e os critérios de aceite como lista marcável. Marque as caixas no plano em `docs/` à medida que cumpre.
3. A **esteira de CI** (`.github/workflows/ci.yml`) roda em todo PR e em `main`, e precisa estar verde para juntar:

| Job | O que confere |
|---|---|
| `back` | `pytest` em Python 3.11 e 3.14, modo simulado. |
| `front` | `npm ci` e `npm run build` (tipos e compilação), Node 22. |
| `extensao` | Manifesto válido e arquivos citados existem. |
| `versao` | Extensão, API e front contam o mesmo número. |
| `iniciar` | Scripts de início sobem a plataforma no Ubuntu e no Windows. |

4. Commits em português, no imperativo ou descritivo curto, com o número do ticket quando houver (`feat(front): …`, `docs: …`).
5. Fins de linha: `.gitattributes` mantém `*.bat` em CRLF e `*.sh` em LF; não normalize à mão.

## 5. Convenções e proibições

**Faça**

- Interface e documentação em **português do Brasil**, linguagem simples.
- **Dados fictícios**: pessoas, áreas, lojistas, políticas e sistemas. Nada apresentado como produto oficial da Stone, sem logotipo ou marca de terceiros.
- **Acesso decidido pelo back.** Papéis, nível e abas moram em `backend/app/core/identidade.py`. O front só lê `pessoa.abas`; a API confere de novo (`exigir`, `exigir_aba`).
- Ferramentas sempre pelo executor governado (`app/tools/executor.py`); dados pessoais mascarados antes de qualquer modelo e antes da auditoria; evento relevante vai para a trilha (`app/audit`).
- Tudo funciona em **modo simulado**; o que não roda de verdade leva o selo “simulado”.
- Siga os tokens e componentes de [DESIGN.md](DESIGN.md) (`.caixa`, `.botao-pedra`, `.selo`, cores por classe do Tailwind) e trate acessibilidade e movimento reduzido em toda tela nova.

**Não faça**

- **Nada de chave no código**, na extensão ou no Git. `backend/.env` está no `.gitignore`; use só `.env.exemplo` como modelo.
- Não calcule permissão no front, nem duplique a lista de abas.
- Não grave dado real ou pessoal; os dados de demonstração são inventados.
- Não use `--workers` no back nem tarefas que dependam de vários processos.
- Não rode “Reiniciar a demo” contra um banco que importa: **apaga o banco, inclusive a trilha de auditoria**.
- Não mude a versão, o contrato da API ou a matriz de acesso sem o ticket pedir; atualize os documentos ([REQUIREMENTS.md](REQUIREMENTS.md), [ARCHITECTURE.md](ARCHITECTURE.md)) quando mudar.
- Não pule a CI nem os hooks.

## 6. Dicas de trabalho

- Procure a regra no módulo certo (tabela em [ARCHITECTURE.md](ARCHITECTURE.md)) antes de criar outra; as rotas em `backend/app/api` só orquestram.
- Para ver uma tela com dados, o back semeia a demonstração na primeira subida (agentes, processos, arquivos e histórico sintético); os seis perfis aparecem na tela de entrada.
- Dependências do back ficam em `backend/requirements.txt` (a CI e `iniciar.*` leem esse arquivo) e `backend/pyproject.toml`; do front, em `frontend/package.json` e `package-lock.json`.
