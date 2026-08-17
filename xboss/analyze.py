"""
Account read: turn a person's recent posts + profile facts into a diagnosis mapped to the code.

Input model (see xboss/intake.py for loaders):
  profile = {"handle": "…", "followers": int, "following": int, "premium": bool, "joined": "YYYY-MM",
             "bio": str, "pinned_text": str|None, "bio_url": str|None}
  posts   = [{"text": str, "date": "YYYY-MM-DD", "views": int, "likes": int, "replies": int, "reposts": int,
              "quotes": int, "bookmarks": int, "is_reply": bool, "is_repost": bool, "is_quote": bool,
              "has_media": bool, "urls": [..], "mentions": [..], "pinned": bool}, ...]

Everything here is descriptive statistics + rules from the repo. It does not predict reach.
"""
import datetime as dt
import re
import statistics
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .lint import THREAD_RE, BAIT_RE, URL_RE, MENTION_RE, HASHTAG_RE, SHORTENERS
from .score import Weights

QUESTION_RE = re.compile(r"\?")
ASK_VOID_RE = re.compile(r"\b(can anyone|does anyone|is anyone|anyone (know|using|have)|any (recs|recommendations|suggestions))\b", re.I)


def _median(xs, default=0):
    xs = [x for x in xs if x is not None]
    return statistics.median(xs) if xs else default


def _months_between(joined: Optional[str], today: dt.date) -> Optional[int]:
    if not joined:
        return None
    m = re.match(r"(\d{4})-(\d{1,2})", joined)
    if not m:
        return None
    y, mo = int(m.group(1)), int(m.group(2))
    return (today.year - y) * 12 + (today.month - mo)


@dataclass
class AccountRead:
    profile: Dict
    n_posts: int
    n_originals: int
    n_replies: int
    n_reposts: int
    n_quotes: int
    median_views: float
    median_views_originals: float
    p_zero_likes: float
    p_zero_engagement: float
    best: List[Dict]
    worst: List[Dict]
    media_median_views: Optional[float]
    text_median_views: Optional[float]
    question_share: float
    ask_void_share: float
    thread_share: float
    link_share: float
    shortener_posts: int
    multi_mention_posts: int
    hashtag_heavy_posts: int
    bait_posts: int
    cold_start_eligible_author: bool
    under_the_hood_available: Optional[bool]
    findings: List[str] = field(default_factory=list)
    plan: List[str] = field(default_factory=list)


