# 01 · How a post is scored (RankingScorer)

Source: `home-mixer/scorers/ranking_scorer.rs`, weights in `home-mixer/params/param.rs` (mirrored production defaults; the current values are in `data/weights.json`, auto-synced).

## The formula

```
score(viewer, post) = Σ weight_i × P_viewer(action_i | post)      // ranking_scorer.rs:451-458
```

Phoenix (a transformer) reads the viewer's last ~1,000 actions and outputs, for each candidate post, a probability for each action. `RankingScorer` combines them with fixed weights. **Weights multiply predicted probabilities, not raw counts.** X added a comment (param.rs:279-307) because "one report cancels 468 likes" is a misreading: reports are more than 1000× rarer than likes, so −234 is what it takes for the prediction to matter at all, and predictions are personalized (reports from one crowd mostly lower predictions for similar viewers).

## Weights (production, synced 2026-08-12)

| head | weight | note |
|---|---|---|
| share via copy link | **20.0** | largest positive weight |
| reply | 5.0 | **+15.0 → 20.0** on your *originals* for viewers who follow you and whom you follow back (`ranking_scorer.rs:180-193`) |
| quote | 5.0 | |
| share via DM | 5.0 | |
| follow author | 4.0 | P(viewer follows you because of this post) |
| share (share sheet) | 2.0 | |
| repost | 1.0 | |
| like | 0.5 | |
| click (open post) | 0.4 | |
| open link | 0.2 | positive; no link penalty exists |
| video quality view | 0.05 | only if video > 10 s **and viewer has < 10k followers** (`util/candidates_util.rs:19-40`) |
| photo expand · video open · quoted click | 0.05 | |
| dwell time (continuous) | 0.004 / predicted second | capped near 30 s ≈ 0.12 |
| post unexplored | 0.02 | in-network only |
| profile click · dwell (binary) · quoted VQV | 0.0 | |
| **report** | **−234.0** | |
| mute author | −58.8 | bigger than block |
| not interested | −43.2 | |
| block author | −31.2 | |
| not dwelled | −0.02 | fires constantly |

Bookmarks have no ranking weight (they only seed SimClusters retrieval as a viewer signal).

## Net-negative squash

`offset_score` (`ranking_scorer.rs:554-562`, constants in `params/config.rs`): if the sum is negative, `(score + 367.22) / 410.54 × 0.001`; otherwise `score + 0.001`. A post a viewer is predicted to mute or report is placed beneath every net-positive post, not "ranked lower".

## Then, in order (`RankingScorer::score`)

1. **Cold-start lift** (`scorers/author_cold_start.rs`): one eligible post per request is raised to the score at slot 15/16. Eligible = original (not reply/repost) + author ≤ 1,000 followers + post < 1,000 views + already inside the top 85% of the pool + (treatment arm) < 24 h old. Highest-scoring eligible wins.
2. **Author diversity** (`ranking_scorer.rs:643-645`): the k-th post from the same author in the pool is multiplied by `(1 − 0.25) × 0.5^k + 0.25` → 1.0, 0.625, 0.4375, 0.344, … floor 0.25.
3. **Out-of-network factor** 0.75 for posts from authors the viewer doesn't follow, **and for replies/reposts from authors the viewer does follow** (`EnableOonRescoreForInNetworkRepliesRetweets = true`, `ranking_scorer.rs:773-783`). Topic feeds: 0.5.
4. **VMRanker / DPP** (`vm-ranker/dpp.rs`, theta 0.65): over the top 150 by score, greedily keeps ≤ 50 preferring high score and low content-embedding similarity to what it already picked; non-selected are zeroed. Near-duplicate takes lose.
5. **Cut**: top 50 → post-selection filters → 35 posts per page (`params/config.rs`).

## Practical reading

- What wins is being the post a *particular person* is predicted to reply to, quote, forward, or follow because of. Design each original for one of those.
- Mutual follows are worth 4× on replies. Follow back people who reply.
- Rage bait moves predicted mute/not-interested/report; those weights are two orders of magnitude bigger than the positives.
