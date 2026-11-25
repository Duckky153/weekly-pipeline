"""Locks: fingerprints of the files that must not change after a point in the build.

    python3 lock.py add <stage> <file> [<file> ...]   record the files' SHA-256 under a stage (once per stage)
    python3 lock.py check [<stage>]                   exit 1 if any locked file changed

Stages: "definitions" (before the scored export is written: the definitions, the writing and labeling rules, the
team list and the stage limits) and "scored" (before the scored read: everything that decides the page).
"""
import datetime as dt
import hashlib
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
LOCK = HERE / "lock.json"


def sha(path):
    return hashlib.sha256((HERE / path).read_bytes()).hexdigest()


def load():
    return json.loads(LOCK.read_text()) if LOCK.exists() else {"note": "Fingerprints of locked files; tests fail if one changes.", "stages": {}}


def add(stage, files):
    lock = load()
    if stage in lock["stages"]:
        raise SystemExit(f"stage {stage!r} is already locked; a lock is never rewritten")
    lock["stages"][stage] = {"locked_at": dt.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
                             "files": {f: sha(f) for f in files}}
    LOCK.write_text(json.dumps(lock, indent=1) + "\n")
    print(f"locked {len(files)} files under {stage!r}")


def check(stage=None):
    lock = load()
    bad = []
    for name, s in lock["stages"].items():
        if stage and name != stage:
            continue
        for f, h in s["files"].items():
            if not (HERE / f).exists():
                bad.append(f"{f} (missing)")
            elif sha(f) != h:
                bad.append(f)
    if bad:
        print("lock broken:", ", ".join(bad))
        return 1
    print("lock holds:", ", ".join(f"{n} ({len(s['files'])} files)" for n, s in lock["stages"].items() if not stage or n == stage) or "nothing locked yet")
    return 0


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["add"] and len(a) >= 3:
        add(a[1], a[2:])
    elif a[:1] == ["check"]:
        sys.exit(check(a[1] if len(a) > 1 else None))
    else:
        print(__doc__)
        sys.exit(2)
