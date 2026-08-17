import json
import os
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from xboss.score import Weights, score, offset_score, author_diversity_multiplier, cold_start_eligible  # noqa: E402
from xboss.lint import lint  # noqa: E402
from xboss.analyze import analyze, render_markdown  # noqa: E402
from xboss.intake import load_json, load_pasted_profile  # noqa: E402
from xboss.weights import load_weights  # noqa: E402


def test_weights_file_has_core_values():
    doc = load_weights()
    pos = doc["groups"]["positive"]
    assert pos["ShareViaCopyLinkWeight"]["value"] == 20.0
    assert pos["FavoriteWeight"]["value"] == 0.5
    assert doc["groups"]["negative"]["ReportWeight"]["value"] == -234.0
    assert doc["groups"]["boosts"]["BidirectionalFollowReplyWeightBoost"]["value"] == 15.0
    assert doc["groups"]["adjustments"]["OonWeightFactor"]["value"] == 0.75
    assert doc["groups"]["cold_start"]["ColdStartFollowerCap"]["value"] == 1000
    for name, e in pos.items():
        assert e["ref"].startswith("home-mixer/params/param.rs:")


def test_sums_match_ranking_scorer_from_params():
    W = Weights.production()
    # positive_sum and negative_sum as computed in ScoringWeights::from_params
    assert abs(W.positive_sum() - 43.32) < 1e-9
    assert abs(W.negative_sum() - 367.22) < 1e-9


def test_generic_preset_arithmetic():
    probs = {"favorite": 0.03, "reply": 0.002, "quote": 0.0005, "retweet": 0.004, "share_via_copy_link": 0.0005,
             "share_via_dm": 0.0005, "share": 0.001, "follow_author": 0.001, "click": 0.04, "dwell_time_secs": 6,
             "post_unexplored": 0.2, "not_dwelled": 0.6, "not_interested": 0.0002, "mute_author": 0.0001,
             "block_author": 0.00005, "report": 0.00002}
    r = score(probs)
    assert abs(r.positive - 0.094) < 1e-9
    assert abs(r.negative - 0.03276) < 1e-9
    assert abs(r.weighted_score - (0.094 - 0.03276 + 0.001)) < 1e-9
    assert r.diversity_multiplier == 1.0 and r.oon_multiplier == 1.0


def test_offset_squashes_negative():
    W = Weights.production()
    v = offset_score(-1.0, W)
    assert 0 < v < 0.001
    assert offset_score(0.5, W) == 0.501


def test_bidirectional_boost_only_for_originals():
    a = score({"reply": 0.01}, mutual_follow=True)
    b = score({"reply": 0.01}, mutual_follow=True, is_reply_or_repost=True)
    c = score({"reply": 0.01})
    assert abs(a.terms["reply"] - 0.01 * 20.0) < 1e-12
    assert abs(b.terms["reply"] - 0.01 * 5.0) < 1e-12
    assert abs(c.terms["reply"] - 0.01 * 5.0) < 1e-12
    assert b.oon_multiplier == 0.75          # in-network reply gets the OON factor


def test_vqv_gate():
    assert score({"vqv": 0.5}, video_over_10s=True, viewer_followers=100).terms["vqv"] == 0.5 * 0.05
    assert score({"vqv": 0.5}, video_over_10s=False).terms["vqv"] == 0.0
    assert score({"vqv": 0.5}, video_over_10s=True, viewer_followers=20000).terms["vqv"] == 0.0


def test_diversity_and_oon():
    assert author_diversity_multiplier(0) == 1.0
    assert abs(author_diversity_multiplier(1) - 0.625) < 1e-12
    assert abs(author_diversity_multiplier(2) - 0.4375) < 1e-12
    r = score({"favorite": 0.1}, in_network=False, k_th_post=1)
    assert abs(r.final_score - (0.05 + 0.001) * 0.625 * 0.75) < 1e-12


