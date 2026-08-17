# 03 · What suppresses a post or an account (visibility filtering + labels)

Ranking decides order; **visibility filtering** decides whether a post can be shown at all (`visibility-filtering/rules/registry.rs`). Rules run in order; first Drop wins. One set applies to everyone; a stricter set applies only to **recommendations from accounts the viewer doesn't follow**. Authors are exempt from their own labels when viewing their own posts, so you can't see it from your account.

## Applies to everyone (selected)

- Protected account → zero reach beyond followers (`ProtectedAuthorDropRule`).
- Tweet label `SPAM` (link with a BAD verdict) → dropped for everyone including followers. Policy labels (hateful conduct, violent speech, abuse, civic integrity, PDNA, bounce) likewise.
- Edited posts: only the latest version is eligible. Withheld-by-country / DMCA media drop for affected viewers.
- Sensitive-media posts (NSFW/gore labels or your own "sensitive" flag): dropped for logged-out, under-18, and no-stated-age viewers in 16 countries; interstitial for followers who haven't opted in.

## Only for non-follower recommendations (the quiet reach cap)

Post labels: `SPAM_HIGH_RECALL`, `MALICIOUS_URL`, `DO_NOT_AMPLIFY`, `NSFW_HIGH_RECALL`, `NSFW_HIGH_PRECISION`, `NSFW_TEXT`, `NSFW_CARD_IMAGE`, `GORE_AND_VIOLENCE_HIGH_PRECISION`, `FOSNR_ABUSE_INSULTS`.
Account labels hiding **all** your posts from non-followers: `SpamHighRecall`, any `Nsfw*`, `NsfwAvatarImage`, `NsfwBannerImage`, `Compromised`, `ReadOnly`, `ImpersonationHighPrecision`, `AbusiveHighRecall`, `DoNotAmplify`, plus the account-level "mark media as sensitive" setting.

Two mechanics people don't expect:
1. The retrieval index applies these rules **with no viewer** (as logged-out), so a sensitive-media or spam-labeled post never enters the out-of-network index.
2. When you reply under or quote a post, its ancestors/quoted post are evaluated with the stricter policy; if any is dropped, **your** post is dropped too, even for your followers (`home-mixer/candidate_hydrators/vf_candidate_hydrator.rs:139-178`).

## How ordinary creators get labeled (rules that are in the repo)

| behaviour | label | consequence | where |
|---|---|---|---|
| link whose redirect chain touches a LOW_QUALITY domain | post `SPAM_HIGH_RECALL` | hidden from non-followers | `LQ_Tweets_With_LQ_URL_Verdict…_v2.bot` |
| link with BAD / UNSAFE verdict | `SPAM` / `MALICIOUS_URL` | dropped for everyone / non-followers; retroactive when a domain's verdict changes | `Tweet_Spam_High_Recall_RTF_All_Bad_URL_Sources.bot`, `rtf_tweets_on_unsafe_verdict.bot` |
| **pinned** post with BAD or LOW_QUALITY link | account `SpamHighRecall`, 1 week | **all** posts hidden from non-followers | `PinnedLowQualityOrBadUrl.bot` |
| link post that @mentions a non-follower | post `SPAM_HIGH_RECALL` | hidden from non-followers | `LQ_Tweets_…_At_Mention_To_NonFollower.bot` |
| engagement bait / farming (LLM) | post `SpamHighRecall` | hidden from non-followers, even for high-reputation accounts | `grox/flows/ptos/…result_sink.py:233-247` |
| ≥ 2 @mentions | (routing) | real-time spam LLM pass on the post | `grox/flows/ptos/task_filter.py:38` |
| zero-value reply under a >30k account; LLM slop; gibberish; fast reply spam | `RiskyHighVizReply` / post `SpamHighRecall` (30 d) | | `grox/flows/reply_spam/`, `enforcement_post.yaml:39-69` |
| near-identical text repeatedly | `COPYPASTA_SPAM`; at volume account `SpamHighRecall` 30 d | | `BBQDuplicateTextProd.bot`, `enforcement_user.yaml` |
| insulting a named target (English) | `FOSNR_ABUSE_INSULTS` | hidden from non-followers | `…result_sink.py:257-267` |
| 3+ borderline-adult media in a day, or 3 of last 5 posts | account `NSFW_HIGH_PRECISION/RECALL`, 7 d | all posts hidden from non-followers, out of SimClusters and the index | `NsfwTweetMediaProcessor.bot`, `postToUserLabelRules.strato:395-426` |
| NSFW link-card image / avatar / banner | `NSFW_CARD_IMAGE` / `NsfwAvatarImage` / `NsfwBannerImage` | interstitial + hidden from non-followers / all posts hidden | `NSFW_Card_Image_URL_to_Tweet_Verdict.bot`, `user_label_drops.rs:89-100` |
| automation-like behaviour (actions < 1 s apart, follow/unfollow or like/unlike cycles, engaging with unseen posts) | BDSM scores → challenge / `SpamHighRecall` / suspension | thresholds redacted | `bdsm/`, `enforcement_user.yaml` |
| blocks/reports from strangers relative to likes from strangers | agatha ratio labels | notification filtering, search; feeds NSFW media model | `agatha/…/RateBasedLabels.scala:44-56` |

Exemptions: user-cred score ≥ 54 (≥ 50 in enforcement) skips most automatic labels; government (gray) verification is exempt in many rules; a blue check exempts nothing.

Not in the repo: what makes a URL BAD/LOW_QUALITY/UNSAFE, the Grox prompts, BDSM thresholds, the duplicate-text SQL, "some botmaker rules".

## Under the Hood

`x.com/i/under_the_hood` shows the labels on your account and posts for the prior month, if the account is ≥ 365 days old and had ≥ 10 original posts that month (`under-the-hood/strato/columns/underTheHoodReport.User.strato:15-19`). A clean report plus low reach means the cause is ranking/candidate generation, not filtering.

## The checklist

1. Only link to reputable domains; never shorteners or affiliate redirect chains.
2. Never pin a post with a link unless the domain is unimpeachable.
3. Don't @mention non-followers in a post that has a link; keep mentions ≤ 1.
4. No engagement bait ("like if", "RT to", "comment YES").
5. Don't reply under or quote accounts that look labeled (spammy, adult, mass-reported).
6. No copy-paste replies, no reposting the same text, no LLM slop at volume.
7. No rage bait or targeted insults.
8. Nothing borderline-adult in media, avatar, banner, or link-card image; don't enable "mark media as sensitive".
9. Don't automate; no bursts, no churn.
10. Don't go protected; don't rely on editing.
