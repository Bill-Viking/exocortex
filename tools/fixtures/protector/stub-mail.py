#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""stub-mail.py — copied into a gate world as tools/mail.py.

It records the arguments it was given, one JSON line in <world>/mail-sent.jsonl,
and touches no INBOX and no brain. The real mail.py is never run by the gate.
"""
import io
import json
import os
import sys

WORLD = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

with io.open(os.path.join(WORLD, "mail-sent.jsonl"), "a", encoding="utf-8") as fh:
    fh.write(json.dumps(sys.argv[1:], ensure_ascii=False) + "\n")
print("sent: %s (the gate's stub — no INBOX touched)" % (sys.argv[2] if len(sys.argv) > 2 else "?"))
