# Plan: grouped side menu, demo alerts, shared processes and a more present falcon

Base: `main` of v8 (version 8.2.0). One ticket = one commit (or one PR per ticket). Closes as **8.3.0**.
Language note: this plan is written in English; UI copy, code identifiers and commit messages stay in Portuguese, as in the
rest of the repository.

## Context and findings (2026-11-22)

What was checked in the code and in the local database before writing the tickets.

### 1. Side menu (all profiles, mostly Helena)

- The menu is a flat list of 15 tabs. Which ones a persona sees comes from the back (`abas` of the persona, the single source
  of truth for access); the front only filters.
- Tab count per persona: **Helena 14**, **Lucas 11**, Marina / Rafael / Carla / Thiago **9** each.
- The side bar is fixed to the screen height and does not scroll, with the brand on top and the version note at the bottom.
  With 14 tabs on a laptop screen the last ones (Auditoria, Perguntas da Ferramenta) fall below the fold and **cannot be
  reached**. That is the bug Helena hits.
- Falcon return flights land on tabs by their `data-alvo` (`aba-execucoes`, `aba-agentes`, `aba-processos`,
  `aba-revisoes`). Once tabs live inside collapsible groups, a target can be hidden; the flight layer already accepts an
  `alternativo` target, which the grouped menu must use (fly to the group header).

### 2. Alerts look empty in all 6 profiles

- Demo alerts **do exist in code** (v8.1): each persona gets one alert opened by the real rules after the seed shapes the
  state those rules read (no alert is inserted directly). Tests cover it.
- The local database `backend/dados/stonefalcon.db` has **0 rows in `alerta`, ever**, and is missing the v8.1 demo processes
  (Lucas's "Triagem de incidente de sistema" and Helena's "Revisão mensal do custo de IA"). Budgets are the original values,
  not the 88% shaping.
- **Root cause:** the seed only runs on an **empty** database. This database was seeded by older code (before 8.1, or by an
  older copy started from a stale launch config), so the startup never seeds again and the alert scenarios never ran.
