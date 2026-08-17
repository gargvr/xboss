"""
The exact arithmetic of home-mixer/scorers/ranking_scorer.rs (RankingScorer), in Python.

    score = Σ weight_i × P(action_i)          # compute_weighted_parts
    → offset_score (net-negative posts squashed to (0, 0.001))
    → author-diversity multiplier for the k-th post by the same author
    → out-of-network factor (also applied to in-network replies/reposts)

Inputs are PREDICTED PROBABILITIES for one viewer (what Phoenix outputs), not engagement counts.
Nothing here can predict impressions; it shows which levers move the score and by how much.
"""
from dataclasses import dataclass, field
from typing import Dict, Optional

from .weights import load_weights, flat_values

NEGATIVE_SCORES_OFFSET = 0.001          # home-mixer/params/config.rs
VIEWER_FOLLOWERS_VQV_CAP = 10_000       # home-mixer/util/candidates_util.rs MAX_FOLLOWERS_THRESHOLD

# PhoenixScores field -> weight param name (positive heads)
HEADS = {
    "favorite": "FavoriteWeight",
    "reply": "ReplyWeight",
    "retweet": "RetweetWeight",
    "photo_expand": "PhotoExpandWeight",
    "video_open": "VideoOpenWeight",
    "click": "ClickWeight",
    "open_link": "OpenLinkWeight",
    "profile_click": "ProfileClickWeight",
    "vqv": "VqvWeight",
    "share": "ShareWeight",
    "share_via_dm": "ShareViaDmWeight",
    "share_via_copy_link": "ShareViaCopyLinkWeight",
    "dwell": "DwellWeight",
    "quote": "QuoteWeight",
    "quoted_click": "QuotedClickWeight",
    "quoted_vqv": "QuotedVqvWeight",
    "follow_author": "FollowAuthorWeight",
    "post_unexplored": "PostUnexploredWeight",
    "not_interested": "NotInterestedWeight",
    "block_author": "BlockAuthorWeight",
    "mute_author": "MuteAuthorWeight",
    "report": "ReportWeight",
    "not_dwelled": "NotDwelledWeight",
}
CONTINUOUS = {
    "dwell_time_secs": "ContDwellTimeWeight",
    "click_dwell_time_secs": "ContClickDwellTimeWeight",
    "active_secs_5m_residual_norm": "ContActiveSecs5mResidualNormWeight",
}


@dataclass
class Weights:
    values: Dict[str, float]

    @classmethod
    def production(cls, path=None):
        return cls(flat_values(load_weights(path)))

    def w(self, name, default=0.0):
        v = self.values.get(name, default)
        return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else default

    def flag(self, name, default=False):
        v = self.values.get(name, default)
        return bool(v)

    # ScoringWeights::from_params sums (used by offset_score)
    def positive_sum(self):
        names = ["FavoriteWeight", "ReplyWeight", "RetweetWeight", "PhotoExpandWeight", "VideoOpenWeight",
                 "ClickWeight", "OpenLinkWeight", "ProfileClickWeight", "VqvWeight", "ShareWeight",
                 "ShareViaDmWeight", "ShareViaCopyLinkWeight", "DwellWeight", "QuoteWeight",
                 "QuotedClickWeight", "QuotedVqvWeight", "FollowAuthorWeight", "PostUnexploredWeight"]
        return sum(self.w(n) for n in names)

    def negative_sum(self):
        return -sum(self.w(n) for n in ["NotInterestedWeight", "BlockAuthorWeight", "MuteAuthorWeight",
                                        "ReportWeight", "NotDwelledWeight"])


@dataclass
class ScoreBreakdown:
    terms: Dict[str, float]
    positive: float
    negative: float
    combined: float
    weighted_score: float
    diversity_multiplier: float
    oon_multiplier: float
    final_score: float
    like_equivalents: float
    notes: list = field(default_factory=list)

    def top_terms(self, n=8):
        return sorted(self.terms.items(), key=lambda kv: -abs(kv[1]))[:n]


def author_diversity_multiplier(k, decay=0.5, floor=0.25):
    """ranking_scorer.rs::diversity_multiplier: k = number of this author's posts ranked above this one."""
    return (1.0 - floor) * (decay ** k) + floor


def offset_score(combined, weights: Weights):
    """ranking_scorer.rs::offset_score"""
    total = weights.positive_sum() + weights.negative_sum()
    if total == 0.0:
        return max(combined, 0.0)
    if combined < 0.0:
        return (combined + weights.negative_sum()) / total * NEGATIVE_SCORES_OFFSET
    return combined + NEGATIVE_SCORES_OFFSET