def analyze(profile: Dict, posts: List[Dict], *, weights: Optional[Weights] = None, today: Optional[dt.date] = None) -> AccountRead:
    W = weights or Weights.production()
    today = today or dt.date.today()
    followers = int(profile.get("followers") or 0)
    posts = [p for p in posts if p.get("text") is not None]
    originals = [p for p in posts if not p.get("is_reply") and not p.get("is_repost")]
    replies = [p for p in posts if p.get("is_reply")]
    reposts = [p for p in posts if p.get("is_repost")]
    quotes = [p for p in posts if p.get("is_quote")]

    def views(p):
        return p.get("views")

    med_all = _median([views(p) for p in posts])
    med_orig = _median([views(p) for p in originals])
    zero_likes = [p for p in originals if (p.get("likes") or 0) == 0]
    zero_eng = [p for p in originals if (p.get("likes") or 0) + (p.get("replies") or 0) + (p.get("reposts") or 0) + (p.get("quotes") or 0) == 0]
    p_zero_likes = len(zero_likes) / len(originals) if originals else 0.0
    p_zero_eng = len(zero_eng) / len(originals) if originals else 0.0

    def eng(p):
        return (p.get("likes") or 0) + 2 * (p.get("replies") or 0) + 2 * (p.get("reposts") or 0) + 3 * (p.get("quotes") or 0)

    ranked = sorted([p for p in originals if not p.get("pinned")], key=lambda p: (eng(p), views(p) or 0), reverse=True)
    best = ranked[:5]
    worst = sorted([p for p in originals if not p.get("pinned")], key=lambda p: (views(p) or 0, eng(p)))[:5]

    media = [p for p in originals if p.get("has_media")]
    text_only = [p for p in originals if not p.get("has_media")]
    media_med = _median([views(p) for p in media], None) if media else None
    text_med = _median([views(p) for p in text_only], None) if text_only else None

    def has_q(p):
        return bool(QUESTION_RE.search(p["text"]))

    question_share = sum(1 for p in originals if has_q(p)) / len(originals) if originals else 0.0
    ask_void_share = sum(1 for p in originals if ASK_VOID_RE.search(p["text"])) / len(originals) if originals else 0.0
    thread_share = sum(1 for p in originals if THREAD_RE.search(p["text"])) / len(originals) if originals else 0.0
    link_posts = [p for p in originals if p.get("urls") or URL_RE.search(p["text"])]
    link_share = len(link_posts) / len(originals) if originals else 0.0
    shortener_posts = sum(1 for p in link_posts if any(s in (" ".join(p.get("urls") or []) + " " + p["text"]).lower() for s in SHORTENERS))
    multi_mention = sum(1 for p in originals if len(p.get("mentions") or MENTION_RE.findall(p["text"])) >= 2)
    hashtag_heavy = sum(1 for p in originals if len(HASHTAG_RE.findall(p["text"])) >= 3)
    bait = sum(1 for p in originals if BAIT_RE.search(p["text"]))

    cold_ok = followers <= W.w("ColdStartFollowerCap", 1000)
    months = _months_between(profile.get("joined"), today)
    uth = (months >= 12) if months is not None else None

    r = AccountRead(profile=profile, n_posts=len(posts), n_originals=len(originals), n_replies=len(replies),
                    n_reposts=len(reposts), n_quotes=len(quotes), median_views=med_all, median_views_originals=med_orig,
                    p_zero_likes=p_zero_likes, p_zero_engagement=p_zero_eng, best=best, worst=worst,
                    media_median_views=media_med, text_median_views=text_med, question_share=question_share,
                    ask_void_share=ask_void_share, thread_share=thread_share, link_share=link_share,
                    shortener_posts=shortener_posts, multi_mention_posts=multi_mention, hashtag_heavy_posts=hashtag_heavy,
                    bait_posts=bait, cold_start_eligible_author=cold_ok, under_the_hood_available=uth)

    F, P = r.findings, r.plan

    # ---- reach baseline vs follower graph ----
    if followers and med_orig:
        ratio = med_orig / followers
        if ratio <= 3:
            F.append("Median original gets %d views against %d followers (%.1fx). That is roughly the follower graph plus profile "
                     "visits: most posts never leave it. In code terms this is a candidate-generation problem, not a ranking one: "
                     "posts that never enter the out-of-network index (original + safety-clean + at least 1 like, evicted at 24h) "
                     "are invisible to everyone else. [phoenixRankAllCandidateProcessor.strato:437-459; phoenix-rankall/src/config/mod.rs:139-143]"
                     % (med_orig, followers, ratio))
        else:
            F.append("Median original gets %d views against %d followers (%.1fx): posts are already leaving the follower graph; "
                     "the work is in what they are built for (predicted replies / forwards / follows), not in getting seen at all."
                     % (med_orig, followers, ratio))
    if originals:
        F.append("%d%% of originals got zero likes and %d%% got zero engagement of any kind. A post with zero likes never enters "
                 "the Phoenix retrieval index (needs ≥1 favorite while under 24h) and builds no SimClusters vector (likes only, "
                 "8h half-life). The first like is the door. [phoenixRankAllCandidateProcessor.strato:457-459; simclusters TweetJob.scala; Configs.scala HalfLife]"
                 % (round(100 * p_zero_likes), round(100 * p_zero_eng)))

    # ---- formats ----
    if media_med is not None and text_med is not None and media and text_only:
        F.append("Media originals: median %d views (n=%d); text-only: median %d views (n=%d). There is no media multiplier in "
                 "the scorer, but images/video enter the content embedding and the photo-expand/video-open heads, and a real "
                 "artifact differentiates you in the DPP reranker. [phoenix/reference/mm_encoder.py; vm-ranker/dpp.rs]"
                 % (media_med, len(media), text_med, len(text_only)))
    if best:
        F.append("Your best originals by engagement: " + " | ".join("\"%s\" (%s views, %s likes, %s replies)" % (
            (p["text"][:70] + ("…" if len(p["text"]) > 70 else "")).replace("\n", " "), p.get("views", "?"), p.get("likes", 0), p.get("replies", 0)) for p in best[:3])
                 + ". Whatever these have in common is your lane; the retrieval index represents a post as author-hash + content "
                   "codes, so consistency is how the author hash starts predicting anything. [recsys_two_tower_model.py:1141-1172]")
    if worst:
        F.append("Your weakest originals: " + " | ".join("\"%s\" (%s views)" % (
            (p["text"][:60] + ("…" if len(p["text"]) > 60 else "")).replace("\n", " "), p.get("views", "?")) for p in worst[:3]) + ".")

    # ---- habits vs code ----
    if thread_share > 0:
        F.append("%d%% of originals look like thread parts. Only post 1 of a thread can reach non-followers; parts 2..n are "
                 "replies (filtered out-of-network, 0.75x for followers, one conversation slot per page). [oon_retweet_reply_filter.rs:13-18; dedup_conversation_filter.rs:42-49]"
                 % round(100 * thread_share))
    if replies and len(replies) > len(originals):
        F.append("You reply more than you post (%d replies vs %d originals in this sample). Replies never reach non-followers "
                 "via For You; they build mutuals (which is worth it: reply weight 5 → 20 for mutual-follow originals) but they "
                 "are not reach. [oon_retweet_reply_filter.rs; ranking_scorer.rs:180-193]" % (len(replies), len(originals)))
    if ask_void_share >= 0.2:
        F.append("%d%% of originals are 'can anyone…' asks with no payload first. A question is the right ending (reply weight 5/20) "
                 "but the post has to be a candidate before anyone can answer; give the finding first, then ask something specific."
                 % round(100 * ask_void_share))
    if question_share < 0.2 and originals:
        F.append("Only %d%% of originals contain a question. Predicted replies (5, or 20 from mutual follows) and predicted "
                 "forwards (copy-link 20, DM 5) are the two levers you control with copy; most posts here ask for neither."
                 % round(100 * question_share))
    if multi_mention:
        F.append("%d original(s) with 2+ @mentions: those are routed to the real-time spam LLM pass. Keep it to one mention. [grox/flows/ptos/task_filter.py:38]" % multi_mention)
    if shortener_posts:
        F.append("%d post(s) use link shorteners/redirects: URL-reputation rules act on the redirect chain (LOW_QUALITY hop → post hidden "
                 "from non-followers; BAD → hidden from everyone, retroactively). Link destinations directly. [Tweet_Spam_High_Recall_RTF_All_Bad_URL_Sources.bot]" % shortener_posts)
    if hashtag_heavy:
        F.append("%d post(s) with 3+ hashtags. No hashtag rule exists in the repo and hashtags carry no weight; piles read as spam to humans (predicted mute −58.8)." % hashtag_heavy)
    if bait:
        F.append("%d post(s) match engagement-bait phrasing; the LLM classifier labels those SpamHighRecall regardless of reputation. [result_sink.py:233-247]" % bait)
    if profile.get("pinned_text") is not None and originals:
        pinned = [p for p in posts if p.get("pinned")]
        if pinned:
            pv = pinned[0].get("views")
            if pv and med_orig and pv > 3 * med_orig:
                F.append("Your pinned post has %d views vs a %d median: profile visits are a real channel for you right now; pin your best "
                         "lane post, not an aphorism. (Never pin a post with a questionable link: a pinned BAD/LOW_QUALITY URL hides the whole "
                         "account from non-followers for a week. [PinnedLowQualityOrBadUrl.bot])" % (pv, med_orig))

    # ---- structural facts about this account ----
    if cold_ok:
        F.append("At %d followers you are inside the cold-start window (≤ %d): every For You request lifts one small-account original "
                 "with under %d views and under 24h age to slot ~%d, IF it is already a candidate for that viewer. Fresh originals with the "
                 "first like landed fast are how you use it. [author_cold_start.rs:138-143, 273-309]"
                 % (followers, int(W.w("ColdStartFollowerCap", 1000)), int(W.w("ColdStartImpressionThreshold", 1000)), int(W.w("ColdStartSlotMin", 15))))
    else:
        F.append("At %d followers you are past the cold-start lift (cap %d); reach now comes only from what posts are built for and from "
                 "reposts/replies by others carrying them into new follower graphs." % (followers, int(W.w("ColdStartFollowerCap", 1000))))
    if uth is False:
        F.append("Under the Hood (x.com/i/under_the_hood) needs a 365-day-old account with 10+ original posts in the month; yours is ~%d months old, "
                 "so use post analytics instead: views in the first hour above ~2x followers means the post left the graph." % (months or 0))
    elif uth:
        F.append("Under the Hood (x.com/i/under_the_hood) is available to you: check it monthly for SPAM_HIGH_RECALL / MALICIOUS_URL / NSFW rows.")
    if not profile.get("premium"):
        F.append("No Premium: 280-character limit applies. Premium buys no ranking boost in the code (only a uniform share of user-cred's "
                 "teleport, i.e. reputation shield, and analytics access).")

    # ---- plan ----
    P.append("Pick one lane and state it in the bio; 80% of originals inside it for 90 days (author hash + content codes are what retrieval matches).")
    P.append("Every original: payload first, then one specific question or one specific reason to forward it (reply 5/20, copy-link 20, DM 5).")
    P.append("First-like protocol: DM each post to 3-5 people it is genuinely for within 10 minutes; the retrieval door is ≥1 like, and it closes at 24h.")
    P.append("Follow back every real follower and leave 5-10 substantive replies a day on lane originals: mutual-follow originals get reply weight 20 instead of 5.")
    if cold_ok:
        P.append("Cadence: 2 originals/day, spaced (author diversity: your 2nd post in a viewer's pool is x0.625), so there is always a fresh <24h original with <1000 views competing for the lifted slot.")
    else:
        P.append("Cadence: 1-2 originals/day, spaced; quality of predicted actions dominates now.")
    P.append("No threads for reach (put the payload in post 1; sequel as a new original or a quote of your own post), no self-reposts, one @mention max, no shorteners, never pin a questionable link.")
    P.append("Media on originals when it adds meaning (a screenshot of the actual thing); video only counts for VQV if > 10 s.")
    P.append("Measure: time-to-first-like (< 10 min), first-hour views vs follower count (> 2x = it left the graph), replies+quotes per 1k, follows per 1k.")
    return r


