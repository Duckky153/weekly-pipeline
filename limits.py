"""Stage limits from the practice export (PLAN.md section 3.5), written to limits.json.

    python3 limits.py [practice folder]

For each stage from Qualified to Order form sent: the average of whole days
(New York calendar dates) between consecutive Date entered values, over won
practice deals that pass every check and have every stage date from Qualified
to Won in order; plus 20%; rounded up, in exact fractions. The independent
recount works the same limits out on its own; both must agree before the file
is written.
"""
import json
import pathlib
import subprocess
import sys

import engine

HERE = pathlib.Path(__file__).resolve().parent


def main(argv):
    folder = pathlib.Path(argv[1]) if len(argv) > 1 else HERE / "sample" / "practice"
    mine = engine.compute_limits(engine.load(folder))
    missing = [s for s, v in mine.items() if v is None]
    if missing:
        raise SystemExit("no clean won practice deal for: " + ", ".join(missing))
    out = subprocess.run([sys.executable, str(HERE / "recount.py"), str(folder), "--print-limits"],
                         capture_output=True, text=True)
    if out.returncode != 0:
        raise SystemExit("recount failed: " + out.stderr.strip())
    theirs = json.loads(out.stdout)
    if theirs != mine:
        raise SystemExit(f"limits differ: engine {mine}, recount {theirs}")
    (HERE / "limits.json").write_text(json.dumps(mine, indent=2) + "\n")
    print("limits.json:", ", ".join(f"{s} {v} days" for s, v in mine.items()))


if __name__ == "__main__":
    main(sys.argv)
