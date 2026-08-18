# 02 · Reaching people who don't follow you (retrieval)

For You candidates come from Thunder (in-network: recent posts from accounts the viewer follows, up to 1,200), **Phoenix retrieval** (out-of-network, up to 1,000) and **SimClusters** (out-of-network, up to 800). All are scored by the same model, then OON posts get ×0.75.

## The Phoenix index has a door, and it closes at 24 hours

Production For You retrieval reads the `1fav_1day` ("HOME") index. Admission (`phoenix-rankall-strato/columns/phoenix_rank_all/phoenixRankAllCandidateProcessor.strato:437-459`; retention `phoenix-rankall/src/config/mod.rs:139-143`):

- must be an **original**: replies, reposts and community posts are skipped
- must pass visibility filtering evaluated **with no viewer** at the "home recommendations" level, and not be NSFW-annotated → any spam / NSFW / malicious-URL / do-not-amplify label on the post or account keeps it out entirely
- must have **≥ 1 like** (the fav event is processed ~2 min later; re-indexed at power-of-two like counts)
- must be **< 24 h old** (creation time); evicted at 24 h regardless of performance

Ranking's own cap is 48 h (`AgeFilter`, `MAX_POST_AGE`). Effective life for discovery: one day, front-loaded, because post age is also a model input in 60-minute buckets.

## What the model sees about a post

Shipped ranking config (`home_direct_packed`, `phoenix/xrex/models/recsys_feature_prep.py:516-724`): hashed post ID, hashed author ID, product surface, post-age bucket, viewer timezone/local hour, and **semantic IDs**: quantized codes of a multimodal embedding (Qwen3-VL) of author name+handle, the text with `t.co` links stripped, images, video frames, link-card title/description, poll choices, quoted post (`phoenix/reference/mm_encoder.py`).

**Not consumed by the shipped model:** raw text, like/repost/reply counts (`enable_engagement_counts = False`, `xrecsys.py:589`), verified/Premium status, post language, "has link"/"has media" flags, bookmarks. **Follower count, watch this one:** until the Aug 14 release the mixer didn't even send `AuthorInfo.followers` to Phoenix; the Aug 17 commit (`b089ce6`, `home-mixer/models/candidate.rs`) started sending it for originals, together with an author-NSFW bit (`SAFETY_BIT_AUTHOR_NSFW`). The Phoenix feature code is unchanged, so nothing consumes it yet; sending it usually means a model variant is being trained or tested with it. `CHANGELOG.md` will show when that flips.

Consequences: engagement counts are gates (≥1 like for the index; <1,000 views for the cold-start lift), not ranking inputs. Content enters as *meaning*, so a post has to be legibly about something; a bare URL adds nothing, the card title does.

## Retrieval two-tower

Indexed post = **hashed author ID + semantic IDs** (`recsys_two_tower_model.py:1141-1172`), trained with likes as positives and report/not-interested/block/mute/unfollow as hard negatives. A new author's hash row is untrained → retrieval leans on content; an established author's posts inherit "who likes this author". Consistency in one lane is how the author hash starts predicting anything.

## SimClusters (second door): likes only

`simclusters/simclusters_v2/summingbird/storm/TweetJob.scala`, `Configs.scala`, `home-mixer/sources/simclusters_source.rs`:

- only **likes** (`ServerTweetFav`) build a post's cluster vector; replies/quotes/reposts/bookmarks/views don't; self-likes excluded
- each like adds the liker's cluster interests, only for clusters where the liker's own interest score ≥ 0.3
- the score **halves every 8 h** without new likes; likes on posts older than 3 days are ignored; you must sit in a cluster's served top 200
- a post needs **≥ 8 likes** to get a persistent embedding and act as a seed for other viewers
- retrieval: viewer's recent engagements (≤15 per type) → cosine > 0.5 with candidate posts ≤ 48 h old
- authors flagged for adult content are dropped from this source for non-followers

Who likes you in the first hours matters more than how many.

## Aug 17 change: topic saturation is being instrumented

`ranking_scorer.rs` (Aug 17) now counts, per viewer pool, how many posts sharing your post's semantic-ID prefix (levels 1-3, i.e. same topic cluster) rank above it, plus the rank gap, and passes `sid_k1..3` / `sid_gap1..3` to the reranker (`models/candidate.rs`). The DPP already penalises near-duplicates by embedding similarity; this is an explicit same-topic count. Same news as everyone, same angle: expect it to cost more, not less.

## Threads and reposts

- Only post 1 of a thread can reach non-followers; OON replies and reposts are removed before scoring (`home-mixer/filters/oon_retweet_reply_filter.rs:13-18`). Quotes are originals and travel.
- For followers, a thread collapses to one item per conversation per page (`dedup_conversation_filter.rs:42-49`), rendered as root + ≤1 intermediate + focal.
- A repost by someone else is in-network for *their* followers (0.75×): that's how a post crosses follower graphs. Multiple reposts of the same post collapse to one per viewer.
- Their reply on your original travels to *their* followers as a conversation module. Your reply on their post does not reach their followers via For You.

## Reputation (user-cred-v2) is a shield, not a booster

Not read by home-mixer/Phoenix/SimClusters. A PageRank score ≥ 54 (`IsHighPageRankUser.df`) / ≥ 50 (enforcement) exempts you from most automatic spam/NSFW/low-quality-URL labels. Mass comes from being followed by high-mass accounts and from likes/reposts by them (7-day windows); Premium gets a uniform teleport share; alts are edge-stripped; follower count is not an input.
