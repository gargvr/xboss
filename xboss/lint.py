"""
Draft linter: checks a post against rules derived from xai-org/x-algorithm.

Every finding says whether it comes from CODE (a rule/threshold that exists in the repo, with a file
reference), a HEURISTIC (an approximation of a classifier whose prompts are withheld), or PLATFORM
(a product limit that is not in the repo). It never claims to predict impressions.
"""
import re
from dataclasses import dataclass, asdict
from typing import List, Optional

URL_RE = re.compile(r"https?://[^\s)]+|\b[a-z0-9.-]+\.(?:com|io|ai|co|net|org|dev|app|xyz|ly|gg|me|to)(?:/[^\s)]*)?", re.I)
MENTION_RE = re.compile(r"(?<![\w@])@([A-Za-z0-9_]{1,15})")
HASHTAG_RE = re.compile(r"(?<!\w)#\w+")
THREAD_RE = re.compile(r"(^|\s)(1/|1\)|\(1/\d+\)|🧵|thread:|a thread|\[thread\])", re.I)
SHORTENERS = ("bit.ly", "t.ly", "tinyurl.com", "lnkd.in", "cutt.ly", "rb.gy", "shorturl.at", "ow.ly", "buff.ly",
              "is.gd", "rebrand.ly", "shor.by", "tiny.cc", "goo.gl", "amzn.to", "linktr.ee")
BAIT_RE = re.compile(
    r"\b(like (this )?if|rt if|retweet if|repost if|comment ['\"]?\w+['\"]? (below|if)|comment below|drop a \w+ below|"
    r"follow (me )?(for|to)|tag (a|someone|3|three|your)|smash (that|the)|turn on (my )?notifications|"
    r"like and (share|retweet|repost)|share if you|double tap|giveaway|free for the first)\b", re.I)
GENERIC_Q_RE = re.compile(r"\b(thoughts\?|agree\?|what do you think\?|am i wrong\?|who else\?)", re.I)


@dataclass
class Finding:
    level: str      # "high" | "medium" | "low"
    kind: str       # "code" | "heuristic" | "platform"
    rule: str
    message: str
    ref: Optional[str] = None

    def to_dict(self):
        return asdict(self)


