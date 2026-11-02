# Security

## Reporting a vulnerability

Report it through this repository's private security advisory — the
"Report a vulnerability" link under the repository's Security tab — rather
than a public issue.

## What this program registers, and where

- Background jobs with your operating system's scheduler: launchd agents on
  macOS, scheduled tasks on Windows. They are named in
  `sync/install/jobs.json`.
- `~/.claude/exocortex-laws.md`, written and re-rendered by the installer.
- `~/.claude/CLAUDE.md`, three lines (a title and the two lines that load
  the law books), written only when that file is absent; a file of yours is
  never edited.
- The four shipped skills (desk, focus, sweep-sessions, sync), copied into
  `~/.claude/skills/` only when absent.

The installer also writes, in the folders you name: the machine file
`machine.json` (your roots), your brain folder (`~/exocortex-brain` unless you
say otherwise), `hygiene-settings.json` and one `INSTALL-WATCHERS-<machine>.md`
sheet in the hub, and `AGENTS.md` in your Codex folder when the machine records
one and the file is absent. On Windows the scheduled tasks are registered by a
script the installer writes to the system's temporary folder.

Nothing else is registered with your machine. Nothing is sent anywhere but the
private git remote you choose for your own brain, with one exception you can
see in `sync/sync.py`: before the first push to a GitHub remote the sync asks
the GitHub API whether that repository is private, and refuses to push to a
public one.
