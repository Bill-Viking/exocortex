---
name: desk
description: One board of every live session on this machine, what each is waiting for, and how to wake, relay into, or open one. Use when the owner asks what the sessions want, says "desk", "board", "wake them", "send <word> to <lane>", "open <lane>", or is lost among windows.
---

# Desk

One window is the owner's desk. Follow `{{HUB}}/laws/LAWS.md` and the
owner's private laws; `{{HUB}}` is the installed hub. The desk keeps one
board of every live session on this machine — by name, with the one word
each is waiting for — so the owner answers in that session's window instead
of hunting. After a restart or a machine switch it wakes every paused
session itself; on the owner's explicit word it relays into a session; and
it opens a lane's session on request. It never decides for the owner; it
carries.

## The board

Read `live-sessions-<machine>.json` in the hub: one record per live session,
carrying at least `title`, `mind`, `model`, `dir`, `in_hub`, `first_line`,
`last_line` and `minutes_ago`. Read the word a session is waiting for from
its `last_line` — a quoted "say X", a DO line, a plain "one word" ask; a
session with no ask reads `nothing`. Render the board as a table:

| window | lane | wants | how long |
|---|---|---|---|
| <title> | <folder or lane token> | <quoted word, or `nothing`> | <minutes_ago> |

## Wake

After a restart or a machine switch, every paused session gets one message
that wakes it where it left off; read `first_line`/`last_line` to say where
that is. The desk never restarts anything by hand, and it never sends a
wake to a session already answered this turn. The exact carrier differs by
vendor — see the roads table below.

## Relay

Send a word into an existing session only on the owner's explicit say-so,
quoted verbatim, one word per message. Where no session-message tool
reaches a paused window, the word travels as mail:
`python3 tools/mail.py --send <machine>/<lane> <target> "<text>" <action>`,
picked up at that surface's next `--read <machine>/<lane>`. Say which
window the word went to; never relay a word the owner has not given.

## Open

Open a lane's session from its opener file (`OPENER*.md`): the folder, the
title in the ACT grammar, and the one-sentence door — "read the project
status/memory first…". Before opening, check
`python3 tools/who-is-live.py --pen --lane <lane>` and
`python3 tools/claim.py --list`; a held claim means naming the holder, not
opening a second writer.

## What the desk never does

- Decide for the owner, or answer a session's question in its place.
- Relay a word the owner has not explicitly given, verbatim.
- Open a second writer on a lane another session already holds — the pen is
  a claim, checked first, never assumed free.
- Restart an app or a session by hand where a wake message will do.

## The roads, per vendor

| vendor / app | the board | wake | relay | open | proof |
|---|---|---|---|---|---|
| Claude Code (Anthropic) | the file above, plus the app's session list where a session tool exists | the app's session-message tool, one message per paused window | the same tool, on the owner's word | a one-click task chip carrying the folder and the door sentence (today); the app's start-session tool the day a build exposes it — the skill checks for the tool by name at wake and falls back to the chip | proof: a live-sessions file with five sessions → the board lists five with their words |
| Codex (OpenAI) | the same file | no session-message tool: the desk writes each paused thread a MAIL line (`to: <machine>/<lane>`) that its next turn reads (the ONBOARD ritual reads mail at every turn) | the mail road, the owner's word quoted | the door word in a new thread (the thread's title in the ACT grammar); no tool opens a thread from outside | the mail road, proven; "open" is the owner's one click — labelled so |
| Grok (xAI) | the same file, read by the Grok session reader (`tools/grok_sessions.py`) | the mail road | the mail road | the headless Grok road, proven: a session ran the whole ritual from a folder | the headless road, proven; the board and relay fixtures not yet proven |

## Say it back

Report the board first, one line per window: window, lane, wants, how long.
Never answer a session's question in its place, and never guess a word it
did not ask for. Close with the owner's move — which window to answer, or
which command to run next — stated last, in plain words.