def score(probs: Dict[str, float], *, weights: Optional[Weights] = None, mutual_follow=False,
          in_network=True, is_reply_or_repost=False, video_over_10s=False, viewer_followers=0,
          k_th_post=0, topic_feed=False) -> ScoreBreakdown:
    """
    probs: {"favorite": 0.03, "reply": 0.002, ..., "dwell_time_secs": 6, ...}: one viewer's predicted values.
    Missing heads count as 0 (same as `score.unwrap_or(0.0)` in the Rust).
    """
    W = weights or Weights.production()
    notes = []

    # ScoringWeights::bidirectional_boost_eligible: original post AND mutual follow
    reply_w = W.w("ReplyWeight") + (W.w("BidirectionalFollowReplyWeightBoost") if (mutual_follow and not is_reply_or_repost) else 0.0)
    dwell_w = W.w("DwellWeight") + (W.w("BidirectionalFollowDwellWeightBoost") if (mutual_follow and not is_reply_or_repost) else 0.0)
    if mutual_follow and not is_reply_or_repost and W.w("BidirectionalFollowReplyWeightBoost"):
        notes.append("mutual-follow original: reply weight %.1f (base %.1f + boost %.1f)" % (
            reply_w, W.w("ReplyWeight"), W.w("BidirectionalFollowReplyWeightBoost")))

    # candidates_util.rs::vqv_weight: video > MinVideoDurationMs AND viewer < 10k followers
    vqv_w = W.w("VqvWeight") if (video_over_10s and viewer_followers < VIEWER_FOLLOWERS_VQV_CAP) else 0.0
    # PostUnexploredWeightInNetworkOnly
    pu_w = W.w("PostUnexploredWeight") if (in_network or not W.flag("PostUnexploredWeightInNetworkOnly", True)) else 0.0

    per_head_weight = {h: W.w(p) for h, p in HEADS.items()}
    per_head_weight["reply"] = reply_w
    per_head_weight["dwell"] = dwell_w
    per_head_weight["vqv"] = vqv_w
    per_head_weight["post_unexplored"] = pu_w

    terms = {}
    for head, w in per_head_weight.items():
        terms[head] = float(probs.get(head, 0.0)) * w
    for head, p in CONTINUOUS.items():
        terms[head] = float(probs.get(head, 0.0)) * W.w(p)

    pos = sum(t for t in terms.values() if t >= 0)
    neg = -sum(t for t in terms.values() if t < 0)
    combined = pos - neg
    weighted = offset_score(combined, W)

    div = author_diversity_multiplier(k_th_post, W.w("AuthorDiversityDecay", 0.5), W.w("AuthorDiversityFloor", 0.25)) \
        if W.flag("EnableAuthorDiversity", True) else 1.0

    # RankingScorer::score: oon_applies: OON, or in-network reply/repost when EnableOonRescoreForInNetworkRepliesRetweets
    oon_applies = (not in_network) or (in_network and is_reply_or_repost and W.flag("EnableOonRescoreForInNetworkRepliesRetweets", True))
    oon_factor = W.w("TopicOonWeightFactor", 0.5) if topic_feed else W.w("OonWeightFactor", 0.75)
    oon_mult = oon_factor if oon_applies else 1.0
    if oon_applies:
        notes.append("out-of-network factor %.2f applied (%s)" % (
            oon_mult, "viewer does not follow author" if not in_network else "in-network reply/repost"))
    if combined < 0:
        notes.append("net negative: squashed into (0, %.3f), beneath every net-positive post" % NEGATIVE_SCORES_OFFSET)

    final = weighted * div * oon_mult
    return ScoreBreakdown(terms=terms, positive=pos, negative=neg, combined=combined, weighted_score=weighted,
                          diversity_multiplier=div, oon_multiplier=oon_mult, final_score=final,
                          like_equivalents=(final / W.w("FavoriteWeight")) if W.w("FavoriteWeight") else 0.0,
                          notes=notes)


def cold_start_eligible(*, author_followers, view_count, is_original, age_hours, weights: Optional[Weights] = None,
                        in_top_85pct=True):
    """
    home-mixer/scorers/author_cold_start.rs: can this post be the ONE lifted to slot ~15 in a request?
    Returns (eligible: bool, reasons: [str]).
    """
    W = weights or Weights.production()
    reasons = []
    if not W.flag("EnableViewerColdStart", True):
        return False, ["EnableViewerColdStart is false"]
    if not is_original:
        reasons.append("must be an original (not a reply or repost)")
    cap = W.w("ColdStartFollowerCap", 1000)
    if author_followers > cap:
        reasons.append("author has %d followers; cap is %d" % (author_followers, int(cap)))
    thr = W.w("ColdStartImpressionThreshold", 1000)
    if view_count >= thr:
        reasons.append("post has %d views; must be under %d" % (view_count, int(thr)))
    max_age = W.w("ColdStartMaxPostAgeSecs", 86400) / 3600.0
    if age_hours > max_age:
        reasons.append("post is %.1fh old; must be ≤ %.0fh (treatment arm)" % (age_hours, max_age))
    if not in_top_85pct:
        reasons.append("must already rank inside the top %.0f%% of the pool" % (W.w("LowImpressionsMaxPositionRatio", 0.85) * 100))
    return (not reasons), reasons or ["eligible: competes for the one lifted slot (~%d) per request" % int(W.w("ColdStartSlotMin", 15))]
