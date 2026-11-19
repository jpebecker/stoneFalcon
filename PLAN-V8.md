# StoneFalcon v8 — Ticket plan

> **Approved for execution** (18/11/2026). Starts from the state delivered in v7. Every ticket is a vertical slice: back end, front end, extension and tests together, demoable on its own, delivered as one PR with the CI pipeline green. This file is the single source for the run: execute the tickets in the order of section 5 and tick the boxes here as you go.

## 1. What changes and why

v7 gave the platform a live AI Map, multiple model providers and scheduled tasks. v8 answers four requests from the team:

1. **Radial persona selector on the home screen.** The "Quem é você hoje?" login screen becomes a ring split into 6 slices, one per persona, each showing the persona's photo. Hovering (or focusing) a slice expands it with an animation and reveals that person's details (name, role, area, what they do, access level).
2. **A Processes tab, separate from Agents.** Today the Agents tab mixes two things: an "agent" is a whole multi-step flow, so it is not clear which persona process an agent belongs to. v8 splits them: an **agent** is a single reusable AI worker; a **process** is a low-code block flow (agents + plugins + data + approvals) mapped to a persona's real process.
3. **A plugin that really works for every persona.** All 9 marketplace plugins are simulated today. v8 adds **Files & Sheets**: upload a CSV/XLSX to the platform, and agents and processes read and write it for real, offline, for all six personas.
4. **"Create your plugin".** A conceptual feature in the Plugins tab: someone names an existing market tool, pastes its public feature description, and the platform drafts an internal company plugin that does the same job ("reverse-engineered" from public features). It is access controlled: an AI analyst must approve it before it exists.

### Feasibility verdicts

| Request | Verdict | Why |
|---|---|---|
| Radial persona selector | **Feasible, low risk** | Exactly 6 personas, and each already exposes photo, initials, color, role, area, description, roles and access level. Built with SVG + CSS transitions; no new front-end dependency. |
| Processes tab | **Feasible, largest change** | The runtime already executes step graphs (parallel layers, approvals, resume) and the Studio already uses React Flow. The risk is the wide blast radius of changing what "agent" means, so it is sequenced as **expand → migrate → contract** (tickets 03–09). |
| Real plugin for all personas | **Feasible** | Fits the existing plugin/tool contract (permissions, guardrails, audit). Needs one new back-end dependency (`openpyxl`, for XLSX); the start scripts already reinstall when requirements change. |
| Create your plugin | **Feasible as a concept** | Reuses the plugin request/approval queue from v6. Generated tools are simulated. Guardrails: only public feature descriptions pasted by the user, no scraping, no logos/trademarks, generic names. |

## 2. Decisions (confirmed)

| # | Decision | Choice |
|---|---|---|
| 1 | Agent vs. process | **Agents are workers.** An agent = one reusable AI worker (instructions, allowed tools, model, input fields, limits). A process = a versioned low-code flow of blocks (trigger/inputs, data source, agent, plugin tool, approval, condition, notify/output), owned by a persona and an area and linked to that persona's AS IS → TO BE process. The seeded multi-step agents migrate into processes. |
| 2 | Real plugin | **Files & Sheets**: CSV/XLSX uploaded to the platform, per area, with a data classification chosen at upload. Works offline and in simulated mode. Badge "real", not "simulado". |
| 3 | Who approves "Create your plugin" | **New role "AI analyst", given to Helena (CoE de IA).** Helena approves the concept. If the proposed plugin touches confidential or restricted data, **Lucas (security) must also approve** (four eyes). Nobody approves their own request. The persona count stays at 6. |
| 4 | What an approved request produces | **A usable simulated internal plugin**: it appears in the marketplace with the badge "internal · conceptual", its proposed tools are backed by generic simulated implementations, and it can be integrated and used as a block in a process. |
| 5 | Where the wheel lives | **The login screen** ("Quem é você hoje?"), replacing the card grid on desktop. The card grid stays as the narrow-screen and no-motion fallback. |
| 6 | Naming in the UI | The wheel is a "radial persona selector". It is inspired by game weapon wheels in genre only: no game names, art, fonts or sounds. |

