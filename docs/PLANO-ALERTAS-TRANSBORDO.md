# Plan: demo alerts that survive tours, and text that never overflows its card

Base: `main` of v8 (version 8.3.0). One ticket = one commit (or one PR per ticket). Closes as **8.3.1**.
Language note: this plan is written in English. UI copy, code identifiers and commit messages stay in Portuguese, like the
rest of the repository.

## Context and findings (2026-11-23)

What was checked in the code, in the local database and in the browser before writing the tickets. The browser sweep ran on
a throwaway database (fresh seed) with all 6 personas and every tab, plus the detail pages of agents, processes, plugins and
executions (including one waiting for confirmation and one escalated). It ran at 1280 px, 1100 px and 1024 px wide.

### 1. The bell is empty in all 6 personas

- The demo alert code works. A fresh seed (seed version 3) leaves these unread counts in the bell: **Marina 1, Rafael 1,
  Carla 1, Thiago 2, Lucas 3, Helena 7**. Each persona also has an alert already read, one being handled ("em tratamento")
  and a resolved one.
- The local database `backend/dados/stonefalcon.db` has **0 rows in `alerta`** but carries the **current** seed stamp (3).
- **Root cause:** the audit trail shows the database was reset at 22:58:56 by a **guided tour** (Marina's: the Estúdio
  suggestion and agent creation that follow are hers). Tours reset with `alertas=False` on purpose, because each tour shapes
  its persona's alert live in the step "veja e trate o seu alerta". But the seed still writes the current stamp. On the next
  `iniciar.bat`, startup sees an up-to-date stamp and keeps the database ("mantido"), so the alerts never come back. The
  v8.3 stamp (ticket 02 of PLANO-MENU-ALERTAS-FALCAO) fixed databases seeded by **old code**. It does not cover a
  database that the **current** code seeded without alerts.
- **Why the README prints show alerts:** they were captured by the `readme-prints` launch config, which points
  `STONEFALCON_DB` at a separate, freshly seeded database. The everyday `iniciar.bat` uses `backend/dados/stonefalcon.db`.
- `iniciar.bat` itself is fine at building and launching. What it lacks: it does not say what startup did to the demo
  (kept, seeded or rebuilt), it has no way to ask for a clean demo, and the startup smoke test only checks that
  `/api/v1/saude` answers, not that the demo has alerts.

### 2. Visual bug in "Execuções" (README step 4, print 07-execucao)

- On an execution waiting for confirmation, the box "O agente quer: …" shows the action's input as preformatted JSON with
  **no wrapping and no scroll**. A long value (the `motivo` of "Reter repasses do lojista") runs past the card. The page
  grows to **3008 px wide** and scrolls sideways at 1280 px and at 1024 px.
- The box belongs to the shared execution timeline, so the same bug shows on **every page that shows a timeline**:
  Execuções (detail), the Estúdio test run, the Agente page and the Processo page and editor. It hits every persona who
  can see that execution. Seeded, that is Rafael (who triggers it) and Helena (who sees everything).
- The header line "Disparada por … · entrada {…}" prints the input JSON inline. It wraps at spaces today, but a long
  value with no spaces would overflow in the same way.

### 3. Similar errors found by the sweep

- **Execution step rows:** the step title shares one line with its details (block type, agent, model, "simulado" badge,
  cost) and has no minimum width. "Avaliar o risco do caso" gets squeezed to one word per line (visible in print 07 too,
  and worse at 1100 px).
- **Ferramentas (catálogo):** each card's header keeps its badges (plugin, classification, action) on one line that cannot
  shrink. For plugin tools ("Listar arquivos (Arquivos e Planilhas)") the badges go past the card edge, the title wraps
  one word per line and the page scrolls sideways. Seen in all 6 personas at 1100 px.
