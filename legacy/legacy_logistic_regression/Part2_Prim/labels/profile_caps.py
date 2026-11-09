#!/usr/bin/env python3
"""Compute BODY_CAP and URL_CAP automatically from the input file, then build the
per-row model input (id, subject, body, urls summary).

Policy (set by the author, see labeling_rules.md section 8):
  BODY_CAP = smallest length that truncates at most BODY_TRUNC_SHARE (1%) of rows,
             rounded up to the next 500, clamped to [BODY_FLOOR, BODY_CEILING].
  URL_CAP  = smallest N (unique URLs kept) such that at most URL_LOSS_SHARE (5%)
             of rows have more than N unique URLs, clamped to [URL_FLOOR, URL_CEILING].

Usage:
  python3 profile_caps.py INPUT.csv --params params.json --out model_input.jsonl
Re-running on the same file gives the same values. Compare params.json between runs;
if BODY_CAP or URL_CAP changed, re-run the gold rows and the affected rows.
"""
import argparse, csv, json, math, datetime, hashlib
from collections import Counter
from urllib.parse import urlparse

BODY_TRUNC_SHARE = 0.01
URL_LOSS_SHARE = 0.05
BODY_FLOOR, BODY_CEILING, BODY_ROUND = 2000, 20000, 500
URL_FLOOR, URL_CEILING = 5, 50
URL_CHARS = 200
MIN_ROWS_FOR_CONFIDENCE = 1000

csv.field_size_limit(10**9)


def split_urls(raw):
    out = []
    for a in (raw or "").split("\n"):
        a = a.strip().strip("\"');")
        if a:
            out.append(a)
    return out


def unique(seq):
    seen, res = set(), []
    for x in seq:
        if x not in seen:
            seen.add(x)
            res.append(x)
    return res


def smallest_cap(values, share):
    """Smallest L such that the share of values greater than L is <= share."""
    v = sorted(values)
    n = len(v)
    allowed = math.floor(n * share)          # rows allowed to exceed the cap
    idx = n - 1 - allowed                    # value at this index is the cap
    return v[max(idx, 0)] if n else 0


def round_up(x, step):
    return int(math.ceil(x / step) * step)


def load(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def compute_params(rows):
    blen = [len(r["body"] or "") for r in rows]
    ucnt = [len(unique(split_urls(r.get("urls")))) for r in rows]
    raw_body = smallest_cap(blen, BODY_TRUNC_SHARE)
    raw_url = smallest_cap(ucnt, URL_LOSS_SHARE)
    body_cap = min(max(round_up(raw_body, BODY_ROUND), BODY_FLOOR), BODY_CEILING)
    url_cap = min(max(raw_url, URL_FLOOR), URL_CEILING)
    n = len(rows)
    return {
        "computed_at": datetime.date.today().isoformat(),
        "n_rows": n,
        "low_confidence": n < MIN_ROWS_FOR_CONFIDENCE,
        "policy": {"body_trunc_share": BODY_TRUNC_SHARE, "url_loss_share": URL_LOSS_SHARE,
                   "body_floor": BODY_FLOOR, "body_ceiling": BODY_CEILING,
                   "body_round": BODY_ROUND, "url_floor": URL_FLOOR,
                   "url_ceiling": URL_CEILING, "url_chars": URL_CHARS},
        "BODY_CAP": body_cap,
        "URL_CAP": url_cap,
        "stats": {
            "body_len_max": max(blen), "body_len_p99": raw_body,
            "rows_body_over_cap": sum(1 for x in blen if x > body_cap),
            "unique_urls_max": max(ucnt), "unique_urls_cap_raw": raw_url,
            "rows_urls_over_cap": sum(1 for x in ucnt if x > url_cap),
        },
    }


def netloc(a):
    """Host part of a URL; malformed URLs (seen in spam) fall back to a simple split."""
    try:
        return urlparse(a).netloc
    except ValueError:
        rest = a.split("://", 1)[-1]
        return rest.split("/", 1)[0]


def summarize_urls(raw, cap):
    allu = split_urls(raw)
    uniq = unique(allu)
    doms = Counter(netloc(a) for a in uniq)
    out = {"urls_total": len(allu), "urls_unique": len(uniq),
           "urls": [a[:URL_CHARS] for a in uniq[:cap]], "urls_truncated": len(uniq) > cap}
    if uniq:
        d, c = doms.most_common(1)[0]
        if c / len(uniq) >= 0.6 and len(uniq) > 1:
            out["domain_summary"] = f"{c} of {len(uniq)} unique URLs on {d}"
    return out


def cut_body(body, cap):
    body = body or ""
    if len(body) <= cap:
        return body, False
    head, tail = int(cap * 0.7), cap - int(cap * 0.7)
    return (body[:head] + f" [truncated {len(body) - cap} characters] " + body[-tail:], True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("--params", default="params.json")
    ap.add_argument("--out", default="model_input.jsonl")
    a = ap.parse_args()
    rows = load(a.input)
    p = compute_params(rows)
    p["input_sha256"] = hashlib.sha256(open(a.input, "rb").read()).hexdigest()
    json.dump(p, open(a.params, "w"), indent=2)
    n_trunc = 0
    with open(a.out, "w", encoding="utf-8") as f:
        for r in rows:
            body, t = cut_body(r["body"], p["BODY_CAP"])
            n_trunc += t
            rec = {"id": r["id"], "subject": r["subject"], "body": body, "truncated": t}
            rec.update(summarize_urls(r.get("urls"), p["URL_CAP"]))
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(json.dumps(p, indent=2))
    print(f"rows truncated: {n_trunc}")
    if p["low_confidence"]:
        print("WARNING: fewer than 1000 rows; the caps are provisional until run on the full file.")


if __name__ == "__main__":
    main()
