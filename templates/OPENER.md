lane: hub
written: at install
by: the installer
on: here
head: none (the hub folder is the brain)
status_updated: at install
where: fresh install — nothing has happened yet
next: machine
depends_on: nothing
open_in: the hub folder · a fresh session titled ACT — hub: first session
model: any · default
judgment: none
---
read the project status/memory first.
1. Read the clock: `date` (Windows PowerShell: `Get-Date -Format "dddd yyyy-MM-dd HH:mm"`).
2. Pull the brain, from this folder: `python3 sync/sync.py pull` (`python` on Windows, here and below).
3. Stamp this session, then claim the hub: `python3 tools/i-am.py <mind> <effort> "ACT — hub: first session"`, then `python3 tools/claim.py --claim hub "ACT — hub: first session"`.
4. Make the first project: `python3 tools/new-project.py <name>`.
5. Say what you are working on in STATUS.md `## Now` — the new project's, and this folder's own.