def lint(text: str, *, is_reply=False, is_quote=False, is_thread: Optional[bool] = None, has_media=False,
         video_seconds: Optional[float] = None, premium=False, mentions_follow_you: Optional[bool] = None) -> List[Finding]:
    f: List[Finding] = []
    t = text or ""
    n = len(t)
    urls = URL_RE.findall(t)
    mentions = MENTION_RE.findall(t)
    hashtags = HASHTAG_RE.findall(t)
    threadish = THREAD_RE.search(t) is not None if is_thread is None else is_thread

    # ---- structure: what can travel ----
    if is_reply:
        f.append(Finding("high", "code", "reply-does-not-travel",
                         "This is a reply. Replies (and reposts) from accounts the viewer doesn't follow are removed before "
                         "scoring, so it can never reach non-followers via For You. Followers see it as a conversation module "
                         "at 0.75x. If the value is in here, publish it as an original.",
                         "home-mixer/filters/oon_retweet_reply_filter.rs:13-18; ranking_scorer.rs:773-783"))
    if threadish:
        f.append(Finding("high", "code", "thread-collapses",
                         "Looks like part of a thread. Only post 1 can leave your follower graph; parts 2..n are replies "
                         "(filtered out-of-network, 0.75x in-network, no mutual-follow reply boost, no cold-start lift), and the "
                         "whole conversation collapses to one slot per page. Put the payload in post 1, or make each part a "
                         "standalone original (a quote of your own earlier post is still an original).",
                         "oon_retweet_reply_filter.rs; dedup_conversation_filter.rs:42-49; author_cold_start.rs:138-143"))
    if is_quote:
        f.append(Finding("low", "code", "quote-is-original",
                         "Quotes count as originals: they can be retrieved out-of-network and are cold-start eligible.",
                         "phoenixRankAllCandidateProcessor.strato:437-447; author_cold_start.rs:138-143"))

    # ---- length ----
    if n > 280 and not premium:
        f.append(Finding("high", "platform", "over-280",
                         "%d characters. Without Premium the post won't send; with Premium, length only helps if it is read "
                         "(dwell weight 0.004 per predicted second, i.e. 30 s ≈ a quarter of a like)." % n,
                         "home-mixer/params/param.rs ContDwellTimeWeight"))
    elif n > 280:
        f.append(Finding("low", "code", "long-post",
                         "Long post: dwell is worth 0.004 per predicted second (30 s ≈ 0.12, a quarter of a like) and the model "
                         "sees meaning, not word count. Keep it dense.", "param.rs ContDwellTimeWeight; recsys_feature_prep.py"))

    # ---- mentions ----
    if len(mentions) >= 2:
        f.append(Finding("medium", "code", "two-plus-mentions",
                         "%d @mentions. Posts with 2+ mentions are routed to the real-time spam LLM pass (10 s after posting). "
                         "One mention is safe; two invites a classifier." % len(mentions),
                         "grox/flows/ptos/task_filter.py:38-58 (MIN_MENTION_COUNT = 2)"))
    if mentions and urls and mentions_follow_you is False:
        f.append(Finding("high", "code", "link-plus-nonfollower-mention",
                         "A link plus an @mention of someone who doesn't follow you matches a spam rule when the link's "
                         "reputation is low-quality: post label SPAM_HIGH_RECALL, hidden from non-followers.",
                         "botmaker-rules/scarecrow/…/LQ_Tweets_With_LQ_URL_Verdict_At_Mention_To_NonFollower.bot"))

    # ---- links ----
    if urls:
        f.append(Finding("low", "code", "link-present",
                         "Link detected. No filter or weight penalizes URLs (OpenLinkWeight is +0.2). But the t.co link is "
                         "stripped before the content embedding and the CARD TITLE/DESCRIPTION is what gets embedded, so the "
                         "destination page needs a meaningful title, and the post must carry its meaning without the URL.",
                         "param.rs OpenLinkWeight; phoenix/reference/mm_encoder.py:91-94, 215-249"))
        for u in urls:
            if any(s in u.lower() for s in SHORTENERS):
                f.append(Finding("high", "code", "shortener-or-redirect",
                                 "'%s' is a shortener/redirect. URL reputation rules act on the redirect chain: a LOW_QUALITY hop "
                                 "labels the post SPAM_HIGH_RECALL (hidden from non-followers); a BAD verdict labels it SPAM "
                                 "(hidden from everyone) and is applied retroactively. Link the destination directly." % u,
                                 "Tweet_Spam_High_Recall_RTF_All_Bad_URL_Sources.bot:40-46; LQ_Tweets_..._v2.bot:7-16"))
        f.append(Finding("medium", "code", "never-pin-a-bad-link",
                         "If you pin this post: a pinned post whose link is BAD or LOW_QUALITY labels your whole ACCOUNT "
                         "SpamHighRecall for a week (all posts hidden from non-followers). Only pin links to unimpeachable domains.",
                         "PinnedLowQualityOrBadUrl.bot:6-41; user_label_drops.rs:64"))

    # ---- engagement bait ----
    m = BAIT_RE.search(t)
    if m:
        f.append(Finding("high", "heuristic", "engagement-bait",
                         "'%s' reads as engagement bait. The LLM classifier labels SpamEngagementBaiting/SpamEngagementFarming "
                         "posts SpamHighRecall (hidden from non-followers) regardless of account reputation. The prompts are "
                         "withheld, so this is a phrase heuristic; rewrite the ask as a specific question." % m.group(0),
                         "grox/flows/ptos/task_write_safety_post_annotations_result_sink.py:233-247"))

    # ---- hashtags ----
    if len(hashtags) >= 3:
        f.append(Finding("low", "heuristic", "hashtag-pile",
                         "%d hashtags. No hashtag rule exists in the repo and hashtags carry no weight; three or more mostly "
                         "signals 'spam' to humans, which feeds predicted mute/not-interested (−58.8 / −43.2)." % len(hashtags),
                         "param.rs MuteAuthorWeight, NotInterestedWeight (no hashtag rule found)"))

    # ---- what the post is built for ----
    if GENERIC_Q_RE.search(t):
        f.append(Finding("medium", "heuristic", "generic-question",
                         "Ends with a generic question. Reply is weighted 5 (20 for viewers who follow you back, on originals); "
                         "a specific question a reader can answer in one line predicts replies better than 'thoughts?'.",
                         "param.rs ReplyWeight, BidirectionalFollowReplyWeightBoost; ranking_scorer.rs:180-193"))
    elif "?" not in t:
        f.append(Finding("low", "heuristic", "no-ask",
                         "No question. Not required, but the two biggest levers you control with copy are predicted replies "
                         "(5 / 20) and predicted forwards (copy-link 20, DM 5). Give people either a specific thing to answer "
                         "or a specific reason to send it to someone.",
                         "param.rs ReplyWeight, ShareViaCopyLinkWeight, ShareViaDmWeight"))

    # ---- media ----
    if video_seconds is not None and video_seconds <= 10:
        f.append(Finding("low", "code", "short-video",
                         "Video ≤ 10 s: the video-quality-view head only counts when the video is longer than 10 s "
                         "(MinVideoDurationMs 10000), and only for viewers with under 10k followers.",
                         "home-mixer/util/candidates_util.rs:19-40; param.rs MinVideoDurationMs"))
    if not has_media and not urls:
        f.append(Finding("low", "code", "no-media",
                         "Text only. There is no media multiplier, but images/video enter the content embedding (meaning) and "
                         "the photo-expand / video-open heads (0.05 each); a screenshot of the thing you're describing also "
                         "differentiates the post from same-topic text takes in the DPP reranker.",
                         "phoenix/reference/mm_encoder.py; vm-ranker/dpp.rs"))

    return f


def summarize(findings: List[Finding]) -> str:
    if not findings:
        return "no findings"
    order = {"high": 0, "medium": 1, "low": 2}
    lines = []
    for x in sorted(findings, key=lambda z: order[z.level]):
        lines.append("[%s/%s] %s: %s%s" % (x.level.upper(), x.kind, x.rule, x.message, ("  (%s)" % x.ref) if x.ref else ""))
    return "\n".join(lines)
