"""xboss command line: weights · score · lint · analyze · cold-start · explain"""
import argparse
import json
import sys

from . import __version__
from .weights import load_weights, refs
from .score import Weights, score, cold_start_eligible
from .lint import lint, summarize
from .intake import load_json, load_analytics_csv, load_pasted_profile
from .analyze import analyze, render_markdown


def cmd_weights(a):
    doc = load_weights()
    if a.json:
        print(json.dumps(doc, indent=2))
        return 0
    m = doc["meta"]
    print("upstream %s (%s) · param.rs last sync %s · extracted %s" % (m.get("commit"), m.get("commit_date"), m.get("param_rs_last_sync"), m.get("extracted_at")))
    print(doc["note"])
    for group, entries in doc["groups"].items():
        print("\n[%s]" % group)
        for name, e in entries.items():
            print("  %-42s %-10s %s" % (name, json.dumps(e["value"]), e["ref"]))
    return 0


def cmd_score(a):
    probs = json.loads(a.probs) if a.probs else {}
    if a.probs_file:
        with open(a.probs_file) as f:
            probs.update(json.load(f))
    r = score(probs, mutual_follow=a.mutual, in_network=not a.oon, is_reply_or_repost=a.reply_or_repost,
              video_over_10s=a.video, viewer_followers=a.viewer_followers, k_th_post=a.k, topic_feed=a.topic)
    if a.json:
        print(json.dumps({"final_score": r.final_score, "weighted_score": r.weighted_score, "positive": r.positive,
                          "negative": r.negative, "diversity_multiplier": r.diversity_multiplier,
                          "oon_multiplier": r.oon_multiplier, "like_equivalents": r.like_equivalents,
                          "terms": r.terms, "notes": r.notes}, indent=2))
        return 0
    print("final score        %.5f   (= %.2f like-equivalents)" % (r.final_score, r.like_equivalents))
    print("weighted sum       %.5f   positive %.5f   negative %.5f" % (r.weighted_score, r.positive, r.negative))
    print("author diversity x %.3f    OON/reply-repost x %.3f" % (r.diversity_multiplier, r.oon_multiplier))
    print("top terms:")
    for k, v in r.top_terms(10):
        if v:
            print("  %-28s %+.5f" % (k, v))
    for n in r.notes:
        print("note: " + n)
    return 0


def cmd_lint(a):
    text = a.text
    if a.file:
        with open(a.file, encoding="utf-8") as f:
            text = f.read()
    if not text:
        print("give text or --file", file=sys.stderr)
        return 2
    fs = lint(text, is_reply=a.reply, is_quote=a.quote, is_thread=a.thread if a.thread else None, has_media=a.media,
              video_seconds=a.video_seconds, premium=a.premium, mentions_follow_you=(False if a.mentions_nonfollowers else None))
    if a.json:
        print(json.dumps([f.to_dict() for f in fs], indent=2))
    else:
        print("%d chars" % len(text))
        print(summarize(fs))
    return 1 if any(f.level == "high" for f in fs) else 0


def cmd_analyze(a):
    profile = {}
    for k in ("handle", "followers", "following", "joined", "bio"):
        v = getattr(a, k, None)
        if v is not None:
            profile[k] = v
    if a.premium:
        profile["premium"] = True
    if a.csv:
        prof, posts = load_analytics_csv(a.csv, profile)
    elif a.paste:
        prof, posts = load_pasted_profile(a.paste, profile)
    else:
        prof, posts = load_json(a.source)
        prof.update({k: v for k, v in profile.items() if v is not None})
    if not posts:
        print("no posts found in the input", file=sys.stderr)
        return 2
    r = analyze(prof, posts)
    if a.json:
        out = r.__dict__.copy()
        print(json.dumps(out, indent=2, default=str))
    else:
        print(render_markdown(r))
    return 0


def cmd_cold_start(a):
    ok, reasons = cold_start_eligible(author_followers=a.followers, view_count=a.views, is_original=not a.reply,
                                      age_hours=a.age_hours)
    print(("ELIGIBLE" if ok else "not eligible") + ": " + "; ".join(reasons))
    return 0 if ok else 1