- Nothing else overflowed: Início, Alertas, Saúde, Revisões, Auditoria (its JSON already scrolls inside its box), Finanças,
  Painel, Processos, Plugins and the rest came out clean. The react-flow connection handles that stick out of process
  nodes are by design.

## Decisions taken in this plan

- **Tour resets are not a demo state to keep across restarts.** The seed stamp also records **how** the database was
  seeded: the full demo or a guided tour. Startup rebuilds the full demo (with alerts) when the last reset came from a
  tour, the same way it does for an old stamp. Accepted trade-off: restarting the server in the middle of a tour loses
  that tour's state. That is rare, and the tour can be restarted from Roteiros.
- **At least 2 unread alerts per persona** after a fresh demo, still produced by the real rules (never inserted directly).
  The read, in-treatment and resolved mix stays as it is.
- **Overflow rule:** long dynamic text (JSON, reasons, names, inputs) wraps or scrolls inside its own box. A title next to
  badges or metadata keeps a minimum width, and the badges or metadata wrap under it instead of squeezing it. This goes
  into DESIGN.md so new screens follow it.

## Summary

| # | Ticket | Blocked by | Status |
|---|---|---|---|
| 01 | Pending-action input wraps inside its card | — | parcial (Estúdio / Agente / Processo pages not opened) |
| 02 | Titles are never squeezed by metadata or badges | — | feito |
| 03 | Seed stamp knows a tour reset; `iniciar.bat` brings the alerts back | — | feito |
| 04 | At least 2 unread alerts per persona | 03 | feito |
| 05 | Overflow rule in DESIGN.md, README prints and version 8.3.1 | 01, 02, 04 | feito |

Initial frontier: **01**, **02** and **03** (independent). Two tracks: visual (01, 02) and alerts (03 → 04). They meet at 05.

---

# 01: Pending-action input wraps inside its card

