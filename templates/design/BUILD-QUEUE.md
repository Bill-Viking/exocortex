<!-- Shipped with the program. The installer copied this file here once, when
     there was no design/BUILD-QUEUE.md, and will never touch it again: from
     now on it is yours. An update does not overwrite it. -->

# BUILD QUEUE — the one list

What this is: every improvement this system has been asked for, in one place.
One row per item, in priority order — **file order is priority**, and a row is
moved up by moving its line. Nothing is dropped: a row that goes in comes out,
and a row the tools cannot read is shown as unreadable rather than skipped.

Who edits what:

- **You, through a hub session, rule a row** — nobody else, and never a builder.
  A row may be ruled once its brief file is written, its gates are written, and the
  session has read both. A row that was only written down is not a ruled one.
- **A ruling is signed.** The status cell reads `ruled by <session title> <ISO
  timestamp>`, so the row itself says which session authorised the build and
  when. A bare `ruled` with no by-line is refused in one line and the row is
  set to `stop:`.
- **An automatic builder**, where one is enabled, writes only the `status` and
  `note` cells of the row it runs, and never any other line of this file.

A row is eligible for an automatic build only when its status is `ruled by
<session title> <ISO timestamp>`, the row's brief file exists,
the file named in its `gates` cell exists, and the brief file carries a block naming
the repository and the exact paths that build may write:

    ## RUNNER
    repo: hub
    writes: docs/example.md, tools/example.py

Status values: `seeded` · `ruled by <session title> <ISO timestamp>` ·
`running <MACHINE> <ISO timestamp>` · `done <sha>` · `stop: <one question>`.

The note cell is the row's plain-words purpose. It may open with a title
between guillemets — `«what this row is for, in a sentence»` — and everything
read from the note (the date it was heard, the words you said, a gate count) is
read after the closing mark, so a title is never mistaken for them.

`python3 tools/improvements.py --count` says how this list stands in one line;
`--write` draws `improvements.html` beside the board. Neither ever writes this
file.

| id | arc | brief | gates | model | status | note |
|---|---|---|---|---|---|---|