## 3. Workflow and CI

- **One ticket = one branch = one PR.** Branch `v8/NN-short-name` from `main`; PR to `main` with the ticket number in the title and the acceptance criteria as a checklist.
- The existing CI pipeline must be green to merge: back-end pytest (Python 3.11 and 3.14, simulated mode, no API key), front-end type check and production build, extension manifest check, version consistency check, start-script smoke test.
- The front end has no test runner. Front-end criteria are met by "type check and build pass" plus a check in the browser preview (screenshot in the PR). Back-end behaviour always gets pytest coverage.
- **Definition of done:** acceptance criteria ticked in this file, CI green, common criteria (section 7) respected, and the ticket's **Status** line updated here.
- The version moves to **8.0.0** in ticket 01; no other ticket touches it.

## 4. Access matrix (what changes)

| Tab / feature | Helena (CoE de IA) | Creators (Marina, Rafael, Carla, Thiago) | Lucas (Engineering/Security) |
|---|---|---|---|
| **Radial persona selector** *(new)* | everyone, before login | | |
| **Processes** tab *(new)* | view all; costs and health | create, edit, test, publish, run processes of their area | view; pause in emergency |
| **Agents** tab | view | create single worker agents (Studio) | view; pause in emergency |
| **Files & Sheets** plugin *(new, real)* | upload/preview; exports Finances to a sheet | upload, use in agents and processes | upload/preview; incident log |
| **Create your plugin** *(new)* | approves (AI analyst) | proposes | proposes (as engineering); co-approves confidential/restricted |
| Other tabs | as in v7 | as in v7 | as in v7 |

## 5. Tickets (vertical slices)

| # | Ticket | Phase | Blocked by |
|---|---|---|---|
| 01 | Version 8.0 everywhere | 0 · Base | — |
| 02 | Radial persona selector on the home screen | 1 · Home | — |
| 03 | Prefactor: owner-agnostic lifecycle and runner | 2 · Processes (expand) | — |
| 04 | Processes tab (tracer bullet) | 2 · Processes (expand) | 03 |
| 05 | Low-code block palette | 2 · Processes (expand) | 04 |
| 06 | Agents become single workers | 2 · Processes (expand) | 04 |
| 07 | Move demo seed and guided scripts to processes | 2 · Processes (migrate) | 05, 06 |
| 08 | Scheduled tasks, extension, AI Map and Finances understand processes | 2 · Processes (migrate) | 06 |
| 09 | Contract: retire multi-step agents | 2 · Processes (contract) | 07, 08 |
| 10 | Files & Sheets: the real plugin | 3 · Plugins | — |
| 11 | A Files & Sheets use for every persona | 3 · Plugins | 05, 10 |
| 12 | "Create your plugin": request and draft spec | 3 · Plugins | — |
| 13 | Approve and publish internal plugins | 3 · Plugins | 12 |
| 14 | v8 guided scripts, pitch and docs | 4 · Closing | 01, 02, 09, 11, 13 |
| 15 | v8 release check | 4 · Closing | 14 |

**Execution order for a single run:** 01 → 02 → 03 → 04 → 05 → 06 → 07 → 08 → 09 → 10 → 11 → 12 → 13 → 14 → 15. (01, 02, 03, 10 and 12 have no blockers and could also run in parallel.)

```
01 ─────────────────────────────────────────────┐
02 ─────────────────────────────────────────────┤
03 ── 04 ─┬─ 05 ──────────┬─ 07 ─┐              │
          └─ 06 ─┬────────┘      ├─ 09 ─────────┤
                 └─ 08 ──────────┘              ├─ 14 ── 15
10 ──────────────────── 11 (also needs 05) ─────┤
12 ── 13 ───────────────────────────────────────┘
```

---

### 01: Version 8.0 everywhere

**What to build:** the extension appears as **"StoneFalcon 8.0"** on the browser extensions page with version 8.0.0. The API health route, the extension side panel and options page, and the hub footer show the same version, read from the single version source. The README tells v7 users to remove and reload the extension.

