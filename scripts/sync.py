#!/usr/bin/env python3
"""
sync.py: extract X's For You ranking parameters from xai-org/x-algorithm into JSON, and diff them.

What it does
  1. Reads (or shallow-clones) the upstream repo.
  2. Parses every `param!(...)` in home-mixer/params/param.rs, every `pub const` in a few
     home-mixer files, and the retrieval-index retention windows in phoenix-rankall/src/config/mod.rs.
  3. Writes data/params.json, data/constants.json, data/retention_windows.json and the curated
     data/weights.json (with file:line provenance for every value).
  4. Diffs against the previously committed data and appends to CHANGELOG.md.
     Exit code 3 means "something changed" (the GitHub Action uses that to open an issue).

Usage
  python scripts/sync.py --clone                # clone upstream to a temp dir and sync
  python scripts/sync.py --source ../x-algorithm # use a local checkout
  python scripts/sync.py --source ../x-algorithm --check   # diff only, write nothing
"""
import argparse

import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
UPSTREAM = "https://github.com/xai-org/x-algorithm.git"

PARAM_FILE = "home-mixer/params/param.rs"
CONST_FILES = [
    "home-mixer/params/config.rs",
    "home-mixer/util/candidates_util.rs",
    "home-mixer/sources/simclusters_source.rs",
    "home-mixer/scorers/ranking_scorer.rs",
    "home-mixer/candidate_pipeline/phoenix_candidate_pipeline.rs",
    "thunder/config.rs",
    "vm-ranker/args.rs",
]
RETENTION_FILE = "phoenix-rankall/src/config/mod.rs"

# Curated view: which params are "the weights" and how to group them.
WEIGHT_GROUPS = {
    "positive": [
        "ShareViaCopyLinkWeight", "ReplyWeight", "QuoteWeight", "ShareViaDmWeight", "FollowAuthorWeight",
        "ShareWeight", "RetweetWeight", "FavoriteWeight", "ClickWeight", "OpenLinkWeight", "VqvWeight",
        "PhotoExpandWeight", "VideoOpenWeight", "QuotedClickWeight", "QuotedVqvWeight", "ProfileClickWeight",
        "DwellWeight", "ContDwellTimeWeight", "ContClickDwellTimeWeight", "ContActiveSecs5mResidualNormWeight",
        "PostUnexploredWeight",
    ],
    "boosts": ["BidirectionalFollowReplyWeightBoost", "BidirectionalFollowDwellWeightBoost"],
    "negative": ["ReportWeight", "MuteAuthorWeight", "NotInterestedWeight", "BlockAuthorWeight", "NotDwelledWeight"],
    "adjustments": [
        "OonWeightFactor", "TopicOonWeightFactor", "EnableOonRescoreForInNetworkRepliesRetweets",
        "AuthorDiversityDecay", "AuthorDiversityFloor", "EnableAuthorDiversity",
        "MinVideoDurationMs", "PostUnexploredWeightInNetworkOnly", "ValueModelMode",
    ],
    "cold_start": [
        "EnableViewerColdStart", "ColdStartFollowerCap", "ColdStartImpressionThreshold", "ColdStartSlotMin",
        "ColdStartSlotMax", "ColdStartMaxPostAgeSecs", "LowImpressionsMaxPositionRatio",
        "EnableColdStartThompsonSampling",
    ],
    "reranker": ["EnableVMRanker", "VMRankerDppTheta", "VMRankerDppMaxSelectedRank", "VMRankerValueModelId"],
    "sources": ["ThunderMaxResults", "PhoenixMaxResults", "EnableSimclustersSource", "EnablePhoenixSource",
                "MaxSeqLengthScoring", "MaxSeqLengthRetrieval", "EngagementSignalsMaxPerType"],
    "served_seen": ["ExcludeServedTweetIdsDuration", "ExcludeServedTweetIdsNumber", "EnableServedFilterAllRequests"],
}


# ----------------------------------------------------------------------------- helpers
def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def line_of(text, idx):
    return text.count("\n", 0, idx) + 1


def parse_rust_value(raw):
    """Best-effort conversion of a Rust literal to JSON."""
    s = raw.strip().rstrip(",").strip()
    s = s.replace("_", "") if re.fullmatch(r"[0-9_]+(\.[0-9_]+)?", s) else s
    if s in ("true", "false"):
        return s == "true"
    m = re.fullmatch(r"\"(.*)\"(?:\.to_string\(\))?", s, re.S)
    if m:
        return m.group(1)
    if re.fullmatch(r"vec!\[\s*\]", s):
        return []
    m = re.fullmatch(r"vec!\[(.*)\]", s, re.S)
    if m:
        items = [i.strip() for i in m.group(1).split(",") if i.strip()]
        return [parse_rust_value(i) for i in items]
    if re.fullmatch(r"-?[0-9]+", s):
        return int(s)
    if re.fullmatch(r"-?[0-9]*\.[0-9]+", s):
        return float(s)
    # simple numeric arithmetic like 48 * 60 * 60 (regex-validated: digits and operators only)
    if re.fullmatch(r"[0-9_\s\+\-\*/\(\)\.]+", s):
        try:
            return eval(s.replace("_", ""), {"__builtins__": {}}, {})  # noqa: S307 (validated above)
        except Exception:
            return s
    return s


