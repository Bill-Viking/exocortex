"""add-root.py — add this machine's Codex folder to machine.json.

One small repair, run by hand: it names the folder the vendor's global rules
file lives in, so the entry that carries it stops saying "that root is not in
this machine's machine.json". Where the machine file IS comes from the
resolver, never from a path spelled here, so it works in both layouts and on
both operating systems.
"""
import io
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def resolver():
    beside = HERE.parent / "tools" / "exo_paths.py"
    if not beside.is_file():
        record = json.loads(io.open(str(HERE / "machine.json"), encoding="utf-8").read())
        beside = Path(record["roots"]["orchestrator"]).expanduser() / "tools" / "exo_paths.py"
    import importlib.util
    spec = importlib.util.spec_from_file_location("exo_paths", str(beside))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    path = resolver().paths(tool_file=__file__)["machine_file"]
    if path is None:
        sys.stderr.write("add-root.py: this machine has no machine.json yet.\n")
        return 2
    record = json.loads(io.open(str(path), encoding="utf-8").read())
    codex = Path(record["roots"]["home"]) / ".codex"
    record["roots"].setdefault("codex", str(codex))
    io.open(str(path), "w", encoding="utf-8", newline="\n").write(
        json.dumps(record, indent=2) + "\n")
    print("OK", record["roots"]["codex"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
