---
name: sweep-sessions
description: Review session clutter across available vendors and propose one archive, rename, needs-harvest and keep list. Use for session cleanup or a requested sweep. No archival or deletion occurs without the owner's approval.
---

# Sweep sessions

Follow `{{HUB}}/laws/LAWS.md` and the owner's private laws. A session can be archived only after its unique work is saved outside the conversation. This skill proposes first; it never treats a stale title as permission to archive.

## Inventory

Use the current surface's session-list tools and inspect all available pages. Group by the verified working folder, then stable lane. If a vendor is unavailable, say which part of the inventory is missing; do not call it a complete sweep.

When local transcripts are available, use the installed `python3 tools/tail-session.py --scan "<session-root>" --days <days>` from `{{HUB}}` to supplement discovery. Windows uses `python`. Read the session root from the machine record. Keep raw transcripts local.

## Classify and propose

Read the project's STATUS, opener, claim and relevant memory before deciding whether a session's work has been saved. Inspect the transcript tail when the record is unclear.

- **Archive candidate:** unique work is preserved and verified. Keep newly retired sessions visible for one day by default, and retain useful live context longer with a reason.
- **Needs harvest:** unique decisions or work remain only in the conversation. Name what must be saved and the responsible lane; do not archive yet.
- **Rename candidate:** the title is misleading or missing its state tag. Preserve owner-chosen titles unless clearly stale, and keep the same lane token.
- **Keep:** active, recently used or needed for open work. An old timestamp alone does not make a session disposable.

Check duplicate-looking sessions independently; the older one may hold unique work. For a misfiled session, propose the correct existing project or an exactly named new one. Do not claim its working folder can be moved when the app cannot do so.

Present one combined list grouped by project, with one reason per proposed action. Wait for the owner's ruling. No deletion is part of this skill, including sessions marked `DEL?`.

## Apply approved actions

Recheck activity and harvest evidence immediately before archival. If state changed, preserve the session and report the difference. Use only native tools actually available on the current surface, and verify the result rather than assuming the app changed.

Titles use `ACT`, `ARCH`, `HARV` or `DEL?` followed by the stable project/lane and a short purpose. A rename to `ARCH` requires verified saved carryover. Do not wake another session to harvest itself unless that communication is part of the approved work; the authorized hub can capture an idle session from its local record.

Save a short sweep receipt in the private hub with counts, approved actions, remaining harvest work and any unavailable vendors. Record a new cadence preference in the dossier, not as an automatic schedule.

If the hub is inaccessible, give an explicitly unsaved receipt for an authorized writer. Keep completed app actions distinct from bookkeeping that remains unsaved.