- **Contributing cause:** guided tours reset the platform **without** alerts on purpose (each tour has a step that shapes the
  persona's alert live). Anyone who entered through a tour and then browsed freely also sees nothing.
- Even when it works, each persona gets **one** open alert. There are no read alerts, nothing "in treatment" and no resolved
  history, so the Alerts page and the bell look thin.

### 3. Shared processes (a process that affects two areas)

- The domain supports it: a process has `compartilhado_com` (extra areas). People in a shared area can **see** and **execute**
  it; only the owner or creators of the owning area can edit.
- The seed has exactly **one** shared process: "Registro de incidente de sistema" (Thiago, Logística → shared with
  Engenharia, i.e. Lucas).
- Gaps found by reading the code (to be confirmed by ticket 05):
  - Alerts of a process go only to its **owner** (plus Engenharia for system alerts). The shared area never hears about a
    problem in a process it depends on.
  - The front never shows that a process is shared (no badge, no "shared by"), so the connection is invisible.
  - There is no UI to share a process; the API endpoint exists but nothing calls it.
  - It is unverified whether the shared process shows up in the other persona's Início, execution history and Mapa de IA.

### 4. The falcon

- v8.2 gave the falcon a body that appears only as feedback: hovering while something loads, one return flight after an
  action, empty states, and a short hop between steps in the tour bar.
- DESIGN.md §7.5 makes this a rule: the body appears **only after a person's action** and **at most one flight per action**.
  Asking for "random routines" **changes that rule**; ticket 08 rewrites §7.5 first so the new behaviour is a design decision,
  not a violation.
- Tour steps already carry `acao` (what to do) and `fala` (what the presenter can say), but no target element, so the falcon
  cannot point at where the person should click.

## Decisions taken in this plan

- **Menu groups** (by purpose; names are the Portuguese UI labels):

  | Group | Tabs |
  |---|---|
  | *(no group, always visible)* | Início |
  | Construir | Estúdio, Agentes, Processos, Plugins, Ferramentas |
  | Acompanhar | Execuções, Saúde, Revisões |
  | Gestão e valor | Painel executivo, Finanças, Mapa de IA, Auditoria |
  | Apresentação | Roteiros, Perguntas da Ferramenta |

  A group with no tab allowed for the persona is not rendered. A group with a single allowed tab renders as a plain link (no
  accordion for one item). Access still comes only from the back; the grouping is front-only presentation.
- **Accordion:** opening one group closes the others. The group holding the current route opens by itself on navigation
  (including tour steps and typed URLs). The open group is remembered per browser as a convenience only.
- **Alerts:** keep the v8.1 principle (alerts are opened, updated and closed by the real rules; never inserted directly).
  Fix the stale-database path with a **seed version stamp**, not by asking people to delete files.
- **Shared-process alerts** go to the owner **and** the creators of every shared area (they depend on it), in addition to
  today's recipients.
- **Falcon:** becomes a **companion**: a small perched presence near the brand, a speech bubble for short lines, a guide in
  tours and occasional ambient routines with a frequency cap. Reduced motion and a "silenciar o falcão" switch turn the
  ambient part off.

## Summary

| # | Ticket | Blocked by | Status |
|---|---|---|---|
| 01 | Grouped, collapsible side menu | — | feito |
| 02 | Seed version stamp: stale databases get the demo alerts | — | feito |
| 03 | Rich demo alerts: pending, read, in treatment and resolved | 02 | feito |
| 04 | Alerts on the Início of each persona | 03 | feito |
| 05 | Shared process: verified end to end and visible on both sides | — | feito |
| 06 | Shared-process alerts reach the shared area | 02, 05 | feito |
| 07 | Share a process from the UI | 05 | feito |
| 08 | Falcon companion: perch, speech bubble and the new motion rule | 01 | feito |
| 09 | Falcon as the guide of guided tours | 08 | feito |
| 10 | Falcon ambient routines | 08, 03 | feito |
| 11 | Docs, tours and version 8.3.0 | 01, 04, 06, 07, 09, 10 | ready-for-agent |

Initial frontier: **01**, **02** and **05** (independent). Three tracks: menu → falcon (01, 08, 09, 10), alerts (02, 03,
04) and shared processes (05, 06, 07); they meet at 10 (needs alerts), 06 (needs the stamp) and 11.

---

# 01: Grouped, collapsible side menu

**What to build:** every persona sees the side menu as Início plus the groups in the table above. Clicking a group header
expands it and collapses any other open group. The group of the current page opens by itself when the route changes (menu
click, tour step, typed address, falcon return). Helena can reach all 14 of her tabs on a 1366 × 768 screen without
scrolling the page. The menu also scrolls on its own if a very short window still does not fit, so no tab can ever be
unreachable. Falcon return flights whose tab is inside a collapsed group land on that group's header, which gets the same
short highlight a tab gets.

**Blocked by:** None (can start immediately).

**Status:** feito

- [x] Groups and their tabs follow the decision table; access still comes only from the persona's `abas` (no new access rule
      in the front).
- [x] Groups with no allowed tab are hidden; a group with one allowed tab is a plain link.
- [x] Opening a group closes the others (single open group); keyboard works (Enter/Space toggles, `aria-expanded`,
      `aria-controls`, visible focus).
- [x] The group holding the active route is open after any navigation, and the active tab keeps its current highlight.
- [x] At 1366 × 768, each of the 6 personas reaches every allowed tab; at 1280 × 600 the menu scrolls inside itself.
- [x] Return flights to a tab inside a collapsed group land on the group header (uses the existing `alternativo` target),
      for publish, execute, review and alert-action flights.
- [x] The remembered open group is per-viewer convenience only (wrapped in try/catch; the menu works without storage).
- [x] `npm run build` passes; checked in the browser for Helena, Lucas and Marina, light and dark where applicable.

---

# 02: Seed version stamp: stale databases get the demo alerts

