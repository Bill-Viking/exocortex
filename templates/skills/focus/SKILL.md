---
name: focus
description: Plan a work session, day or week from every registered project's STATUS and the owner's recorded priorities. Use when the owner asks what to work on, wants to prioritize or invokes focus.
---

# Focus

Help the owner choose a small, realistic set of outcomes from the actual record. Follow `{{HUB}}/laws/LAWS.md` and the owner's private laws. Run hub commands from `{{HUB}}`; examples use `python3`, or `python` on Windows.

## Read before recommending

Read the real clock, then every project's STATUS within the owner's authorized planning scope: the configured projects root and any additional registered project roots. Read all sections, including Important constraints and unfinished urgent items. Honor recorded access restrictions and report exclusions or unreadable state; do not quietly drop a project.

Read the available dossier in the hub, especially the owner's profile, principles, rhythms and learned preferences. If absent, proceed from the request. Do not invent an energy pattern or schedule.

If available time materially changes the choice and is unknown, ask one compact question. Otherwise use the supplied constraints and keep moving.

Run `python3 tools/ideas.py --list --new` when the installed tool is available. Raise an urgent idea briefly. For ordinary new ideas, propose filing into a named project, keeping for later or dropping. Keep capture separate from approval of new work.

## Choose

Weigh verified urgency, moves that unblock other work, the owner's priorities and the cost of resuming a project. Offer up to three items by default, each with an outcome, a concrete first step and one sentence explaining why it fits. Do not repeat the full project inventory.

For a week, assign work only against known availability and leave room for interruption. Treat the proposal as the owner's choice. Do not announce commitments they have not made.

## Save the agreed plan

Write the agreed plan to a dated `PLAN-YYYY-MM-DD.md` in the private hub. Include each chosen project's verified location, first action and deliberate deferrals. Scheduling a task does not complete its STATUS checkbox.

If the hub is inaccessible, provide the plan as an explicitly unsaved delta for an authorized writer. Do not say it was persisted.

Check ownership before updating project state. File approved ideas with `python3 tools/ideas.py --file <number> --to "<project>" --item "<todo>"` only when authorized to write that project; otherwise mail its holder. Use `python3 tools/ideas.py --someday <number>`, `--drop <number>` or `--done <number>` for an approved disposition. Keep item history.

Verify any claimed completion before checking its box. Preserve unrelated changes when committing an owned STATUS update, and use only that project's allowed carrier.

Save a newly stated durable preference to the dossier. Ask separately before promoting it into a standing private law. End with the chosen next move in ordinary words.
