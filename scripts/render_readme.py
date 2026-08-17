#!/usr/bin/env python3
"""Regenerate the weights table + sync badge in README.md from data/weights.json (between the markers)."""
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
README = os.path.join(ROOT, "README.md")
W = json.load(open(os.path.join(ROOT, "data", "weights.json"), encoding="utf-8"))
m = W["meta"]

LABELS = {
    "ShareViaCopyLinkWeight": "share via copy link", "ReplyWeight": "reply", "QuoteWeight": "quote",
    "ShareViaDmWeight": "share via DM", "FollowAuthorWeight": "follow author", "ShareWeight": "share",
    "RetweetWeight": "repost", "FavoriteWeight": "like", "ClickWeight": "click (open post)", "OpenLinkWeight": "open link",
    "VqvWeight": "video quality view (>10 s, viewer <10k followers)", "PhotoExpandWeight": "photo expand",
    "VideoOpenWeight": "video open", "QuotedClickWeight": "quoted click", "QuotedVqvWeight": "quoted video quality view",
    "ProfileClickWeight": "profile click", "DwellWeight": "dwell (binary)", "ContDwellTimeWeight": "dwell time (per predicted second)",
    "ContClickDwellTimeWeight": "click dwell time (per second)", "ContActiveSecs5mResidualNormWeight": "active secs residual",
    "PostUnexploredWeight": "post unexplored (in-network only)",
    "BidirectionalFollowReplyWeightBoost": "reply boost when author and viewer follow each other (originals only)",
    "BidirectionalFollowDwellWeightBoost": "dwell boost, mutual follow",
    "ReportWeight": "report", "MuteAuthorWeight": "mute author", "NotInterestedWeight": "not interested",
    "BlockAuthorWeight": "block author", "NotDwelledWeight": "not dwelled",
}


def row(name, e):
    v = e["value"]
    return "| %s | `%s` | %s | `%s` |" % (LABELS.get(name, name), name, ("**%g**" % v) if isinstance(v, (int, float)) and not isinstance(v, bool) else "`%s`" % v, e["ref"])


lines = []
lines.append("<!-- weights:start -->")
lines.append("_Mirrored from upstream commit `%s` (%s); `param.rs` header says last production sync **%s**; extracted %s. "
             "Weights multiply the viewer's **predicted probability** of the action, not raw counts._" % (
                 m.get("commit"), m.get("commit_date"), m.get("param_rs_last_sync"), m.get("extracted_at", "")[:10]))
lines.append("")
lines.append("| action | param | weight | where |")
lines.append("|---|---|---|---|")
for name, e in W["groups"]["positive"].items():
    lines.append(row(name, e))
for name, e in W["groups"]["boosts"].items():
    lines.append(row(name, e))
for name, e in W["groups"]["negative"].items():
    lines.append(row(name, e))
lines.append("")
adj = W["groups"]
lines.append("**After the sum:** out-of-network ×`%s` (also applied to replies/reposts from followed accounts: `%s`); "
             "author diversity decay `%s`, floor `%s` (2nd post ×0.625); cold-start lift for authors ≤ `%s` followers with < `%s` views "
             "and < `%s`h age, to slot `%s`; DPP reranker theta `%s` over top `%s`; posts older than 48h never enter." % (
                 adj["adjustments"]["OonWeightFactor"]["value"], adj["adjustments"]["EnableOonRescoreForInNetworkRepliesRetweets"]["value"],
                 adj["adjustments"]["AuthorDiversityDecay"]["value"], adj["adjustments"]["AuthorDiversityFloor"]["value"],
                 adj["cold_start"]["ColdStartFollowerCap"]["value"], adj["cold_start"]["ColdStartImpressionThreshold"]["value"],
                 adj["cold_start"]["ColdStartMaxPostAgeSecs"]["value"] // 3600, adj["cold_start"]["ColdStartSlotMin"]["value"],
                 adj["reranker"]["VMRankerDppTheta"]["value"], adj["reranker"]["VMRankerDppMaxSelectedRank"]["value"]))
lines.append("<!-- weights:end -->")
block = "\n".join(lines)

src = open(README, encoding="utf-8").read()
new = re.sub(r"<!-- weights:start -->.*?<!-- weights:end -->", lambda _: block, src, flags=re.S)
if new == src and "<!-- weights:start -->" not in src:
    raise SystemExit("README.md has no <!-- weights:start --> marker")
open(README, "w", encoding="utf-8").write(new)
print("README weights table updated (%s)" % m.get("param_rs_last_sync"))