def parse_params(text):
    """param!(Name, type, "key", value);"""
    out = {}
    for m in re.finditer(r"param!\(\s*([A-Za-z0-9_]+)\s*,\s*([^,]+?)\s*,\s*\"([^\"]+)\"\s*,\s*(.*?)\s*\);", text, re.S):
        name, rtype, key, raw = m.group(1), m.group(2).strip(), m.group(3), m.group(4)
        out[name] = {"key": key, "type": rtype, "value": parse_rust_value(raw), "raw": raw.strip(),
                     "file": PARAM_FILE, "line": line_of(text, m.start())}
    return out


def parse_consts(text, rel):
    out = {}
    for m in re.finditer(r"(?:pub(?:\(crate\))?\s+)?const\s+([A-Z][A-Z0-9_]*)\s*:\s*([^=]+?)\s*=\s*(.*?);", text, re.S):
        name, rtype, raw = m.group(1), m.group(2).strip(), m.group(3).strip()
        # resolve references to earlier consts in the same file (e.g. RESULT_SIZE + FEED_MODULE_SLOTS)
        expr = raw
        for k, v in out.items():
            if isinstance(v["value"], (int, float)):
                expr = re.sub(r"\b%s\b" % re.escape(k), str(v["value"]), expr)
        val = parse_rust_value(expr)
        out[name] = {"type": rtype, "value": val, "raw": raw, "file": rel, "line": line_of(text, m.start())}
    return out


