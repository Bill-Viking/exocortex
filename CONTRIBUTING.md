# Contributing

## How

Open an issue to discuss a change, or send a pull request from your fork for a
small, clear change. Say what changed and why. Pull requests are reviewed as
patches. Accepted patches are brought into the private development tree,
checked, and credited in a publisher-made release commit; they are not merged
through GitHub's merge button.

## Before you open a pull request

Run every gate the program ships, against your own change:

    python3 tools/prove-install.py

Every gate that runs must be green. The self-check names gates skipped on
your platform; include that result with your change. A red or stopped row
names what to fix.

## Rules for anything you add

- Fixtures, examples, and test data name nobody real — invented names only.
- No personal data and no absolute home paths in any file you add.
- No vendor persona (a named AI character) in any file you add. Product
  names, such as Claude Code, Codex, Grok, or GitHub, are fine.

A scrub check reviews every accepted change before publication.
