"""The paid AI read of the notes check: sends fixed questions to TypeSafe's Jev and saves every answer. It picks and
gives probabilities; it writes nothing.

- The key is read only from TYPESAFE_API_KEY and is never printed or saved.
- Every request is sent twice, the second time with options and questions reversed (Jev leans to what comes first).
- Every paid attempt is logged in cache/spend.jsonl (never published), at the real token count, or at the worst case
  when there is none.
- The build's cap ($0.50) and the account-wide limit (local/private-paths.json, never published) are checked before a
  run and before every request. No paid request runs without that file.
- A saved answer is reused only for exactly the same request (its fingerprint), so the page and the README replay
  saved answers and never pay.
- A request whose high-case size is over 8,000 tokens is refused before it is sent.
- A reply that is broken (wrong model, missing or out-of-range answers) counts as "not read": no tags for that deal.
"""
import hashlib
import json
import os
import pathlib
import time
import urllib.error
import urllib.request

HERE = pathlib.Path(__file__).resolve().parent
URL = "https://api.typesafe.ai/v1/systemone"
MODEL = "jev-1.14.0"
PRICE_PER_TOKEN = 0.042 / 1_000_000
WORST_TOKENS = 64_000
MAX_REQUEST_TOKENS = 8_000
CAP = 0.50
LEDGER = HERE / "cache" / "spend.jsonl"
PRIVATE = HERE / "local" / "private-paths.json"
ANSWERS = HERE / "answers"


class Refused(RuntimeError):
    pass


def fingerprint(body):
    return hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]


def reverse(body):
    """The same request with every list of options and the order of questions reversed."""
    qs = {}
    for qid in reversed(list(body["questions"])):
        q = dict(body["questions"][qid])
        if q["type"] == "choice":
            q["criteria"] = dict(reversed(list(q["criteria"].items())))
        qs[qid] = q
    return {**body, "questions": qs}


def high_tokens(body):
    """A high-case token count for one request: one token per three characters of its JSON."""
    return len(json.dumps(body, ensure_ascii=False)) // 3 + 1


def check_reply(reply, questions):
    if reply.get("model") != MODEL:
        return f"model is {reply.get('model')!r}, not {MODEL}"
    usage = reply.get("usage") or {}
    if not isinstance(usage.get("input_tokens"), int) or usage["input_tokens"] <= 0:
        return "usage.input_tokens missing"
    answers = reply.get("answers")
    if not isinstance(answers, dict):
        return "no answers"
    for qid, q in questions.items():
        a = answers.get(qid)
        if not isinstance(a, dict):
            return f"{qid} missing"
        if q["type"] == "noul":
            p = a.get("noul")
            if not isinstance(p, (int, float)) or not 0 <= p <= 1:
                return f"{qid} is not a number between 0 and 1"
        elif a.get("choice") not in q["criteria"]:
            return f"{qid} answer {a.get('choice')!r} is not an allowed option"
    return None


# ---------------------------------------------------------------- spending

def tokens_in(path):
    path = pathlib.Path(path)
    if not path.exists():
        return 0
    total = 0
    for row in path.read_text().splitlines():
        if row.strip():
            try:
                total += int(json.loads(row).get("input_tokens") or 0)
            except ValueError:
                continue
    return total


def spent():
    return tokens_in(LEDGER) * PRICE_PER_TOKEN


def room_left():
    if not PRIVATE.exists():
        raise Refused("the account-wide limit can't be checked without local/private-paths.json; no call made")
    private = json.loads(PRIVATE.read_text())
    others = sum(tokens_in(p) for p in private["other_spend_logs"]) * PRICE_PER_TOKEN
    mine = spent()
    return min(CAP - mine, private["account_limit"] - others - mine)


def preflight(n_requests):
    room = room_left()
    worst = n_requests * WORST_TOKENS * PRICE_PER_TOKEN
    if worst > room:
        raise Refused(f"{n_requests} requests could cost ${worst:.3f}, more than the ${room:.3f} left; nothing sent")
    return room


def log_attempt(tag, rid, tokens, outcome):
    LEDGER.parent.mkdir(exist_ok=True)
    with LEDGER.open("a") as f:
        f.write(json.dumps({"t": round(time.time()), "tag": tag, "id": rid, "outcome": outcome, "model": MODEL,
                            "input_tokens": WORST_TOKENS if tokens is None else tokens, "estimated": tokens is None}) + "\n")


def post(body):
    key = os.environ.get("TYPESAFE_API_KEY")
    if not key:
        raise Refused("TYPESAFE_API_KEY is not set; run inside a login shell")
    req = urllib.request.Request(URL, data=json.dumps(body).encode(), method="POST",
                                 headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json", "User-Agent": "research-prototype/0.1"})
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read())


def ask(body, tag, rid):
    delay, attempts = 2.0, 0
    while True:
        if room_left() < WORST_TOKENS * PRICE_PER_TOKEN:
            raise Refused("stopped before a request that could cross the cap")
        attempts += 1
        try:
            reply = post(body)
            tokens = (reply.get("usage") or {}).get("input_tokens")
            log_attempt(tag, rid, tokens if isinstance(tokens, int) and tokens > 0 else None, "ok")
            return reply
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504, 529) and attempts < 5:
                log_attempt(tag, rid, None, f"retry {e.code}")
                time.sleep(delay)
                delay *= 2
                continue
            log_attempt(tag, rid, None, f"failed {e.code}")
            raise Refused(f"{rid}: the service said {e.code}")
        except (urllib.error.URLError, TimeoutError) as e:
            if attempts < 5:
                log_attempt(tag, rid, None, "retry network")
                time.sleep(delay)
                delay *= 2
                continue
            log_attempt(tag, rid, None, "failed network")
            raise Refused(f"{rid}: network: {e}")


def two_reads(body, folder, rid, tag, live):
    """Both reads of one request: from the saved answers when this exact request was asked before, else live (paid).
    A broken reply is saved as broken and returns no answers ("not read")."""
    fp = fingerprint(body)
    path = ANSWERS / folder / f"{rid}-{fp}.json"
    if path.exists():
        saved = json.loads(path.read_text())
        if saved.get("broken"):
            return None, None, {"saved": True, "fingerprint": fp, "broken": saved["broken"]}
        return saved["a"], saved["b"], {"saved": True, "fingerprint": fp}
    if not live:
        return None, None, {"saved": False, "fingerprint": fp, "missing": True}
    size = high_tokens(body)
    if size > MAX_REQUEST_TOKENS:
        raise Refused(f"{rid}: the request could be {size} tokens, over {MAX_REQUEST_TOKENS}; nothing sent")
    out = {}
    for side, b in (("a", body), ("b", reverse(body))):
        reply = ask(b, tag, f"{rid}:{side}")
        problem = check_reply(reply, b["questions"])
        if problem:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps({"request_fingerprint": fp, "model": MODEL, "broken": f"read {side}: {problem}"}, indent=1))
            return None, None, {"saved": False, "fingerprint": fp, "broken": problem}
        out[side] = {"answers": reply["answers"], "input_tokens": reply["usage"]["input_tokens"]}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"request_fingerprint": fp, "model": MODEL, "a": out["a"], "b": out["b"]}, indent=1))
    return out["a"], out["b"], {"saved": False, "fingerprint": fp}