def cmd_explain(a):
    doc = load_weights()
    r = refs(doc)
    name = a.name
    for group, entries in doc["groups"].items():
        if name in entries:
            e = entries[name]
            print("%s = %s   [%s]   feature switch key: %s" % (name, json.dumps(e["value"]), e["ref"], e["key"]))
            print("group: %s" % group)
            print("source: https://github.com/xai-org/x-algorithm/blob/main/%s#L%s" % tuple(e["ref"].rsplit(":", 1)))
            return 0
    print("unknown parameter %r; try `xboss weights`" % name)
    return 1


def main(argv=None):
    p = argparse.ArgumentParser(prog="xboss", description="X's For You ranking, made usable (xboss %s)" % __version__)
    sp = p.add_subparsers(dest="cmd")

    w = sp.add_parser("weights", help="print the mirrored production weights and thresholds")
    w.add_argument("--json", action="store_true")
    w.set_defaults(fn=cmd_weights)

    s = sp.add_parser("score", help="run RankingScorer's arithmetic on one viewer's predicted probabilities")
    s.add_argument("--probs", help='JSON, e.g. \'{"favorite":0.03,"reply":0.002,"share_via_copy_link":0.0005,"dwell_time_secs":6,"not_dwelled":0.6}\'')
    s.add_argument("--probs-file")
    s.add_argument("--mutual", action="store_true", help="viewer and author follow each other")
    s.add_argument("--oon", action="store_true", help="viewer does not follow the author")
    s.add_argument("--reply-or-repost", action="store_true")
    s.add_argument("--video", action="store_true", help="video longer than 10 s")
    s.add_argument("--viewer-followers", type=int, default=0)
    s.add_argument("--k", type=int, default=0, help="k-th post by this author in the pool (0 = first)")
    s.add_argument("--topic", action="store_true", help="topic feed (OON factor 0.5)")
    s.add_argument("--json", action="store_true")
    s.set_defaults(fn=cmd_score)

    l = sp.add_parser("lint", help="check a draft post against code-derived rules")
    l.add_argument("text", nargs="?")
    l.add_argument("--file")
    l.add_argument("--reply", action="store_true", help="the draft is a reply")
    l.add_argument("--quote", action="store_true", help="the draft is a quote post")
    l.add_argument("--thread", action="store_true", help="the draft is part of a thread")
    l.add_argument("--media", action="store_true")
    l.add_argument("--video-seconds", type=float)
    l.add_argument("--premium", action="store_true", help="account has Premium (long posts allowed)")
    l.add_argument("--mentions-nonfollowers", action="store_true", help="the @mentions are people who don't follow you")
    l.add_argument("--json", action="store_true")
    l.set_defaults(fn=cmd_lint)

    an = sp.add_parser("analyze", help="account read from your exported posts (see scripts/collect_profile.js)")
    an.add_argument("source", nargs="?", help="me.json from scripts/collect_profile.js")
    an.add_argument("--csv", help="X analytics content export (Premium)")
    an.add_argument("--paste", help="text file pasted from your profile page (best effort)")
    an.add_argument("--handle")
    an.add_argument("--followers", type=int)
    an.add_argument("--following", type=int)
    an.add_argument("--joined", help="YYYY-MM")
    an.add_argument("--bio")
    an.add_argument("--premium", action="store_true")
    an.add_argument("--json", action="store_true")
    an.set_defaults(fn=cmd_analyze)

    c = sp.add_parser("cold-start", help="is a post eligible for the one lifted slot per request?")
    c.add_argument("--followers", type=int, required=True)
    c.add_argument("--views", type=int, required=True)
    c.add_argument("--age-hours", type=float, required=True)
    c.add_argument("--reply", action="store_true", help="the post is a reply or repost")
    c.set_defaults(fn=cmd_cold_start)

    e = sp.add_parser("explain", help="where a parameter lives in the upstream code")
    e.add_argument("name")
    e.set_defaults(fn=cmd_explain)

    a = p.parse_args(argv)
    if not a.cmd:
        p.print_help()
        return 0
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
