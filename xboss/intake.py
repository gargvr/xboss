"""
Intake: get a person's posts + profile facts into the shape xboss.analyze expects.

Three paths, best first:
  1. JSON exported by scripts/collect_profile.js (run in your own browser on your profile; nothing leaves your machine)
  2. X analytics CSV export (Premium):  load_analytics_csv("account_content.csv")
  3. Pasted profile text (best effort):  load_pasted_profile("paste.txt")
"""
import csv
import io
import json
import re
from typing import Dict, List, Tuple

from .lint import URL_RE, MENTION_RE

_NUM = re.compile(r"^\s*([0-9][0-9,\.]*)\s*([KkMm]?)\s*$")


def _num(s):
    if s is None:
        return None
    if isinstance(s, (int, float)):
        return int(s)
    m = _NUM.match(str(s))
    if not m:
        return None
    v = float(m.group(1).replace(",", ""))
    mult = {"k": 1e3, "m": 1e6}.get(m.group(2).lower(), 1)
    return int(v * mult)


def _post_defaults(p: Dict) -> Dict:
    text = p.get("text") or ""
    return {
        "text": text,
        "date": p.get("date"),
        "views": _num(p.get("views")),
        "likes": _num(p.get("likes")) or 0,
        "replies": _num(p.get("replies")) or 0,
        "reposts": _num(p.get("reposts")) or 0,
        "quotes": _num(p.get("quotes")) or 0,
        "bookmarks": _num(p.get("bookmarks")) or 0,
        "is_reply": bool(p.get("is_reply")),
        "is_repost": bool(p.get("is_repost")),
        "is_quote": bool(p.get("is_quote")),
        "has_media": bool(p.get("has_media")),
        "urls": p.get("urls") or URL_RE.findall(text),
        "mentions": p.get("mentions") or MENTION_RE.findall(text),
        "pinned": bool(p.get("pinned")),
    }


def load_json(path_or_obj) -> Tuple[Dict, List[Dict]]:
    """Output of scripts/collect_profile.js: {"profile": {...}, "posts": [...]}"""
    obj = path_or_obj
    if isinstance(path_or_obj, str):
        with open(path_or_obj, encoding="utf-8") as f:
            obj = json.load(f)
    profile = dict(obj.get("profile") or {})
    for k in ("followers", "following"):
        profile[k] = _num(profile.get(k))
    posts = [_post_defaults(p) for p in obj.get("posts") or []]
    return profile, posts


def load_analytics_csv(path, profile: Dict = None) -> Tuple[Dict, List[Dict]]:
    """X analytics content export (column names vary; matched loosely)."""
    with open(path, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        return dict(profile or {}), []
    cols = {c.lower().strip(): c for c in rows[0].keys()}

    def col(*names):
        for n in names:
            for lc, orig in cols.items():
                if lc == n or lc.startswith(n):
                    return orig
        return None

    c_text = col("post text", "tweet text", "text")
    c_views = col("impressions", "views")
    c_likes = col("likes", "favorites")
    c_replies = col("replies")
    c_reposts = col("reposts", "retweets")
    c_quotes = col("quotes")
    c_book = col("bookmarks")
    c_time = col("time", "date", "created")
    posts = []
    for r in rows:
        text = (r.get(c_text) or "") if c_text else ""
        posts.append(_post_defaults({
            "text": text, "date": (r.get(c_time) or "")[:10] if c_time else None,
            "views": r.get(c_views) if c_views else None, "likes": r.get(c_likes) if c_likes else 0,
            "replies": r.get(c_replies) if c_replies else 0, "reposts": r.get(c_reposts) if c_reposts else 0,
            "quotes": r.get(c_quotes) if c_quotes else 0, "bookmarks": r.get(c_book) if c_book else 0,
            "is_reply": text.strip().startswith("@"), "is_repost": text.strip().startswith("RT @"),
        }))
    return dict(profile or {}), posts


def load_pasted_profile(path_or_text, profile: Dict = None) -> Tuple[Dict, List[Dict]]:
    """
    Best-effort parser for text copied from an X profile page. X shows a post's text followed by its
    non-zero counters (replies, reposts, likes, bookmarks, views); only the LAST number is reliably views.
    Prefer scripts/collect_profile.js when you can.
    """
    text = path_or_text
    try:
        with open(path_or_text, encoding="utf-8") as f:
            text = f.read()
    except (OSError, ValueError):
        pass
    prof = dict(profile or {})
    m = re.search(r"([0-9][0-9,\.]*[KkMm]?)\s+Following", text)
    if m and not prof.get("following"):
        prof["following"] = _num(m.group(1))
    m = re.search(r"([0-9][0-9,\.]*[KkMm]?)\s+Followers", text)
    if m and not prof.get("followers"):
        prof["followers"] = _num(m.group(1))
    m = re.search(r"Joined\s+([A-Za-z]+)\s+(\d{4})", text)
    if m and not prof.get("joined"):
        months = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6, "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12}
        prof["joined"] = "%s-%02d" % (m.group(2), months.get(m.group(1)[:3].lower(), 1))
    m = re.search(r"@([A-Za-z0-9_]{1,15})", text)
    if m and not prof.get("handle"):
        prof["handle"] = m.group(1)

    lines = [ln.rstrip() for ln in text.splitlines()]
    # posts start after the profile header; X renders a "Posts" tab label right before the timeline
    starts = [i for i, ln in enumerate(lines) if ln.strip() in ("Posts", "Posts ")]
    if starts:
        lines = lines[starts[0] + 1:]
    else:
        fol = [i for i, ln in enumerate(lines) if ln.strip().endswith("Followers")]
        if fol:
            lines = lines[fol[-1] + 1:]
    posts = []
    buf = []
    nums = []
    pinned_next = False
    for ln in lines + [""]:
        s = ln.strip()
        if s == "Pinned":
            pinned_next = True
            continue
        if _NUM.match(s) and buf:
            nums.append(_num(s))
            continue
        if nums and buf:
            body = "\n".join(buf).strip()
            body = re.sub(r"^(?:.*\n)?@[A-Za-z0-9_]+\n·?\s*\S+\n", "", body)   # drop "Name\n@handle\n·\n3h" header if present
            posts.append(_post_defaults({"text": body, "views": nums[-1], "pinned": pinned_next,
                                         "likes": nums[-2] if len(nums) >= 2 else 0}))
            buf, nums, pinned_next = [], [], False
            if s:
                buf.append(s)
            continue
        if s:
            buf.append(s)
    return prof, posts