def test_cold_start():
    ok, _ = cold_start_eligible(author_followers=25, view_count=40, is_original=True, age_hours=3)
    assert ok
    ok, reasons = cold_start_eligible(author_followers=2500, view_count=40, is_original=True, age_hours=3)
    assert not ok and any("followers" in r for r in reasons)
    ok, reasons = cold_start_eligible(author_followers=25, view_count=1200, is_original=False, age_hours=30)
    assert not ok and len(reasons) == 3


def test_lint_flags():
    fs = lint("1/ a thread 🧵 like if you agree bit.ly/x @a @b thoughts?")
    rules = {f.rule for f in fs}
    assert {"thread-collapses", "shortener-or-redirect", "engagement-bait", "two-plus-mentions", "generic-question"} <= rules
    fs = lint("read the code. one thing changed how I post\n\nfirst like is the door", has_media=True)
    assert not any(f.level == "high" for f in fs)
    fs = lint("x" * 300)
    assert any(f.rule == "over-280" for f in fs)
    assert not any(f.rule == "over-280" for f in lint("x" * 300, premium=True))
    fs = lint("this is a reply", is_reply=True)
    assert any(f.rule == "reply-does-not-travel" for f in fs)


def test_analyze_and_render():
    posts = [
        {"text": "shipped a tool, screenshot inside", "date": "2026-08-01", "views": 200, "likes": 6, "replies": 1, "has_media": True},
        {"text": "no one is coding now", "date": "2026-08-02", "views": 18, "likes": 0},
        {"text": "can anyone tell me the math?", "date": "2026-08-03", "views": 45, "likes": 0, "replies": 1},
        {"text": "1/ a thread on things", "date": "2026-08-04", "views": 36, "likes": 1},
        {"text": "@a @b great takes", "date": "2026-08-05", "views": 100, "likes": 0, "reposts": 2},
    ]
    from xboss.intake import _post_defaults
    posts = [_post_defaults(p) for p in posts]
    r = analyze({"handle": "x", "followers": 25, "following": 143, "joined": "2026-05", "premium": False}, posts)
    md = render_markdown(r)
    assert "Account read: @x" in md
    assert r.cold_start_eligible_author is True
    assert r.under_the_hood_available is False
    assert any("zero likes" in f for f in r.findings)
    assert any("cold-start" in f for f in r.findings)


def test_pasted_profile_parser():
    txt = "Himanshu Garg\n@hgarg101\nFocus\nJoined May 2026\n143\nFollowing\n25\nFollowers\nPosts\nPinned\nHello world post\n1\n275\nAnother post here\n39\n"
    prof, posts = load_pasted_profile(txt)
    assert prof["followers"] == 25 and prof["following"] == 143 and prof["joined"] == "2026-05"
    assert len(posts) == 2 and posts[0]["views"] == 275 and posts[0]["pinned"] and posts[1]["views"] == 39


def test_cli_smoke():
    out = subprocess.run([sys.executable, "-m", "xboss", "weights", "--json"], cwd=ROOT, capture_output=True, text=True)
    assert out.returncode == 0 and json.loads(out.stdout)["groups"]["positive"]["FavoriteWeight"]["value"] == 0.5
    out = subprocess.run([sys.executable, "-m", "xboss", "explain", "ReplyWeight"], cwd=ROOT, capture_output=True, text=True)
    assert "param.rs" in out.stdout


def test_sync_check_against_data_is_clean():
    """The committed data must match what sync.py extracts from a checkout, if one is available next to the repo."""
    src = os.path.join(os.path.dirname(ROOT), "x-algorithm")
    if not os.path.exists(os.path.join(src, "home-mixer", "params", "param.rs")):
        pytest.skip("no local upstream checkout")
    out = subprocess.run([sys.executable, "scripts/sync.py", "--source", src, "--check"], cwd=ROOT, capture_output=True, text=True)
    assert out.returncode == 0, out.stdout