**Blocked by:** None (can start immediately).

**Status:** done

- [x] The health route answers 8.0.0.
- [x] Extension manifest name "StoneFalcon 8.0", version 8.0.0; options page and hub footer show 8.0.
- [x] Front-end package version is 8.0.0.
- [x] The CI version-consistency check passes, and fails if any of the three diverges (tested).
- [x] README "Updating from a previous version" mentions v7 → v8 and the extension reload.

### 02: Radial persona selector on the home screen

**What to build:** on the login screen, the six personas sit in a ring split into 6 equal slices, each slice showing that persona's photo (initials in the persona's color if the photo fails). Hovering or keyboard-focusing a slice **expands it outward with a smooth animation** (radius grows, neighbours shrink slightly, slice brightens) and the centre of the ring reveals that person's details: name, role, area, short description, role badges ("creates agents", "reviews security"…) and access level. Clicking the slice (or Enter) enters as that persona; a "Start guided script" button in the centre starts their script, exactly as the current cards do. Narrow screens and users with reduced motion get the existing card grid (or a no-animation version).

**Blocked by:** None (can start immediately).

**Status:** done

- [x] Desktop login shows a 6-slice ring with each persona's photo; no persona cards on desktop.
- [x] Hover or focus expands the slice with an animation (≤ 250 ms, eased) and shows name, role, area, description, role badges and access level in the centre.
- [x] Moving between slices animates the previous one back; leaving the ring returns to a neutral centre ("Who are you today?").
- [x] Click/Enter enters as that persona; the centre's "Start guided script" starts the persona's script (same behaviour as today, including the "Preparing…" state and error message).
- [x] Keyboard: Tab enters the ring, arrow keys move between slices, Enter selects; each slice has an accessible name and a visible focus ring.
- [x] `prefers-reduced-motion` disables the expansion animation (details still change instantly).
- [x] Below the medium breakpoint the existing card grid is shown instead; no horizontal scroll at 375 px.
- [x] Photo load failure falls back to initials in the persona's color inside the slice.
- [x] Persona data comes from the existing profiles endpoint only (no hard-coded persona list in the front end); works in both light theme and the extension-free hub.
- [x] Type check and build pass; checked in the browser preview by DOM/keyboard/hover (the pane was hidden, so no screenshot could be captured).

### 03: Prefactor — owner-agnostic lifecycle and runner

**What to build:** "make the change easy". The versioned lifecycle (draft → review → published ⇄ paused → deprecated, immutable versions with diff, four-eyes review for high risk, emergency pause, hash-chained audit) and the step-graph runner (layers in parallel, approvals, resume, budgets, escalation) stop assuming that the owner is an agent. Executions record **what** ran (`agent` or `process`, plus its id and version). No behaviour change for users.

**Blocked by:** None (can start immediately).

**Status:** done

- [x] Lifecycle operations and version/diff logic accept an owner type, with agents as the only owner for now.
- [x] The runner executes a step graph given an owner reference instead of an agent id; budgets, escalation and approval resume still work.
- [x] Executions store the owner type and id; existing rows read as `agent` (existing databases keep working: new columns/tables only, `create_all` compatible).
- [x] Audit events carry the owner type.
- [x] The full existing back-end suite passes unchanged (no test edited except to add owner-type assertions).

### 04: Processes tab (tracer bullet)

