"""Copies the scored material from the data helper's folder into the build, without printing any of it. Run once,
just before the scored lock.

    python3 tests/bring_scored.py <data helper folder>

- export/*.csv                        -> sample/scored/
- key.json, key-original.json         -> tests/keys/scored.json, tests/keys/scored-original.json
- the 15 deals OpenAI's model wrote   -> tests/keys/scored-openai-notes.json (their IDs only)
- other/*.csv                         -> sample/other/
- other/key.json                      -> tests/keys/other-original.json
- other/reader-check.json's corrected key -> tests/keys/other.json
- key-changes-before-lock.md          -> tests/key-changes-before-lock.md
"""
import json
import pathlib
import shutil
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent


def main(src):
    src = pathlib.Path(src)
    for name, dest in (("sample/scored", src / "export"), ("sample/other", src / "other")):
        out = ROOT / name
        if out.exists():
            raise SystemExit(f"{name} already exists; the scored material is brought once")
        out.mkdir(parents=True)
        for f in sorted(dest.glob("*.csv")):
            shutil.copyfile(f, out / f.name)
    keys = ROOT / "tests" / "keys"
    shutil.copyfile(src / "key.json", keys / "scored.json")
    original = src / "key-original.json"
    shutil.copyfile(original if original.exists() else src / "key.json", keys / "scored-original.json")
    reader = json.loads((src / "private" / "codex-15-key-for-reader.json").read_text())
    rows = reader if isinstance(reader, list) else reader.get("deals", reader)
    ids = sorted(r["deal_id"] for r in rows) if isinstance(rows, list) else sorted(rows)
    (keys / "scored-openai-notes.json").write_text(json.dumps({"note": "Deals whose notes and Next step text OpenAI's model wrote.", "deals": ids}, indent=1) + "\n")
    shutil.copyfile(src / "other" / "key.json", keys / "other-original.json")
    check = json.loads((src / "other" / "reader-check.json").read_text())
    (keys / "other.json").write_text(json.dumps(check["corrected_key"], indent=1) + "\n")
    shutil.copyfile(src / "key-changes-before-lock.md", ROOT / "tests" / "key-changes-before-lock.md")
    audit = ROOT / "tests" / "label-audit"
    audit.mkdir(exist_ok=True)
    for f, name in ((src / "private" / "audit-differences.json", "differences.json"),
                    (src / "private" / "codex-audit" / "draw.json", "draw.json"),
                    (src / "private" / "codex-15-reader.json", "openai-15-reader.json"),
                    (src / "other" / "reader-check.json", "other-40-reader.json")):
        if f.exists():
            shutil.copyfile(f, audit / name)
    print(f"brought: {len(list((ROOT / 'sample/scored').glob('*.csv')))} scored files, {len(list((ROOT / 'sample/other').glob('*.csv')))} other files, "
          f"{len(ids)} OpenAI-written deals, keys and the key-change log")


if __name__ == "__main__":
    main(sys.argv[1])