**What to build:** a person opening an execution that waits for their confirmation sees the whole action input ("O agente
quer: Reter repasses do lojista") inside the yellow box. Long values wrap within the box, and a very tall input scrolls
inside it. The page never scrolls sideways. The same holds everywhere the execution timeline appears (Execuções detail,
Estúdio test run, Agente page, Processo page and editor), so every persona who can see a pending execution gets the fix.
The "entrada" line under the execution title also wraps long values.

**Blocked by:** None (can start immediately).

**Status:** parcial (the pending box was checked on Execuções only; same `LinhaDoTempo` component elsewhere)

- [x] With Rafael's "Triagem de chargebacks" run on lojista L1003 (pending "Reter repasses do lojista"), the input JSON stays
      inside the box at 1280 px and 1024 px, and the page has no horizontal scroll (document width = viewport width).
- [x] The same execution opened as Helena shows the same result (she can't confirm, but she sees the box).
- [ ] The pending box looks right on the Estúdio test run and on the Agente / Processo pages when a run stops for
      confirmation there. (Same `LinhaDoTempo` component; checked on Execuções only, not opened on those pages.)
- [x] The "Disparada por … · entrada {…}" line wraps an input with a long unbroken value without widening the page.
- [x] JSON stays readable (indentation kept). Wrapping does not hide any part of the value.
- [x] `npm run build` passes. Before/after screenshots attached.

---

# 02: Titles are never squeezed by metadata or badges

**What to build:** on the execution timeline, each step shows its title on as few lines as the width allows, and the
details (block type, agent, model, "simulado", cost, duration) move under the title when there is no room. On
Ferramentas, each tool card keeps its title readable and its badges (plugin, classification, action) wrap inside the card
instead of going past its edge. No page scrolls sideways at 1024 px or wider.

**Blocked by:** None (can start immediately).

**Status:** feito

- [x] "Avaliar o risco do caso" (Triagem de chargebacks) shows its title on a single line at 1280 px and at most two at
      1024 px. The details stay readable and aligned.
- [x] On Ferramentas, the plugin tools ("Listar arquivos (Arquivos e Planilhas)" and the rest) keep their badges inside
      the card at 1100 px and 1024 px, and the page has no horizontal scroll, for all 6 personas.
- [x] The step row stays a single button with the same click behaviour (expand/collapse) and keyboard focus ring.
- [x] The same check across the other badge-plus-title headers (Agentes, Processos, Plugins, Alertas, Revisões) finds no
      new overflow.
- [x] `npm run build` passes. Before/after screenshots attached.

---

# 03: Seed stamp knows a tour reset; `iniciar.bat` brings the alerts back

**What to build:** someone who ran a guided tour, closed the platform and starts it again with `iniciar.bat` lands on the
full demo, with alerts in the bell of every persona, without deleting any file. The seed stamp records how the database
was seeded (full demo or guided tour). Startup treats a tour-seeded database like an old one and rebuilds the full demo,
with a clear log line saying why. A database seeded as the full demo with the current stamp is still kept untouched, so a
restart in the middle of a free demo loses nothing. `iniciar.bat` (and `iniciar.sh`) print what startup did to the demo
(kept, seeded or rebuilt) and accept an optional variable to force a clean full demo. The startup smoke test checks that
the started platform has demo alerts.

**Blocked by:** None (can start immediately).

**Status:** feito

- [x] The stamp stores the seed version **and** how the database was seeded (full demo or tour id). Reading it still works
      on databases stamped before this change; they count as the full demo.
- [x] Startup on a tour-seeded database rebuilds the full demo and logs it once. Every persona then has unread alerts.
- [x] Startup on a full-demo database with the current stamp does not touch it. `STONEFALCON_SEMEAR=0` still disables any
      seeding or rebuild.
- [x] `iniciar.bat` / `iniciar.sh` show in plain Portuguese whether the demo was kept, seeded or rebuilt. A documented
      variable (e.g. `STONEFALCON_DEMO_NOVA=1`) forces a clean full demo, with a warning that it erases the database and
      its audit trail.
- [x] Regression test: reset through a tour, then run startup again. The database becomes the full demo and each persona
      has at least one unread alert.
- [x] `scripts/fumaca_iniciar.py` also checks that `/api/v1/notificacoes/contagem` has unread alerts for at least one persona.
- [x] On this machine, `backend/dados/stonefalcon.db` (today: 0 alerts, tour-seeded) shows alerts in the bell for all 6
      personas after one run of `iniciar.bat` (checked in the browser).
- [x] `MODO_SIMULADO=1 pytest -q` green. AGENTS.md / ARCHITECTURE.md describe the new stamp rule and the variable.

---

# 04: At least 2 unread alerts per persona

**What to build:** after a fresh demo, every persona opens the platform and sees **at least 2** in the bell, with alerts
tied to their own processes, systems or budget. Today Marina, Rafael and Carla have only 1. Each gets one more open
alert that they have not read yet, produced by the real rules (the seed shapes the state those rules read and runs them).
Thiago, Lucas and Helena keep at least what they have. The read, in-treatment and resolved mix stays. The seed version is
bumped, so any existing database receives the new scenarios on its next start.

**Blocked by:** 03 (the stamp change and the version bump must land in order so existing databases are rebuilt once, with
the new scenarios).

**Status:** feito

- [x] Per persona after a fresh seed: ≥ 2 unread open alerts, ≥ 1 read, ≥ 1 in treatment (with note), ≥ 1 resolved. Each
      new alert belongs to the persona (their process, systems or budget). Helena still sees all of them by role.
- [x] Suggested new scenarios (to confirm while building): Marina — a system her FAQ flow uses slow or out; Rafael — a
      second sign on the chargeback side (for example "consultar lojista" slow); Carla — the vacation process failing.
      Each must avoid clashing with the scenario already shaped for the same process.
- [x] No alert is inserted directly. Tests assert each new alert has its `alerta_aberto` audit entry by the system and
      survives two rounds of the 60 s watcher.
- [x] The bell count, the Início "Seus alertas" card and the Alertas filters (Abertos, Em tratamento, Todos) show the mix
      correctly for each persona.
- [x] Guided tours still start clean and their "veja e trate o seu alerta" step still works.
- [x] Seed version bumped (3 → 4). Seed time stays reasonable (before/after not timed). `pytest -q` green. Checked in the browser
      for all 6 personas.

---

# 05: Overflow rule in DESIGN.md, README prints and version 8.3.1

**What to build:** the docs and the README match what was fixed. DESIGN.md gains the overflow rule (long dynamic text
wraps or scrolls inside its box, titles keep a minimum width next to badges and metadata, no page scrolls sideways at
1024 px or wider). The README prints affected by this plan are captured again from a fresh demo: 07-execucao (no
overflow), 09-alertas, and 02-inicio if the alert card changed. LEIA-ME.md and README mention the `iniciar` option to
force a clean demo. The version goes to 8.3.1.

**Blocked by:** 01, 02, 04.

**Status:** feito

- [x] DESIGN.md has the overflow rule with a short do/don't.
- [x] Prints 07-execucao and 09-alertas (and 02-inicio if needed) re-captured. Print 07 shows the pending input wrapped
      inside its box.
- [x] README / LEIA-ME.md explain what happens to the demo when a tour was run and how to force a clean demo.
- [x] AGENTS.md links this plan. This plan's statuses set to "feito" (or "parcial" with the reason).
- [x] Version 8.3.1 in the single source and its copies. `python scripts/verifica_versao.py` passes.
- [x] Full CI set green: `npm run build`, `verifica_extensao.py`, `verifica_versao.py` and `fumaca_iniciar.py` pass. `pytest -q`: 806 passed
      after fixing the 2 date-dependent failures in the demo history (see Notes).


---

# Notes (what was built, 8.3.1)

- **01/02:** `LinhaDoTempo.tsx` (pending `<pre>` wraps and scrolls inside its box; step row is `flex-wrap` with a 16 rem minimum title),
  `ExecucaoDetalhe.tsx` (entrada line wraps), `Catalogo.tsx` (badges wrap under the title). Measured at 1024, 1100 and 1280 px for all 6
  personas on 11 routes (198 checks): no sideways scroll, no badge past its card, no step title over 2 lines.
- **03:** `selo_semente.origem` ("demo" or the roteiro id; old rows count as "demo"). `partida.preparar` rebuilds a roteiro-seeded database and
  `STONEFALCON_DEMO_NOVA=1` forces a clean demo. `main.py` prints a "Demo: ..." line, which `iniciar.bat` / `iniciar.sh` point to
  (the scripts themselves only warn when the variable is on; the line comes from the server). On this machine the real database was
  backed up to `backend/dados/stonefalcon.db.bak-antes-8.3.1` and rebuilt by `iniciar.bat`: bell counts Marina 3, Rafael 3, Carla 2,
  Thiago 2, Lucas 3, Helena 7.
- **04 (deviation from the suggested scenarios):** instead of a failing vacation process for Carla (it would move the cost ratio of her budget
  alert), two slow systems were shaped: "Consultar cadastro do lojista" and "Buscar política interna". The rule opens one alert per
  dependent process, so Marina, Rafael and Carla each get one more unread alert about their own process; Lucas, Thiago and Helena
  already have them marked as read. More alerts than 6 open (8 in total) because other processes use the same systems.
- **CI fix (date-dependent tests):** `seed/historico.py` drew durations from 2.5–9 s, so on some dates plain noise crossed the
  "2x the median" slowness rule (a false "Revisão mensal do custo de IA está mais lento" alert). The range is now 4–7.5 s
  (ratio < 2). A run escalated before the agent step was also charged 40% of a full run that no step carried, so the
  process cost more than its agent whenever the bad days fell inside the month; it now carries only the steps that ran.
