# 04 · Myths vs. the code

| claim | verdict | what the code says |
|---|---|---|
| "One report cancels 468 likes" | wrong | weights multiply each viewer's *predicted probability*, not counts (`param.rs:279-307`); reports are >1000× rarer than likes; personalized |
| "Replies are worth 27× likes" | stale | reply 5.0 vs like 0.5 = 10×; 40× (20.0) only on your originals for viewers who follow you back |
| "External links get a 30-50% penalty" | not in the repo | no filter or weight penalizes URLs; `OpenLinkWeight = 0.2` is positive; URL *reputation* labels exist (bad/low-quality domains, malicious URLs); t.co is stripped before embedding, card title/description is embedded |
| "Premium / verified gets a ranking boost" | no explicit term | no verified/premium term in the scorer or shipped features; indirect: user-cred teleport share (reputation shield), and one Grox embedding renderer writes verification tier into embedded text (learned, unquantified) |
| "Early engagement velocity is rewarded" | half true | no velocity feature; the model doesn't see counts; but the index needs ≥1 like and evicts at 24 h, SimClusters halves every 8 h, and post age is an input |
| "Reply to big accounts to get in front of their followers" | not via For You | your reply is OON for their followers and removed before scoring; it reaches your followers as a conversation module (0.75×). Their reply on your original travels to *their* followers |
| "Threads are the reach format" | wrong for reach | only post 1 can leave your follower graph; the rest are replies |
| "Follower count matters" | only as a gate (for now) | not consumed by the shipped model; gates the cold-start lift (≤1,000 helps you) and the `post_unexplored` label. Since Aug 17 the mixer sends it to Phoenix; nothing reads it yet |
| "Bookmarks and profile visits are strong signals" | zero weight | `ProfileClickWeight = 0.0`; bookmark has no ranking head weight |
| "Post 10+ times a day" | diminishing | 2nd post in a viewer's pool ×0.625, 3rd ×0.4375, floor 0.25; one cold-start lift per request |
| "Video is boosted" | barely, in For You | `VqvWeight = 0.05`, only >10 s videos, only viewers under 10k followers; separate video indices exist but default For You retrieval embeds HOME only |
| "Language mismatch gets you deboosted" | no rule | only the viewer's language is a feature; post language is not; no language filter |
| "Long posts get a dwell boost" | small | 0.004 per predicted second, capped near 30 s ≈ 0.12 (a quarter of a like) |
| "I'm shadowbanned" | check | visibility filtering is label-driven and readable; Under the Hood shows your labels (accounts ≥ 1 year old) |