def parse_retention(text):
    """WindowConfig::new("1fav", 24) inside window_configs()."""
    out = []
    section = None
    for m in re.finditer(r"Self::([A-Za-z]+)\s*=>\s*vec!\[|WindowConfig::new\(\"([a-z_0-9]+)\",\s*([0-9\*\s]+)\)", text):
        if m.group(1):
            section = m.group(1)
            continue
        hours = eval(m.group(3).replace(" ", ""), {"__builtins__": {}}, {})
        out.append({"index": section, "name": m.group(2), "retention_hours": hours,
                    "window_name": "%s_%dday" % (m.group(2), hours // 24) if hours % 24 == 0 else "%s_%dh" % (m.group(2), hours),
                    "file": RETENTION_FILE, "line": line_of(text, m.start())})
    return out


def upstream_meta(src):
    def git(*a):
        return subprocess.run(["git", "-C", src] + list(a), capture_output=True, text=True).stdout.strip()
    sha = git("rev-parse", "--short", "HEAD")
    date = git("log", "-1", "--format=%cs")
    return {"commit": sha or None, "commit_date": date or None}


def curated_weights(params):
    view = {}
    for group, names in WEIGHT_GROUPS.items():
        view[group] = {}
        for n in names:
            if n in params:
                p = params[n]
                view[group][n] = {"value": p["value"], "key": p["key"], "ref": "%s:%d" % (p["file"], p["line"])}
    return view


def flatten(d, prefix=""):
    """{name: value} for diffing (only values)."""
    out = {}
    if isinstance(d, dict):
        for k, v in d.items():
            if isinstance(v, dict) and "value" in v and ("key" in v or "type" in v or "ref" in v):
                out[prefix + k] = v["value"]
            elif isinstance(v, dict):
                out.update(flatten(v, prefix + k + "."))
    return out


def diff_values(old, new):
    changes = []
    for k in sorted(set(old) | set(new)):
        if k not in old:
            changes.append(("added", k, None, new[k]))
        elif k not in new:
            changes.append(("removed", k, old[k], None))
        elif old[k] != new[k]:
            changes.append(("changed", k, old[k], new[k]))
    return changes


def load_json(path):
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def dump_json(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False, sort_keys=False)
        f.write("\n")


# ----------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", help="path to a local xai-org/x-algorithm checkout")
    ap.add_argument("--clone", action="store_true", help="shallow-clone upstream into a temp dir")
    ap.add_argument("--check", action="store_true", help="diff only; do not write files")
    args = ap.parse_args()

    tmp = None
    src = args.source
    if args.clone or not src:
        tmp = tempfile.mkdtemp(prefix="x-algorithm-")
        subprocess.run(["git", "clone", "--depth", "1", "--quiet", UPSTREAM, tmp], check=True)
        src = tmp
    try:
        param_text = read(os.path.join(src, PARAM_FILE))
        params = parse_params(param_text)
        hdr = re.search(r"last sync\s+([0-9T:\-Z]+)", param_text)
        consts = {}
        for rel in CONST_FILES:
            p = os.path.join(src, rel)
            if os.path.exists(p):
                consts[rel] = parse_consts(read(p), rel)
        retention = parse_retention(read(os.path.join(src, RETENTION_FILE)))
        meta = upstream_meta(src)
        meta.update({"upstream": "https://github.com/xai-org/x-algorithm",
                     "param_rs_last_sync": hdr.group(1) if hdr else None,
                     "extracted_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")})

        new_params = {"meta": meta, "params": params}
        new_consts = {"meta": meta, "constants": consts}
        new_ret = {"meta": meta, "windows": retention}
        new_weights = {"meta": meta, "note": ("Each weight multiplies the viewer's PREDICTED PROBABILITY of that action "
                                              "(or a predicted continuous value such as dwell seconds); weights do not "
                                              "multiply raw engagement counts. See knowledge/01-scoring.md."),
                       "groups": curated_weights(params)}

        old_params = load_json(os.path.join(DATA, "params.json"))
        old_consts = load_json(os.path.join(DATA, "constants.json"))
        old_ret = load_json(os.path.join(DATA, "retention_windows.json"))

        changes = []
        if old_params:
            changes += [("param",) + c for c in diff_values(flatten(old_params["params"]), flatten(params))]
        if old_consts:
            oldf = {}
            for rel, d in old_consts["constants"].items():
                oldf.update(flatten(d, rel + "::"))
            newf = {}
            for rel, d in consts.items():
                newf.update(flatten(d, rel + "::"))
            changes += [("const",) + c for c in diff_values(oldf, newf)]
        if old_ret:
            oldw = {"%s/%s" % (w["index"], w["window_name"]): w["retention_hours"] for w in old_ret["windows"]}
            neww = {"%s/%s" % (w["index"], w["window_name"]): w["retention_hours"] for w in retention}
            changes += [("retention",) + c for c in diff_values(oldw, neww)]

        first_run = old_params is None
        print("upstream %(commit)s (%(commit_date)s), param.rs last sync %(param_rs_last_sync)s" % meta)
        print("params: %d  const files: %d  retention windows: %d" % (len(params), len(consts), len(retention)))
        if first_run:
            print("first run: no previous data to diff against")
        elif not changes:
            print("no changes")
        else:
            print("%d change(s):" % len(changes))
            for kind, what, key, old, new in changes:
                print("  [%s] %s %s: %r -> %r" % (kind, what, key, old, new))

        if args.check:
            return 3 if changes else 0
        if not first_run and not changes:
            print("data unchanged; nothing written")
            return 0

        os.makedirs(DATA, exist_ok=True)
        dump_json(os.path.join(DATA, "params.json"), new_params)
        dump_json(os.path.join(DATA, "constants.json"), new_consts)
        dump_json(os.path.join(DATA, "retention_windows.json"), new_ret)
        dump_json(os.path.join(DATA, "weights.json"), new_weights)

        if changes:
            entry = ["## %s · upstream %s (%s) · param.rs sync %s" % (
                meta["extracted_at"][:10], meta["commit"], meta["commit_date"], meta["param_rs_last_sync"]), ""]
            for kind, what, key, old, new in changes:
                if what == "changed":
                    entry.append("- **%s** `%s`: `%r` → `%r`" % (kind, key, old, new))
                elif what == "added":
                    entry.append("- **%s added** `%s` = `%r`" % (kind, key, new))
                else:
                    entry.append("- **%s removed** `%s` (was `%r`)" % (kind, key, old))
            entry.append("")
            cl = os.path.join(ROOT, "CHANGELOG.md")
            preamble_default = ("# Changelog\n\nEvery change to X's mirrored production parameters "
                                "(home-mixer/params/param.rs and friends), as detected by scripts/sync.py. "
                                "Newest first.\n\n")
            existing = read(cl) if os.path.exists(cl) else preamble_default
            idx = existing.find("\n## ")
            preamble, entries = (existing, "") if idx < 0 else (existing[:idx + 1], existing[idx + 1:])
            with open(cl, "w", encoding="utf-8") as f:
                f.write(preamble.rstrip("\n") + "\n\n" + "\n".join(entry) + "\n" + entries.lstrip("\n"))
            with open(os.path.join(DATA, "last_change.md"), "w", encoding="utf-8") as f:
                f.write("\n".join(entry) + "\n")
            return 3
        return 0
    finally:
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
