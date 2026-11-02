<!-- Shipped with the program. This file was created once, when there was no
     INBOX.md — by the installer, or by the first letter sent — and neither will
     touch it again: from now on it is yours. An update does not overwrite it. -->

# INBOX — cross-project findings

Any session that discovers something relevant to a DIFFERENT project drops it
here instead of touching that project's files. One dated line per finding,
under `## Waiting`:

`- YYYY-MM-DD · <target project> · <finding> · <suggested action>`

MAIL: a line meant for a LIVE session carries an address right after the date —

`- YYYY-MM-DD · to: <MACHINE>/<lane> · <target project> · <finding or paste> · <suggested action>`

one line per message, where `<MACHINE>` is a machine's name as its own
`machine.json` records it and `<lane>` is the lane's short token (a session
that speaks for the hub folder itself uses `hub`). The engine is
`tools/mail.py` — `--send TO TARGET TEXT ACTION` · `--read TO [--mark "<title>"]`
· `--watch TO [--every 150]`. A session that wants mail arms the watcher at its
wake, so each new addressed line reaches it with no human in the path; the
receiver marks delivery with `--read TO --mark "<title>"`.

A line with no `to:` is not addressed to a live session: it waits here until
someone reads this file.

Nothing under the heading is deleted: the record stays whole. A line here has
no done-marker in this version — which is why the asks screen leaves this file
alone — so a finding is closed where it lands, in the `## To do` list of the
project it names.

## Waiting
