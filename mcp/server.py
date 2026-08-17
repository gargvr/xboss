"""
xboss MCP server: gives any MCP client (Claude Desktop, Claude Code, Cursor, …) tools to
read the mirrored weights, score a post, lint a draft, analyze an exported account, and read the knowledge base.

Install:   pip install "mcp[cli]"     (or: pip install -e ".[mcp]" from the repo root)
Run:       python mcp/server.py       (stdio transport)

Claude Desktop config (claude_desktop_config.json):
  {"mcpServers": {"xboss": {"command": "python", "args": ["/ABS/PATH/xboss/mcp/server.py"]}}}
Claude Code:   claude mcp add xboss -- python /ABS/PATH/xboss/mcp/server.py
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:  # pragma: no cover
    sys.stderr.write("The MCP server needs the `mcp` package: pip install \"mcp[cli]\"\n")
    raise

from xboss.weights import load_weights  # noqa: E402
from xboss.score import score, cold_start_eligible  # noqa: E402
from xboss.lint import lint  # noqa: E402
from xboss.intake import load_json  # noqa: E402
from xboss.analyze import analyze, render_markdown  # noqa: E402

mcp = FastMCP("xboss", instructions=(
    "Tools for reviewing X (Twitter) accounts and drafts against X's open-sourced For You ranking code. "
    "Start with get_weights or read_knowledge('05-playbook'); for a person, get their exported posts "
    "(scripts/collect_profile.js) and call analyze_account. Never predict impressions."))


@mcp.tool()
def get_weights() -> str:
    """The mirrored production weights/thresholds (auto-synced from xai-org/x-algorithm) with file:line refs."""
    return json.dumps(load_weights(), indent=2)


@mcp.tool()
def score_post(probs: dict, mutual_follow: bool = False, in_network: bool = True, is_reply_or_repost: bool = False,
               video_over_10s: bool = False, viewer_followers: int = 0, k_th_post: int = 0) -> str:
    """Run RankingScorer's exact arithmetic on one viewer's predicted probabilities, e.g.
    {"favorite":0.03,"reply":0.002,"share_via_copy_link":0.0005,"dwell_time_secs":6,"not_dwelled":0.6}."""
    r = score(probs, mutual_follow=mutual_follow, in_network=in_network, is_reply_or_repost=is_reply_or_repost,
              video_over_10s=video_over_10s, viewer_followers=viewer_followers, k_th_post=k_th_post)
    return json.dumps({"final_score": r.final_score, "weighted_score": r.weighted_score, "positive": r.positive,
                       "negative": r.negative, "diversity_multiplier": r.diversity_multiplier,
                       "oon_multiplier": r.oon_multiplier, "like_equivalents": r.like_equivalents,
                       "top_terms": r.top_terms(10), "notes": r.notes}, indent=2)


@mcp.tool()
def lint_draft(text: str, is_reply: bool = False, is_quote: bool = False, is_thread: bool = False,
               has_media: bool = False, premium: bool = False) -> str:
    """Check a draft post against code-derived rules (threads, mentions, links, bait, length, asks)."""
    fs = lint(text, is_reply=is_reply, is_quote=is_quote, is_thread=is_thread or None, has_media=has_media, premium=premium)
    return json.dumps([f.to_dict() for f in fs], indent=2)


@mcp.tool()
def analyze_account(export_json_path: str = "", export_json: dict = None) -> str:
    """Account read from the JSON produced by scripts/collect_profile.js (path or object). Returns markdown."""
    prof, posts = load_json(export_json_path or export_json)
    return render_markdown(analyze(prof, posts))


@mcp.tool()
def cold_start(author_followers: int, view_count: int, age_hours: float, is_original: bool = True) -> str:
    """Is a post eligible for the one lifted slot (~15) per For You request?"""
    ok, reasons = cold_start_eligible(author_followers=author_followers, view_count=view_count, is_original=is_original, age_hours=age_hours)
    return json.dumps({"eligible": ok, "reasons": reasons})


@mcp.tool()
def read_knowledge(name: str = "01-scoring") -> str:
    """Read a knowledge file: 01-scoring, 02-reach, 03-suppression, 04-myths, 05-playbook (or 'skill', 'changelog')."""
    paths = {"skill": os.path.join(ROOT, "skills", "xboss", "SKILL.md"), "changelog": os.path.join(ROOT, "CHANGELOG.md")}
    p = paths.get(name) or os.path.join(ROOT, "knowledge", name if name.endswith(".md") else name + ".md")
    if not os.path.exists(p):
        return "unknown knowledge file %r" % name
    with open(p, encoding="utf-8") as f:
        return f.read()


if __name__ == "__main__":
    mcp.run()