def render_markdown(r: AccountRead) -> str:
    p = r.profile
    out = []
    out.append("# Account read: @%s" % p.get("handle", "?"))
    out.append("")
    out.append("**%s followers · %s following · %s%s · %d posts in sample (%d originals, %d replies, %d reposts, %d quotes)**" % (
        p.get("followers", "?"), p.get("following", "?"), "Premium" if p.get("premium") else "no Premium",
        (" · joined %s" % p["joined"]) if p.get("joined") else "", r.n_posts, r.n_originals, r.n_replies, r.n_reposts, r.n_quotes))
    out.append("")
    out.append("| metric | value |")
    out.append("|---|---|")
    out.append("| median views, originals | %s |" % r.median_views_originals)
    out.append("| originals with zero likes | %d%% |" % round(100 * r.p_zero_likes))
    out.append("| originals with zero engagement | %d%% |" % round(100 * r.p_zero_engagement))
    if r.media_median_views is not None:
        out.append("| median views, media originals | %s |" % r.media_median_views)
    if r.text_median_views is not None:
        out.append("| median views, text-only originals | %s |" % r.text_median_views)
    out.append("| originals with a question | %d%% |" % round(100 * r.question_share))
    out.append("| thread-looking originals | %d%% |" % round(100 * r.thread_share))
    out.append("| originals with a link | %d%% |" % round(100 * r.link_share))
    out.append("| cold-start window (≤1000 followers) | %s |" % ("yes" if r.cold_start_eligible_author else "no"))
    out.append("| Under the Hood available | %s |" % ({True: "yes", False: "not yet", None: "unknown"}[r.under_the_hood_available]))
    out.append("")
    out.append("## What the code says about this account")
    out.append("")
    for x in r.findings:
        out.append("- " + x)
    out.append("")
    out.append("## Plan")
    out.append("")
    for i, x in enumerate(r.plan, 1):
        out.append("%d. %s" % (i, x))
    out.append("")
    out.append("_Descriptive statistics + rules from xai-org/x-algorithm; nothing here predicts impressions. Weights and thresholds are read from data/weights.json (auto-synced)._")
    return "\n".join(out)
