# Exocortex

<img src="icon.png" alt="" width="96" height="96">

Exocortex is a folder of plain files that your AI sessions read before they
start and write before they stop. The record belongs to you, not to a model
or a vendor: switch from Claude Code to Codex, or from one machine to
another, and the next session wakes up already oriented, reading what the
last one wrote. Every project you have is on one page, with whose move is
next. And nothing irreversible happens without your own hand: you hold the
key.

You work across projects, machines and models. A conversation gets long, a
session ends, you switch computers, and you become the one who remembers
where everything stands and explains it again. Exocortex keeps that record
outside any one conversation.

What is in the folder:

- `STATUS.md` per project: where it stands, what is left, what was decided.
- An opener: the next session's starting point, written by the last one.
- Mail between sessions, and a claim that says who may write.
- A tree page that shows every project and whose move is next.

What it is not: an assistant, a chatbot, or a memory database. It runs
beside the coding agents you already use (Claude Code, Codex, Grok) and
stays on your own machines; your record never leaves your private repository.

Read the essay behind it: [The soul of the operating system](docs/WHY.md).
How it is built: [How Exocortex is built, how it compares, and where it goes](docs/DESIGN.md).

## What it needs

- Python 3.9 or later
- git
- macOS or Windows
- A private git remote for your own brain (never a public one)
- A coding-agent session, such as Claude Code, Codex, or Grok

## Where it runs

Exocortex has no app of its own. It runs inside the coding agent you already
use, wherever that agent runs:

- **The Claude Code desktop app** (the Code tab of the Claude app) is the
  easiest door. Open your hub folder as a project, start a session, and type
  `hub`: the session reads the record and hands you each project's next step
  in the chat. Each project gets its own session, opened on its own folder.
- **The Codex app** works the same way. Open the hub folder, or a project's
  folder, and start a thread; Codex reads its `AGENTS.md` and the same files,
  under the same laws.
- **The terminal** is the other door: `cd` into the folder and start
  `claude` or `codex` there. Every hand-off Exocortex gives you carries both
  doors, the text for the app's chat box and the one-line launch for your
  shell.

<!-- The three screenshots go here once captured; docs/screens/OWED.md says
     what each must show and the scrub rule they pass before they ship:
![The hub's wake in the Claude Code desktop app](docs/screens/hub-wake-claude-code.png)
![A project thread in the Codex app](docs/screens/lane-thread-codex.png)
![The tree page](docs/screens/tree-page.png)
-->

## Install

Clone the program, then run the installer from the cloned folder (command
examples use `python3`; on Windows use `python` in its place):

    python3 sync/install.py

The installer offers three ways to a brain: join an existing one by URL or
path, make a new one that stays only on this disk, or make a new one and
push it to a remote you name. Its fourth step renders the law book for
this machine into `~/.claude/exocortex-laws.md`, and writes
`~/.claude/CLAUDE.md` only when that file does not already exist yet — a
file of yours is never edited. The first run also draws the board and the
tree.

The program lives in the folder you cloned; that folder is your hub, where
your projects' state, your mail and your claims are written. Your brain — the
folder you name at install, `~/exocortex-brain` unless you say otherwise — is
your own private repository: the heartbeat carries the hub's state into it,
and none of it ever rides the public history.

## How it compares

| kind | examples | what it holds | sessions and machines | Exocortex's focus |
|---|---|---|---|---|
| personal AI assistants | OpenClaw, Hermes Agent | Acts on your behalf: messages you, remembers things, and runs tasks. | Chat or terminal access; OpenClaw supports multiple workspaces. | Project status, next-session openers, and writing claims. |
| markdown brains for agents | agentBrain, Open Second Brain | Shared Markdown memory that supported agents read and write. | Shared files; agentBrain adds sync and opt-in messaging. | STATUS, openers, mail, writing claims, and a project tree. |
| memory tools and platforms | mem0, Letta (also Basic Memory) | Persistent memory via SDKs, agents, or Markdown and MCP. | Local or hosted; cloud options span computers. | A plain-file law book and project coordination. |
| agent instruction files | CLAUDE.md, AGENTS.md | Instructions read at the start of a session, per project or per user. | AGENTS.md spans tools; files travel with a repo. | STATUS, mail, claims, and a tree across machines and vendors. |

OpenClaw acts for you: it runs on your own machine and answers you in your chat apps.
Exocortex is not an assistant; it is the shared record your coding-agent sessions work
in.

For shared agent memory, consider agentBrain or Open Second Brain. Exocortex focuses
on project status, session handoffs, writing claims, and a tree across projects.

## First run

Open the board or the tree page. The tree starts with one tile: the hub
itself. Add your first tracked project with:

    python3 tools/new-project.py <name>

The new project gets a `STATUS.md`, an opener, and, when git is on your
machine, its own repository with one commit. Redrawing the board or the
tree picks it up.

## Every day

Open a session in your hub folder and type `hub`. That session is your front
desk: it reads the record, opens the tree, and hands you each lane's next step.

Each session begins with a short wake sequence: check the real clock, pull
the brain, check whether another session already holds the project's
writing claim, stamp itself in, then read `STATUS.md`, the opener, and any
mail addressed to it. During the day, sessions send and read short messages
with `tools/mail.py`, and hold a claim through `tools/claim.py` so only one
session writes a given project or lane at a time. The tree page always
shows where each project stands and whose move is next.

## What it touches on your machine

- `~/.claude/CLAUDE.md` — only if that file is absent
- `~/.claude/exocortex-laws.md` — written by the installer, and re-rendered
  when the shipped law book changes
- The four shipped skills (desk, focus, sweep-sessions, sync), copied into
  `~/.claude/skills/` when absent
- Background jobs — launchd agents on macOS, scheduled tasks on Windows —
  named in `sync/install/jobs.json`
- The hub folder (the clone) and the brain folder you chose at install, with
  `machine.json` naming your roots
- `hygiene-settings.json` and one `INSTALL-WATCHERS-<machine>.md` sheet in
  the hub; `AGENTS.md` in your Codex folder when the machine records one and
  the file is absent
- On Windows, a task-registration script written to the system's temporary
  folder

Nothing goes anywhere but the private git remote you choose for your own
brain; the one call outside it is a read of the GitHub API before the first
push, to confirm that remote is private. The pages it draws load no font
from the network.

## Prove your install

    python3 tools/prove-install.py

This runs every gate the program ships against your own install, from your
own `tools/` folder, and prints one table: what each gate checked, how many
checks passed, how many failed, and how long it took.

On Windows the table runs the gates that are Windows-true today and says, in
one line above it, which are not yet run there and why; the install, the
heartbeat and the uninstall were proven on Windows 10 by hand. Setting
`EXO_PROVE_EVERYWHERE=1` runs them anyway.

## Uninstall

    python3 sync/install.py --uninstall

Removes only what the installer made, and nothing else — never your hub
folder, your projects, or a file of yours. To come back later, run the
installer again from that same folder:

    python3 sync/install.py --defaults

For a fresh installation, clone this repository into a new, empty folder and
run the installer there. Keep your existing hub and brain until you have
verified the new installation.

## Licence

Code is licensed under Apache License 2.0; see LICENSE. The licence does not
grant rights to this project's trade names or wordmark beyond the attribution
uses permitted by section 6.

## Repository

https://github.com/Bill-Viking/exocortex
