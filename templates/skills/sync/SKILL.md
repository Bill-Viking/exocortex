---
name: sync
description: Sync the configured private brain and check the carriers needed for project continuity. Use for a requested sync, drift check, machine arrival or the wake and close rituals. Report verified completion and pending transfers separately.
---

# Sync

Follow `{{HUB}}/laws/LAWS.md` and the owner's private laws. `{{HUB}}` is the installed hub and `{{SYNC}}` is the installer-rendered sync command, including its interpreter. Stop on unresolved tokens; never guess a home path.

## Inspect the carriers

Read this machine's installed `machine.json`, carrier registry and open drive-ledger items in the hub and relevant projects. Inspect each required drive by its label and test each required private host with a bounded reachability check. An absent carrier and a carrier with no work owed are different facts.

If a required carrier is unavailable, name it and the exact work waiting on it. Request the physical connection or host availability, and complete independent reachable work. A one-machine, local-only setup has no other machine or remote to invent.

## Run the requested operation

- `{{SYNC}} status` inspects drift without choosing a winner.
- `{{SYNC}} pull` brings the brain in before reading project state at wake.
- `{{SYNC}} push` carries the completed record out at close.
- `{{SYNC}} sync` performs pull then push for a normal sync request.

Check the exit status and flags. The brain and project repositories have separate carriers; one successful brain command does not prove project work has crossed. Update project carriers only when the request or established startup or handoff scope includes them, after the one-writer checks. A brain-only request means inspect and report project drift, not upload it. Preserve dirty work and each project's allowed carrier.

A no-remote or upstream-readonly project receives no new remote or push. A transfer drive is a declared carrier, not permission to upload its material elsewhere. If installation or configuration is missing, name the missing piece and use the installed setup instructions instead of fabricating it.

## Resolve without losing work

Keep both sides of a conflict, show the meaningful difference and propose a resolution. Repair a mechanical problem within existing authority and verify it. Ask the owner when a choice between valid intentions needs their ruling; never silently pick a side or reset away work.

An intentional deletion already recorded in the brain may remove an unchanged local mirror with a recoverable receipt. Preserve modified local copies. A new local deletion is a proposal until approved for propagation. Machine-specific settings drift remains a report unless that configuration change is authorized.

On a slow or interrupted transfer, preserve progress and inspect the receiving result before retrying. An unavailable carrier leaves a partial sync with a responsible party and next action; it is not a reason to weaken the completion check.

## Receipt

Give one short digest: files in and out, changes the owner needs to know, the last observed sync of other registered machines, and any flags. Distinguish a local mirror update, remote push and verified receiving-machine arrival. If nothing moved, say so.

At wake, continue with the law book's claim, stamp, state and mail sequence. At close, push after the carryover, surface refresh, claim release and stamp-off. Verify the intended files reached the brain; files still waiting for a settling interval remain pending.