**What to build:** a new **Processes** tab. A creator opens "New process", names it, links it to their area (and optionally to their guided script's AS IS → TO BE process), and places **Agent blocks** that reference published agents on a canvas, connecting them in sequence or in parallel. They can test it in the sandbox, save drafts, publish (same lifecycle and review rules as agents) and run it. The execution timeline shows the process, each block, and which agent ran inside it. Everyone sees the tab; only creators of the area edit.

**Blocked by:** 03

**Status:** ready-for-agent

- [ ] The `processes` tab is in the back end's per-profile tab list (single source of truth) for all personas; the menu shows "Processes" between "Agents" and "Plugins"; the API enforces edit rights (403 for non-creators or other areas).
- [ ] A process stores: name, goal, owner, area, optional linked script/process, input fields, blocks (graph), limits, manual minutes (ROI baseline); versioned like agents.
- [ ] The canvas lets a creator add Agent blocks (picking from published agents they can run), connect them, and remove them; cycles and dangling references are rejected with a plain-language message.
- [ ] Sandbox test runs the draft and shows the timeline per block; publish follows the agent rules (high risk → security review).
- [ ] Running a published process records one process execution with nested per-block results; cost and time are summed per process.
- [ ] Process list shows owner, area, state, version, linked AS IS process, executions and cost; process detail shows versions, lifecycle history and a run form.
- [ ] Back-end tests: create → test → publish → run; parallel blocks run together; permission checks; a paused agent inside a process escalates with the reason.

### 05: Low-code block palette

**What to build:** the process canvas gets a palette of blocks that a non-programmer drags in and configures in a side panel, in plain language: **Inputs/Trigger**, **Data source** (a read tool from an integrated plugin, e.g. read a sheet), **Agent**, **Plugin action** (any integrated plugin tool), **Human approval**, **Condition** (simple rule on a previous block's output: equals / contains / greater than), and **Notify/Output** (e.g. Slack message or final answer). Block outputs can be wired into later blocks' inputs by picking from a list, never by typing template syntax. Validation runs live.

**Blocked by:** 04

**Status:** ready-for-agent

- [ ] Palette with the 7 block types, each with an icon, color and one-line description.
- [ ] Side panel per block: plugin/tool pickers only list tools the creator may use (plugin integrated, area and classification allowed); disallowed ones show why.
- [ ] Wiring outputs to inputs is done by picking "output of block X → field" from a list; the stored graph uses the existing template references under the hood.
- [ ] Condition block routes to a "yes" and a "no" branch; the runner skips the branch not taken and the timeline shows it as skipped.
- [ ] Live validation highlights blocks with missing configuration or no permission, in plain language; publish is disabled while invalid.
- [ ] Risk and cost estimate update as blocks change (reusing the agent estimate rules).
- [ ] Back-end tests for each block type, the condition branch skip, and permission filtering.

### 06: Agents become single workers

**What to build:** the Studio now builds **one reusable AI worker**: what it does (instructions), the tools it may use, the model (or automatic), its input fields, limits, and a sandbox test. "Describe your process" in the Studio produces a worker agent and, when the description is clearly multi-step, offers "Turn this into a process" (opens the Processes editor pre-filled with the suggested blocks). Agent detail gains **"Used in processes"** (each process, its owner persona and its linked AS IS process), which answers "which process does this agent belong to?". Existing multi-step agents keep running and are labelled **"legacy multi-step: convert to process"**.

**Blocked by:** 04

**Status:** ready-for-agent

- [ ] The Studio creates and edits single-worker agents only; the canvas in the Studio is replaced by the worker form plus test panel.
- [ ] A multi-step description shows "Turn this into a process", which opens a pre-filled process draft whose Agent blocks are new worker agents (drafts, owned by the creator).
- [ ] Agent detail lists the processes that use it (name, owner persona, area, linked AS IS process); the Agents list shows a "used in N processes" badge.
- [ ] Existing multi-step agents still execute and show the "legacy" label with a "Convert to process" action (conversion creates the worker agents and a process; the old agent stays until ticket 09).
- [ ] Pausing or deprecating a worker agent warns about, and is reflected in, the processes that use it.
- [ ] Back-end tests: worker create/test/publish; conversion of a multi-step agent produces an equivalent process (same tools, same order/parallelism, same approvals).

### 07: Move demo seed and guided scripts to processes

**What to build:** the demo's initial state now tells the new story. The seeded multi-step agents are converted into worker agents plus processes (e.g. Thiago's "machine swap" becomes a process with parallel data blocks, a worker agent and a Slack notify block). Each creator persona's guided script becomes "create a worker agent → assemble the process → test → publish → run", and the AS IS × TO BE card points to the process. "Reset demo" restores exactly this state.

**Blocked by:** 05, 06

**Status:** ready-for-agent

- [ ] Seed creates worker agents and processes equivalent to the former multi-step agents; 30 days of generated history are attributed to processes (and to the agents inside them).
- [ ] Marina, Rafael, Carla and Thiago scripts walk through agent → process; Lucas and Helena scripts reference processes where they referenced agents.
- [ ] AS IS × TO BE numbers are computed from process executions, with the same "measured / estimated / premise / hypothesis" labels.
- [ ] Script steps resolve processes by name, like they resolve agents today.
- [ ] Reset demo returns the exact initial state (tested).
- [ ] Every script runs end to end in simulated mode (back-end script tests updated and green).

### 08: Scheduled tasks, extension, AI Map and Finances understand processes

**What to build:** everything that used to point at "an agent" can point at a process. A creator schedules a published **process** ("every Monday at 9:00"). The extension's "Answer with…" menu and side panel list the processes and worker agents the profile may run. The AI Map gains a **processes** layer (creator → process → agents → models → plugins/tools → platforms). Finances shows cost, savings and ROI per process alongside per agent.

**Blocked by:** 06

**Status:** ready-for-agent

- [ ] Scheduled tasks accept a process or an agent; the run uses the scheduler's permissions, guardrails and budget; sensitive actions still wait for human confirmation.
- [ ] Extension lists processes and agents grouped, with the same permission filter as the hub; running a process from the extension shows its blocks in the panel.
- [ ] AI Map shows the processes layer with live pulses per execution and the existing area/provider filters.
- [ ] Finances: cost and ROI per process; drill-down into the agents inside it; the "what if everything ran on X" view includes processes.
- [ ] Back-end tests for scheduled process runs, the extension listing and the per-process finance totals.

### 09: Contract — retire multi-step agents

**What to build:** with every caller migrated, the old form goes away. New agent versions must be single workers; any remaining legacy multi-step agent in an existing database is offered a one-click conversion and is otherwise read-only. Dead code paths and labels that only served multi-step agents are removed.

**Blocked by:** 07, 08

**Status:** ready-for-agent

- [ ] Saving an agent version with more than one step is rejected with a plain-language message pointing to Processes.
- [ ] Legacy multi-step agents loaded from an older database run, are read-only, and show "Convert to process".
- [ ] No front-end screen or back-end route still builds multi-step agents; unused code removed.
- [ ] A v7 database opens in v8 without errors (tested with a v7 fixture).
- [ ] Full back-end suite green; front-end build green.

### 10: Files & Sheets — the real plugin

**What to build:** a new marketplace plugin that **actually works**, offline, for every area. A person uploads a CSV or XLSX in the plugin page, chooses its data classification (public → restricted, capped by their own access level) and which areas may use it. Agents and processes get real tools: list files, read rows (with optional filter), find a row, append a row, update a cell/column in a row. The plugin page shows a preview grid and lets people download the current file. It goes through the same permission, guardrail (personal data masked before any model) and audit path as every other tool, and it is badged **"real"**.

**Blocked by:** None (can start immediately).

**Status:** ready-for-agent

- [ ] Plugin appears in the marketplace for all areas with the badge "real"; integrating follows the existing rules (confidential/restricted files need the security approval path).
- [ ] Upload accepts CSV and XLSX up to a size/row/column limit (shown in the UI); invalid files get a plain-language error.
- [ ] File classification cannot exceed the uploader's access level; a file is only readable by people whose area and level cover it.
- [ ] Tools: list files, read rows (filter), find row, append row (write → needs human confirmation when the file is confidential or above), update row; each has a JSON schema like the other catalogue tools.
- [ ] Reads pass through masking (CPF, CNPJ, card, e-mail, phone, secrets become markers before any model); writes are recorded in the audit trail with who, which agent/process and which row.
- [ ] Plugin page: preview grid, row count, last change, download of the current version, and the usual usage/cost/health numbers.
- [ ] `openpyxl` added to the back-end requirements; the start scripts reinstall it automatically (verified once on Windows).
- [ ] Reset demo restores the seeded files.
- [ ] Back-end tests: upload/parse CSV and XLSX, permission by area and level, masking on read, append/update with audit, confirmation on confidential write.

### 11: A Files & Sheets use for every persona

**What to build:** each of the six personas has one working, demoable use of the real plugin, with seeded files: **Marina** reads an FAQ sheet to answer merchants; **Rafael** reads a chargeback list and appends the triage decision (restricted, with confirmation); **Carla** reads a benefits table (confidential, masked); **Thiago** reads pending machine-swap requests and marks the handled row; **Lucas** keeps an incident log that a process appends to when a system goes down; **Helena** exports the Finances summary to a sheet from the Finances page.

**Blocked by:** 05, 10

**Status:** ready-for-agent

- [ ] Six seeded files, one per persona, with fictional data and the right classification/areas.
- [ ] Marina, Rafael, Carla and Thiago each have a seeded process that uses a Files & Sheets block and runs green in simulated mode.
- [ ] Lucas: the "system down" flow appends to the incident log (visible in the plugin preview).
- [ ] Helena: "Export to sheet" in Finances writes a new file she can preview and download.
- [ ] Each use is reachable in ≤ 3 clicks from the persona's home and is listed in the README.
- [ ] Back-end tests for each persona's use, including a denied cross-area read.

### 12: "Create your plugin" — request and draft spec

**What to build:** a **"Create your plugin"** button in the Plugins tab. A creator or engineer names an existing market tool, pastes its **public** feature description (or a public docs excerpt), says what the company needs it for, which areas would use it and how sensitive the data is. The platform drafts an **internal plugin spec** by "reverse-engineering" the public features: capabilities, proposed tools (read/write, inputs, outputs), data classification, areas, risks, and a build-vs-buy estimate (license cost vs. estimated build and run cost). The requester edits the draft and submits it; it lands in the AI analyst's queue (Helena). Helena gets the new **AI analyst** role.

**Blocked by:** None (can start immediately).

**Status:** ready-for-agent

- [ ] New role `ai_analyst` assigned to Helena in the identity module; persona count stays 6.
- [ ] Only creators and engineering see "Create your plugin"; others see the marketplace as before. The API enforces it (403).
- [ ] The wizard collects: market tool name, pasted public description (required, length-limited), purpose, areas, data sensitivity; a notice says only public information may be used, no logos/trademarks/code.
- [ ] Draft generation: real mode uses the model (with injection guardrails on the pasted text); simulated mode uses a deterministic template, so the demo works without a key.
- [ ] The draft shows capabilities, proposed tools (name, read/write, inputs, classification), areas, risks and build-vs-buy numbers, all editable before submitting.
- [ ] The generated plugin uses a generic internal name ("Internal scheduling tool", not the market brand) and a generic category icon.
- [ ] Submitting creates a request (state "awaiting AI analyst"), notifies Helena, and is recorded in the audit trail; the requester can see the request status.
- [ ] Back-end tests: access control, draft generation in simulated mode, injection text in the pasted description is isolated, request creation and audit.

### 13: Approve and publish internal plugins

**What to build:** Helena reviews "Create your plugin" requests in her queue with the spec side by side and approves or rejects with a written opinion. If the spec's classification is confidential or restricted, the request then goes to **Lucas** for a security sign-off (four eyes). Nobody decides their own request. On final approval, the internal plugin is published to the marketplace with the badge **"internal · conceptual"**; its tools are generic simulated implementations that follow the spec's schema. It can be integrated like any plugin and used as a Plugin action/Data source block in processes. The requester is notified of the outcome.

**Blocked by:** 12

**Status:** ready-for-agent

- [ ] Helena's queue lists pending "Create your plugin" requests with the spec, requester, areas, classification and build-vs-buy numbers.
- [ ] Approve/reject requires an opinion; rejection closes the request and notifies the requester.
- [ ] Confidential/restricted specs require Lucas's approval after Helena's; a request made by Helena or Lucas cannot be decided by themselves (the other one decides, as in the v6 plugin rule).
- [ ] Approved plugin appears in the marketplace with "internal · conceptual" and "simulado" badges, its tools in the catalogue with origin "internal plugin X".
- [ ] Its simulated tools return schema-valid fictional data; write tools follow the usual confirmation rules.
- [ ] It can be integrated and used as a block in a process; removing it flags dependent processes like other plugins.
- [ ] Every step (request, each decision, publication, removal) is in the audit trail; Reset demo removes internal plugins.
- [ ] Back-end tests: four-eyes path, self-approval blocked, publication registers tools, process using an internal plugin runs.

### 14: v8 guided scripts, pitch and docs

**What to build:** the demo tells the v8 story end to end. The pitch script opens on the radial persona selector, shows a creator building a worker agent and then a process that uses the real Files & Sheets plugin, shows a "Create your plugin" request approved by Helena (and Lucas for a sensitive one), and closes on the AI Map and Finances per process. Docs and "Perguntas da Ferramenta" cover the new features.

**Blocked by:** 01, 02, 09, 11, 13

**Status:** ready-for-agent

- [ ] Pitch script v8 (Helena's Scripts tab) covers wheel → agent → process → real plugin → create your plugin → AI Map/Finances, in 8–10 minutes, fully in simulated mode.
- [ ] Each persona's script still ends on its AS IS × TO BE card, now based on processes.
- [ ] Three new "Perguntas da Ferramenta": "Why separate agents and processes?", "Is the plugin real?", "How do you stop someone cloning a vendor tool?" — each with a short answer and "Show on screen".
- [ ] README: "What's new in v8", updated access matrix, Files & Sheets usage, Create your plugin rules, updated architecture diagram and test count.
- [ ] Rehearsal checklist updated with the v8 flow.

### 15: v8 release check

**What to build:** confirm the whole v8 runs cleanly from a fresh folder and from a folder that already ran v7.

**Blocked by:** 14

**Status:** ready-for-agent

- [ ] Back-end suite green in Python 3.11 and 3.14, simulated mode, no API key.
- [ ] Front-end type check and production build green; extension and version checks green.
- [ ] `iniciar.bat` (Windows) and `iniciar.sh` (Linux) start v8 and answer 8.0.0 on the health route, from a fresh folder and from a folder with a v7 database (which opens without errors).
- [ ] Every guided script runs end to end; Reset demo restores the initial state.
- [ ] Manual browser pass: radial selector (mouse, keyboard, reduced motion, narrow screen), Processes editor, Files & Sheets upload/preview/download, Create your plugin request → approval → use in a process.
- [ ] Ticket statuses in this file updated; open issues listed at the end of this file.

## 6. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Changing "agent" breaks many call sites at once | Expand → migrate → contract (03–09); old multi-step agents keep running until 09. |
| Wheel looks good on desktop but fails on small screens or for keyboard users | Card grid fallback, keyboard navigation and reduced motion are acceptance criteria in 02. |
| "Reverse-engineering" read as copying a vendor | Only public descriptions pasted by the user, no scraping, generic names and icons, no code; human approval by the AI analyst (and security for sensitive data). |
| Real plugin leaks sensitive file data | Same permission/classification path as other tools, masking before any model, confirmation on confidential writes, full audit. |
| New dependency (`openpyxl`) breaks start scripts | Start scripts already reinstall on requirements change; verified in 10 and 15. |

## 7. Common criteria (every ticket)

- All user-facing text in Brazilian Portuguese, plain language, no code or template syntax shown to non-engineers.
- Personas, areas, merchants and data stay fictional; nothing presented as an official Stone product.
- Everything works in simulated mode, without an API key or internet (except features explicitly marked otherwise).
- Access is decided by the back end (tab list + API checks); the front end only reads it.
- Every state change that matters (create, publish, approve, integrate, write) is in the hash-chained audit trail.
- Reset demo restores the exact initial state after the ticket's changes.
