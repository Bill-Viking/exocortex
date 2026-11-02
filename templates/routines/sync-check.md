<!-- A starter routine, shipped with the program. install.py copies it into
     your own routines/ folder the first time, and never touches it again:
     from then on it is yours to edit. name = `sync-check` -->
---
name: sync-check
description: Once a day, say in one line whether this machine's brain sync is current, and name the one thing to do if it is not.
model: sonnet
schedule: 0 8 * * *
---

Run the real clock (date) and say the day and time in one line.

Then, in the hub folder, run:

    python3 sync/sync.py status

Read only the GIT block and the DRIFT block. Answer in at most four lines:

1. whether this machine is ahead of, behind, or level with the brain remote;
2. how many files would cross in each direction;
3. any CONFLICT line, by file name;
4. the one command to run if something is owed, or `nothing owed` when it is not.

Write the same four lines to `watchers/SYNC-CHECK-run.md`, newest first, and
stop. Change no other file.