**What to build:** starting the platform on a database seeded by older code brings it up to the current demo state, so all
6 personas see their alerts without anyone deleting files. The seed writes a **seed version** when it runs; on startup, a
database with no stamp or an older stamp is reset to the current initial state (the same reset the "Reiniciar
demonstração" action does), with a clear log line saying why. A database with the current stamp is left alone, so a demo in
progress is never wiped by a restart.

**Blocked by:** None (can start immediately).

**Status:** feito

- [x] The seed records a seed version (its own number, bumped whenever the demo catalog or the alert scenarios change; it is
      not the platform version).
- [x] Startup on a database without the stamp, or with an older one, resets to the current initial state and logs it once;
      `STONEFALCON_SEMEAR=0` still disables any seeding or reset.
- [x] Startup on a current database does not touch it (restart in the middle of a demo keeps everything).
- [x] Regression test using the v7 fixture database (or one built by the old seed): after startup, every persona has at
      least one open alert visible to them.
- [x] Test that alerts survive two rounds of the 60 s watcher (`avaliar` twice) without closing by themselves.
- [x] The current `backend/dados/stonefalcon.db` on this machine shows alerts for all 6 personas after one restart (checked
      in the browser).
- [x] `MODO_SIMULADO=1 pytest -q` green.

---

# 03: Rich demo alerts: pending, read, in treatment and resolved

**What to build:** each persona opens the Alerts page and the bell and finds a believable mix of problems and pending
items tied to their role: at least one open unread alert, one open alert already read, one being handled ("em tratamento")
with a note, and one resolved in the recent past. The bell count matches the unread ones. Everything is still produced by
the real rules: the seed shapes the state the rules read, runs them, and for history it shapes then un-shapes a condition so
the rule closes the alert itself. Read marks and "assumir" go through the same functions the page uses, so the audit trail
stays intact. Guided tours keep starting clean, as today.

**Blocked by:** 02 (the stamp must change so existing databases receive the new scenarios).

**Status:** feito

- [x] Per persona, after a fresh seed: ≥ 1 open unread, ≥ 1 open read, ≥ 1 in treatment (with note), ≥ 1 resolved; each tied
      to something that is theirs (their process, their systems, their budget). Suggested second scenarios:
      Marina — FAQ process budget near limit; Rafael — "listar chargebacks" slow; Carla — benefits process failing;
      Thiago — exchange process slow (resolved yesterday); Lucas — provider outage (resolved) and the shared incident process;
      Helena — sees all of the above plus a provider outage resolved last week.
- [x] No alert is inserted directly; tests assert each alert has its `alerta_aberto` (and, for resolved ones,
      `alerta_resolvido`) audit entry by the system.
- [x] No persona receives an alert unrelated to them (Helena excepted: she sees all by role).
- [x] The bell's unread count and the page filters (Abertos, Em tratamento, Todos) show the mix correctly for each persona.
- [x] Tours still reset without alerts and keep their "veja e trate o seu alerta" step working.
- [x] The seed version is bumped; `pytest -q` green; checked in the browser for all 6 personas.

---

**Notes (what was built):** a process that only reads files spends nothing on a model, so the budget rule cannot fire on it;
those processes use the "slow" and "failing" rules instead. Resolved alerts keep the real seed time (the audit trail is
chained and does not accept an invented time). The seed is slower (about 8 s instead of 2 s) because it runs the rules a few
extra times; `gasto_no_mes` now sums in the database to keep that down.

# 04: Alerts on the Início of each persona

**What to build:** the Início of each persona shows a short "Seus alertas" card with the open alerts (most severe first),
the count of unread ones and a link to the Alerts page, so the demo alerts are seen without hunting for the bell. Empty
state uses the falcon's existing empty-state pattern.

**Blocked by:** 03 (needs the richer alert mix to be meaningful).

**Status:** feito

- [x] Card lists up to 3 open alerts visible to the persona (same visibility rule as the Alerts page), critical first.
- [x] Clicking an alert opens it on the Alerts page; "Ver todos" goes to the page.
- [x] Opening the Início does not mark alerts as read.
- [x] Empty state shown when the persona has no open alert.
- [x] `npm run build` passes; checked in the browser for all 6 personas.

---

# 05: Shared process: verified end to end and visible on both sides

**What to build:** a process shared between two areas is visibly the same thing in both personas' interfaces. Using the
seeded "Registro de incidente de sistema" (Thiago → Engenharia/Lucas) as the reference case, verify and fix every place a
person would expect it: the Processos list, the process detail, the Início, executions (an execution by Lucas shows up in
Thiago's history for that process and vice versa), the audit trail and the Mapa de IA (an edge connecting the two areas).
Both sides show a "Compartilhado" badge: the owner sees "compartilhado com Engenharia", the other side sees "de Logística ·
Thiago". The other side can run it but not edit it. Write down what was broken and what was fixed in this ticket's notes.

**Blocked by:** None (can start immediately).

**Status:** feito

- [x] Back-end test: Lucas lists, opens and executes the shared process; Thiago sees Lucas's execution in the process history;
      Lucas cannot edit it (403); Marina (no shared area) cannot see it in her list or open it.
- [x] Both personas see the "Compartilhado" badge with the right direction in the list and in the detail.
- [x] The shared process appears in Lucas's Início wherever his own processes appear.
- [x] Mapa de IA draws the connection between Logística and Engenharia through the process (or the gap is fixed).
- [x] A short "Findings" list is added under this ticket in this file (what worked, what was fixed).
- [x] `pytest -q` and `npm run build` green; checked in the browser as Thiago and as Lucas.

---

**Findings (checked by reading the code and by running the reference case through the API):**

- Worked already: Lucas lists, opens and executes the shared process; Marina (no shared area) gets 403 on open and execute and
  does not see it in the list; Lucas cannot edit or re-share it (403); an execution by Lucas appears in Thiago's list and in the
  process history; the sharing is in the audit trail (`processo_compartilhado`).
- Fixed: Lucas's execution list (the one the Início shows) lacked Thiago's executions of the shared process, and he got 403 when
  opening one from the process history. Both sides now see and open the executions of a process shared with their area (Marina
  still does not).
- Fixed: nothing showed that a process is shared. The process list and detail now return `area_nome`, `dono_nome` and
  `compartilhado_nomes`, and the screens show the "Compartilhado" badge: the owner side reads "Compartilhado com Engenharia de
  Plataforma", the receiving side "Compartilhado · de Logística · Thiago".
- Fixed: the Mapa de IA drew only Thiago -> process. It now also draws the creators of the receiving area -> process, dotted
  (`compartilhado: true` on the link).
- Not changed (by design, other tickets): alerts of the shared process reach only the owner (ticket 06); the UI to share (07).
- Pre-existing, left alone: Lucas has the Pausar button on any process because he is a security reviewer.
- The Início of a persona has no process list; "wherever his own processes appear" is the recent executions, which now include the
  shared process's.

# 06: Shared-process alerts reach the shared area

**What to build:** when a shared process has a problem (failing, slow, budget, a system it uses down), the alert reaches the
owner **and** the creators of every area the process is shared with, and both can see and treat it. The demo gets one such
alert on "Registro de incidente de sistema", so Thiago and Lucas both see the same alert, and whoever "assumes" it is visible
to the other.

**Blocked by:** 02 (the demo alert must reach existing databases), 05 (the shared case must work first).

**Status:** feito

- [x] Recipients of a process alert = owner + creators of each shared area (+ Engenharia for system alerts, as today), no
      duplicates.
- [x] Changing the shared areas of a process updates the recipients of its open alerts on the next rule round.
- [x] Demo scenario: one open alert on the shared process, visible to Thiago and Lucas (and Helena by role), not to others.
- [x] Assuming the alert as Lucas shows "em tratamento por Lucas" to Thiago.
- [x] Tests for recipients and for the demo scenario; seed version bumped; `pytest -q` green.

---

**Notes (what was built):** the owner and the creators of each shared area now receive the alert (`destinatarios_do_processo`);
an open alert follows later changes of the shared areas on the next rule round and the audit trail records each change
(`alerta_destinatarios_alterados`). The demo opens one "falhando" alert on "Registro de incidente de sistema", unread by both
Thiago and Lucas so a presenter can assume it live. The unread counts in the bell become Thiago 2, Lucas 3 and Helena 7. Seed
version 3.

# 07: Share a process from the UI

**What to build:** the owner (or a creator of the owning area) can share a process with other areas from the process
detail, and stop sharing it, so a presenter can create a connection between two personas live during a demo. The change
goes to the audit trail, and the other area's persona sees the process right after switching profile.

**Blocked by:** 05.

**Status:** feito

- [x] "Compartilhar" control on the process detail, shown only to people who can edit; picks one or more areas other than
      the owner's.
- [x] Removing an area stops access for that area (list, detail, execute) immediately.
- [x] Audit entry "Compartilhado" with the areas, as today's API already records.
- [x] Switching to a persona of the newly shared area shows the process with the badge from ticket 05.
- [x] `npm run build` passes; checked in the browser (share as Marina with Risco, see it as Rafael, unshare).

---

**Notes (what was built):** `GET /areas` feeds the picker; the share call re-runs the alert rules right away, so open alerts reach
(or stop reaching) the other area at once, and rejects unknown areas (422). The process history shows which areas each
"Compartilhado" entry named. Sharing a process does not share the files it reads: Rafael running Marina's FAQ process gets an
escalation because `faq-atendimento.csv` belongs to Atendimento and Logística (the audit trail says so). For a live demo, pick a
process whose files the receiving area can read, or share the file too.

# 08: Falcon companion: perch, speech bubble and the new motion rule

**What to build:** the falcon is part of the interface, not only a feedback animation. It has a **perch** (a small idle
body next to the brand in the side menu) and a **speech bubble** it can show for a short line, anchored to wherever it
is. On login it lands on the perch and greets the persona by first name with one line about their day (e.g. how many open
alerts they have). DESIGN.md §7.5 is rewritten to allow a companion presence and ambient behaviour, with the limits that
tickets 09 and 10 follow; §7.6 (reduced motion) keeps the falcon still and drops ambient behaviour. A "silenciar o falcão"
switch in the persona menu hides the bubble and ambient behaviour (feedback flights stay).

**Blocked by:** 01 (the perch lives in the regrouped side menu).

**Status:** feito

- [x] Perched falcon visible beside the brand on every logged-in page, using the existing idle sprite; it leaves the perch
      for flights and comes back after them.
- [x] Speech bubble component: short text, auto-hides, dismissable, announced politely to screen readers, never covers
      the main action button.
- [x] Greeting on login (through the persona wheel) with the persona's first name and their open alert count.
- [x] DESIGN.md §7.5 rewritten with the new rule and its limits (frequency cap, never during typing or a modal, never
      during an action flight); §7.6 updated.
- [x] "Silenciar o falcão" switch, per-viewer, remembered as a convenience only (works without storage).
- [x] Reduced motion: perched still, no greeting flight, bubble without animation.
- [x] `npm run build` passes; checked in the browser, normal and reduced motion.

---

**Notes (what was built):** `Poleiro` (static sprite beside the brand, empty while a flight runs), `Balao` (polite live region,
auto-hide 5-10 s, paused on hover/focus, closes with × or Esc, picks another side if it would cover an `acao-*` button, closes on
page change), and `falar` / `calar` / `silenciado` / `emVoo` in `useFalcao()`. The greeting flies to the perch (`sobre: true`)
and then speaks; with reduced motion it only speaks. DESIGN.md section 8 now defines four roles (perch, return, guide, ambient)
with the limits tickets 09 and 10 follow. The switch lives in the persona menu and is stored per browser.

# 09: Falcon as the guide of guided tours

**What to build:** in every guided tour, each step is led by the falcon: when a step starts, it flies to the element the
person must use next and shows the step's action in its bubble; the "Fala" toggle still shows the presenter line in the
bar. When a step is completed (the person did the action), it flies back to the tour bar and hops to the next segment, as
today. Steps that open outside the app tell it in the bubble. Tour steps gain an optional **target** (the `data-alvo` of the
element to point at); without one, the falcon stays on the perch and only speaks.

**Blocked by:** 08.

**Status:** feito

- [x] Tour step definitions accept an optional target; all six persona tours have targets on the steps that have a clear
      control (execute, publish, open alert, treat alert, etc.).
- [x] Back-end test: every declared target is a known `data-alvo` name (a list kept next to the tour catalog), so tours do
      not point at nothing after a UI change.
- [x] On each step the falcon flies to the target (or the group header from ticket 01 when the tab is collapsed) and shows
      the action text; if the target is not on screen, it speaks from the perch.
- [x] "Voltar", "Avançar" and "Reiniciar" never leave the falcon stuck mid-flight or pointing at the previous step.
- [x] Reduced motion: appears still beside the target with the bubble.
- [x] `pytest -q` and `npm run build` green; one full tour (Helena) and one short one (Marina) checked in the browser.

---

**Notes (what was built):** `Passo.alvo` and `ALVOS_CONHECIDOS` live in `roteiros/catalogo.py`; a test checks every declared
target is in the list and that each name still appears next to a `data-alvo` in the screens. New targets: `acao-montar`,
`acao-aprovar`, `acao-pausar`, `acao-simular-falha`, `acao-integrar` (plus the existing `acao-executar`, `acao-publicar`,
`acao-alerta`). The guide is `roteiro/Guia.tsx`: it waits (up to 5 s) for the control and for the bar's short hop to end, scrolls
the control into view if it is below the fold or behind the bar, flies from the perch, highlights the control and speaks the
step's action; without a target, or with the control missing, it speaks from the perch; an external step says "(abre em outra
aba)". Changing step cancels the guide's own flight and closes the previous bubble. Silenced, the falcon still points, it only
does not speak (the action stays in the bar). The pitch roteiro has no targets yet. The bubble now avoids other controls too.

# 10: Falcon ambient routines

**What to build:** the falcon behaves like a resident of the platform, with a small set of routines that happen on their
own, each tied to something real in the persona's state, so it is never noise:

- **New alert:** when the unread count goes up, it flies from the perch to the bell and back, with a one-line bubble.
- **Idle tip:** after about a minute without interaction, it says one contextual tip for the current page (from a short
  list per page).
- **Stretch / look around:** rare idle animation on the perch (no flight), so it feels alive.
- **First run of the day:** after the persona's first successful execution of the day, a short celebration bubble.
- **Empty states:** where the empty-state falcon already appears, its bubble suggests the next step.

All routines share one scheduler with a frequency cap (at most one ambient behaviour every few minutes), pause while the
person is typing, a modal or dialog is open, an action flight is running or a tour is active (tours belong to ticket 09),
and are off with reduced motion or with the falcon silenced.

**Blocked by:** 08 (perch, bubble, switch), 03 (the "new alert" routine needs alerts that actually appear).

**Status:** feito

- [x] One scheduler for all ambient routines with a configurable cap; no two ambient behaviours within the cap window.
- [x] Each routine above triggers only on its real condition and can be turned on in a test page for review (extend the
      existing falcon test page).
- [x] Paused during typing, open dialogs, action flights and active tours; off with reduced motion and when silenced.
- [x] Tips and bubble lines are short, in Portuguese, and follow the UX writing in DESIGN.md.
- [x] No ambient routine moves focus, blocks a click or covers the main action button.
- [x] `npm run build` passes; checked in the browser for 10 minutes of normal use as Helena without excessive appearances.

---

**Notes (what was built):** one scheduler in `ProvedorFalcao` (cap 3 min, tick 4 s, priority order alert > first run > empty
state > tip > stretch) fed by `components/falcao/Ambiente.tsx`. Checked in the browser as Helena for 10 minutes of idle plus two
page changes: 3 appearances (a tip at 54 s, a stretch at 242 s, a tip for Alertas at 423 s, the second one waiting out the cap).
The first run showed that a new-alert notice arriving inside a cap window was dropped, so alerts now wait up to the cap plus 30 s;
with the cap lowered from the console, a real new alert (a system set to "down" by Lucas) made the falcon fly to the bell and
say "Chegaram 3 alertas novos." The local test page (`frontend/falcao-teste.html`, kept out of Git by `.git/info/exclude`) was extended with the perch, the bubble and a button per routine, but that change is not part of the commit; in the app `window.__ambiente.capMs` lowers the cap from the console.
Not exercised for real: the "first run of the day" routine (only in the test page) and reduced motion for the ambient part (the
scheduler returns early; checked by reading the code).

# 11: Docs, tours and version 8.3.0

**What to build:** documentation and the release match what was built: DESIGN.md (menu groups, companion falcon and
§7.5/§7.6), ARCHITECTURE.md (seed version stamp, shared-process alert recipients), REQUIREMENTS.md (shared process
visibility, alert recipients), AGENTS.md (link to this plan), LEIA-ME.md where it describes the menu or alerts, the tour
texts that mention where tabs are, and the version bumped to 8.3.0 everywhere the version check reads.

**Blocked by:** 01, 04, 06, 07, 09, 10.

**Status:** ready-for-agent

- [ ] Docs updated as listed; this plan's statuses set to "feito" (or "parcial" with the reason).
- [ ] Tour texts and `fala` lines that refer to menu positions match the grouped menu.
- [ ] Version 8.3.0 in the single source and the copies; `python scripts/verifica_versao.py` passes.
- [ ] Full CI set green: `pytest -q`, `npm run build`, `verifica_extensao.py`, `verifica_versao.py`.
