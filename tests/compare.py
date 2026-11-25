"""Engine against the independent recount, deal by deal and number by number.

    python3 tests/compare.py <export folder> [--limits limits.json] [--expected expected.json] [--key key.json]

Compares the held-out reason of every deal, the tags of every deal on the push
list, the list order and every number (the card and the chart included). With
--expected (the fixture's hand-worked file) or --key (an export's answer key),
the engine's result is also compared with that third count. Exit 0 only when
everything agrees.
"""
import argparse
import json
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
import engine  # noqa: E402


def recount(folder, limits_path):
    cmd = [sys.executable, str(ROOT / "recount.py"), str(folder)]
    if limits_path:
        cmd += ["--limits", str(limits_path)]
    out = subprocess.run(cmd, capture_output=True, text=True)
    if out.returncode != 0:
        raise SystemExit(f"recount failed: {out.stderr.strip()}")
    return json.loads(out.stdout)


def diff_maps(name, a, b, label_a, label_b, problems):
    for k in sorted(set(a) | set(b), key=engine.id_key):
        if a.get(k) != b.get(k):
            problems.append(f"{name} {k}: {label_a} {a.get(k)!r}, {label_b} {b.get(k)!r}")


def diff_numbers(a, b, label_a, label_b, problems, path="numbers"):
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            diff_numbers(a.get(k), b.get(k), label_a, label_b, problems, f"{path}.{k}")
    elif a != b:
        problems.append(f"{path}: {label_a} {a!r}, {label_b} {b!r}")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("--limits")
    ap.add_argument("--expected")
    ap.add_argument("--key")
    args = ap.parse_args(argv)

    limits = json.loads(pathlib.Path(args.limits).read_text()) if args.limits else None
    result = engine.run(args.folder, limits)
    mine = engine.summary(result)
    theirs = recount(args.folder, args.limits)
    problems = []

    diff_maps("held out", mine["held_out"], theirs["held_out"], "engine", "recount", problems)
    diff_maps("push", mine["push"], theirs["push"], "engine", "recount", problems)
    if mine["push_order"] != theirs["push_order"]:
        problems.append(f"push order: engine {mine['push_order']}, recount {theirs['push_order']}")
    diff_numbers(json.loads(json.dumps(mine["numbers"])), theirs["numbers"], "engine", "recount", problems)

    if args.expected:
        exp = json.loads(pathlib.Path(args.expected).read_text())
        diff_maps("held out", mine["held_out"], exp["held_out"], "engine", "by hand", problems)
        diff_maps("push", mine["push"], exp["push"], "engine", "by hand", problems)
        if mine["push_order"] != exp["push_order"]:
            problems.append(f"push order: engine {mine['push_order']}, by hand {exp['push_order']}")
        n = result["numbers"]
        lists = {"moved_forward": n["moved_forward"]["deals"], "new_qualified": n["new_qualified"]["deals"],
                 "won": n["won"]["deals"], "lost": n["lost"]["deals"],
                 "lost_before_qualified": n["lost"]["before_qualified"], "open": n["open"]["deals"]}
        for check, ids in exp.get("checks", {}).items():
            if check.startswith("chart"):
                continue
            name, how = check.rsplit("_", 1)
            for i in ids:
                inside = i in lists[name]
                if (how == "includes") != inside:
                    problems.append(f"{name} should {'include' if how == 'includes' else 'leave out'} {i}")

    if args.key:
        key = json.loads(pathlib.Path(args.key).read_text())
        diff_maps("held out", mine["held_out"], key["held_out"], "engine", "key", problems)
        diff_maps("push", mine["push"], key["push"], "engine", "key", problems)
        e = key.get("expected", {})
        if "push_order" in e and mine["push_order"] != e["push_order"]:
            problems.append(f"push order: engine {mine['push_order']}, key {e['push_order']}")
        for k, v in e.items():
            if k == "push_order":
                continue
            if k == "limits":
                diff_numbers(result["limits"], v, "engine", "key", problems, "limits")
                continue
            if k == "chart_new_qualified":
                mine_k, v = mine["numbers"]["chart"], [w["count"] for w in v]
            elif k == "lost_before_qualified" and isinstance(v, dict):
                mine_k, v = mine["numbers"][k], v["count"]
            else:
                mine_k = mine["numbers"].get(k)
            diff_numbers(json.loads(json.dumps(mine_k)), v, "engine", "key", problems, f"numbers.{k}")

    deals = len(result["data"]["this"])
    if problems:
        print(f"{len(problems)} differences over {deals} deals:")
        for p in problems:
            print(" ", p)
        return 1
    print(f"agree: {deals} deals, {len(mine['held_out'])} held out, {len(mine['push'])} on the push list, every number")
    return 0


if __name__ == "__main__":
    sys.exit(main())
