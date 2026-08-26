# X Boss

**Read X's own ranking code. Let your AI read your account. Post what travels.**

X's For You algorithm, made usable. X open-sourced the code that ranks the For You feed ([xai-org/x-algorithm](https://github.com/xai-org/x-algorithm), Apache-2.0; the August 2026 release added the real production weights, filters and safety rules). This kit turns that code into things you can actually use:

- **Ask your AI to read your account.** Point Claude / ChatGPT / Cursor / Claude Code at this repo and say *"analyze my X account"*. It asks for your handle, gets your posts (a script you run in your own browser; nothing leaves your machine), and tells you, in code terms, why your posts don't travel and what to post next, drafted in your own voice.
- **The weights as data, auto-synced.** `data/weights.json` mirrors the production parameters with a `file:line` for every number; a GitHub Action re-extracts them daily and opens an issue whenever X changes one. Watch this repo to hear about it first.
- **A scorer that reproduces the ranking arithmetic**, a **draft linter** with code-derived rules, an **interactive simulator**, and a **knowledge base** with every mechanism cited.

> Nothing here predicts impressions. The model's per-viewer probabilities are not public. What the code does make clear is *which levers exist*, *what gates a post out entirely*, and *what quietly caps reach*.

## Ask your AI (60 seconds)

**Claude Code / Cursor / any agent that can read a repo**

```
git clone https://github.com/gargvr/xboss && cd xboss
```
then say: *"Use the xboss skill in this repo to analyze my X account and draft my next week of posts."* (Claude Code discovers `.claude/skills/xboss/SKILL.md` automatically.)
The agent follows [`skills/xboss/SKILL.md`](skills/xboss/SKILL.md): it asks for your handle, has you run [`scripts/collect_profile.js`](scripts/collect_profile.js) on your profile (DevTools console, copies your posts as JSON to your clipboard, local only), runs `python -m xboss analyze me.json`, explains the result against [`knowledge/`](knowledge/), and lints every draft it writes.

**Claude Desktop / MCP clients**

```
pip install "mcp[cli]"
# claude_desktop_config.json → {"mcpServers": {"xboss": {"command": "python", "args": ["/ABS/PATH/xboss/mcp/server.py"]}}}
# Claude Code: claude mcp add xboss -- python /ABS/PATH/xboss/mcp/server.py
```
Tools: `get_weights`, `score_post`, `lint_draft`, `analyze_account`, `cold_start`, `read_knowledge`.

**ChatGPT / Claude web (no repo access)**

Paste [`prompts/system_prompt.md`](prompts/system_prompt.md) into a new chat, then paste your exported posts. Same procedure, no tools.

### Rate limits and your account (read before exporting)

X throttles its own web endpoints per account in roughly 15-minute windows and, per the upstream `bdsm/` component, scores automation-like behaviour. `scripts/collect_profile.js` therefore scrolls at a human pace with random pauses, stops at ~40 posts, and performs no actions. Run it **once**, yourself, in a foreground tab. Don't let an AI agent loop it against your logged-in session, and if you see "Rate limit exceeded" or "Something went wrong", wait 15-30 minutes instead of retrying. Reading your own profile is normal use; scripted repetition is what gets throttled.

## What the account read tells you

`python -m xboss analyze me.json` prints, for example:

```
25 followers · 143 following · no Premium · joined 2026-05 · 31 posts (30 originals)
median views, originals            51        originals with zero likes    57%
median views, media originals      77        median views, text-only      40
cold-start window (≤1000 followers) yes      Under the Hood available     not yet

- Median original gets 51 views against 25 followers (2.1x): roughly the follower graph plus profile visits.
  In code terms this is a candidate-generation problem: posts that never enter the out-of-network index
  (original + safety-clean + ≥1 like, evicted at 24h) are invisible to everyone else. [phoenixRankAllCandidateProcessor.strato:437-459]
- 57% of originals got zero likes: a post with zero likes never enters the Phoenix retrieval index and builds
  no SimClusters vector (likes only, 8h half-life). The first like is the door.
- Your best originals by engagement: "I open-sourced an AI that runs a faceless Shorts channel…" (198 views, 6 likes) …
  whatever these have in common is your lane; retrieval represents a post as author-hash + content codes.
- At 25 followers you are inside the cold-start window: every For You request lifts one small-account original
  with <1000 views and <24h age to slot ~15, IF it is already a candidate for that viewer. [author_cold_start.rs]
```
…followed by a plan (lane, first-like protocol, mutual-follow graph, cadence, what to stop) with a file reference for each item.

## The weights (auto-synced)

<!-- weights:start -->
_Mirrored from upstream commit `0d3cdd8` (2026-08-25); `param.rs` header says last production sync **2026-08-25T16:20:01Z**; extracted 2026-08-26. Weights multiply the viewer's **predicted probability** of the action, not raw counts._

| action | param | weight | where |
|---|---|---|---|
| share via copy link | `ShareViaCopyLinkWeight` | **20** | `home-mixer/params/param.rs:350` |
| reply | `ReplyWeight` | **5** | `home-mixer/params/param.rs:308` |
| quote | `QuoteWeight` | **5** | `home-mixer/params/param.rs:357` |
| share via DM | `ShareViaDmWeight` | **5** | `home-mixer/params/param.rs:344` |
| follow author | `FollowAuthorWeight` | **4** | `home-mixer/params/param.rs:370` |
| share | `ShareWeight` | **2** | `home-mixer/params/param.rs:343` |
| repost | `RetweetWeight` | **1** | `home-mixer/params/param.rs:321` |
| like | `FavoriteWeight` | **0.5** | `home-mixer/params/param.rs:307` |
| click (open post) | `ClickWeight` | **0.4** | `home-mixer/params/param.rs:334` |
| open link | `OpenLinkWeight` | **0.2** | `home-mixer/params/param.rs:335` |
| video quality view (>10 s, viewer <10k followers) | `VqvWeight` | **0** | `home-mixer/params/param.rs:342` |
| photo expand | `PhotoExpandWeight` | **0.05** | `home-mixer/params/param.rs:322` |
| video open | `VideoOpenWeight` | **0.07** | `home-mixer/params/param.rs:328` |
| quoted click | `QuotedClickWeight` | **0.05** | `home-mixer/params/param.rs:358` |
| quoted video quality view | `QuotedVqvWeight` | **0** | `home-mixer/params/param.rs:364` |
| profile click | `ProfileClickWeight` | **0** | `home-mixer/params/param.rs:336` |
| dwell (binary) | `DwellWeight` | **0.05** | `home-mixer/params/param.rs:356` |
| dwell time (per predicted second) | `ContDwellTimeWeight` | **0.004** | `home-mixer/params/param.rs:400` |
| click dwell time (per second) | `ContClickDwellTimeWeight` | **0** | `home-mixer/params/param.rs:406` |
| active secs residual | `ContActiveSecs5mResidualNormWeight` | **0** | `home-mixer/params/param.rs:442` |
| post unexplored (in-network only) | `PostUnexploredWeight` | **0.02** | `home-mixer/params/param.rs:376` |
| reply boost when author and viewer follow each other (originals only) | `BidirectionalFollowReplyWeightBoost` | **15** | `home-mixer/params/param.rs:309` |
| dwell boost, mutual follow | `BidirectionalFollowDwellWeightBoost` | **0** | `home-mixer/params/param.rs:315` |
| report | `ReportWeight` | **-234** | `home-mixer/params/param.rs:467` |
| mute author | `MuteAuthorWeight` | **-58.8** | `home-mixer/params/param.rs:461` |
| not interested | `NotInterestedWeight` | **-43.2** | `home-mixer/params/param.rs:449` |
| block author | `BlockAuthorWeight` | **-31.2** | `home-mixer/params/param.rs:455` |
| not dwelled | `NotDwelledWeight` | **-0.02** | `home-mixer/params/param.rs:468` |

**After the sum:** out-of-network ×`0.75` (also applied to replies/reposts from followed accounts: `True`); author diversity decay `0.5`, floor `0.25` (2nd post ×0.625); cold-start lift for authors ≤ `1000` followers with < `1000` views and < `24`h age, to slot `15`; DPP reranker theta `0.65` over top `150`; posts older than 48h never enter.
<!-- weights:end -->

Full parameter set: [`data/params.json`](data/params.json) (189 params), [`data/constants.json`](data/constants.json), [`data/retention_windows.json`](data/retention_windows.json). Every change lands in [`CHANGELOG.md`](CHANGELOG.md) and as an issue labelled `upstream-change`.

## Ten things the code says (each cited in [`knowledge/`](knowledge/))

1. Score = Σ weight × *that viewer's predicted probability* of each action. Copy-link share 20, reply 5 (20 for mutual follows on originals), quote 5, DM share 5, follow 4, like 0.5; report −234, mute −58.8, not-interested −43.2. Weights multiply probabilities, not counts.
2. To be recommended to non-followers a post must be an **original**, pass safety filtering, and get **≥1 like**; it leaves the retrieval index at **24 h** regardless. Ranking's cap is 48 h.
3. The shipped model does **not** consume engagement counts, verified/Premium, raw text, or links; content enters as semantic IDs from a multimodal embedding. Follower count: not consumed either, but since the Aug 17 commit the mixer sends it to the model (the sync bot caught that on day one; see `CHANGELOG.md`).
4. **≤1,000 followers?** One original per request with <1,000 views and <24 h age is lifted to slot ~15, if it is already a candidate.
5. Only **post 1 of a thread** can leave your follower graph. OON replies and reposts are removed before scoring; quotes are originals.
6. Your 2nd post in a viewer's pool is ×0.625, 3rd ×0.44 (floor 0.25). Replies/reposts to your own followers are ×0.75.
7. A DPP reranker (theta 0.65) keeps ~50 of the top 150, dropping near-duplicate takes. Same topic, different angle, or skip.
8. SimClusters counts **likes only**, halves every 8 h, needs ≥8 likes to seed others: who likes you first matters more than how many.
9. No link penalty exists; URL **reputation** does: a low-quality redirect chain hides the post from non-followers; a **pinned** post with a bad link hides your **whole account** from non-followers for a week; engagement bait is labelled regardless of reputation.
10. Reputation (PageRank ≥54) is a shield against automatic spam labels, not a ranking boost. Premium has no ranking term.

Myths checked against the code: [`knowledge/04-myths.md`](knowledge/04-myths.md). Interactive simulator + full manual: [`docs/index.html`](docs/index.html) (GitHub Pages).

## CLI

```
pip install -e .            # optional; or just run python -m xboss from the repo root (no dependencies)

xboss weights                          # mirrored weights with file:line refs
xboss explain ReplyWeight              # where a parameter lives upstream (with GitHub link)
xboss score --probs '{"favorite":0.03,"reply":0.002,"share_via_copy_link":0.0005,"dwell_time_secs":6,"not_dwelled":0.6}' [--mutual --oon --k 1]
xboss lint "draft text" [--media --premium --reply --thread]
xboss analyze me.json [--csv content.csv] [--paste profile.txt] [--handle h --followers n --joined 2026-05]
xboss cold-start --followers 25 --views 40 --age-hours 3
python scripts/sync.py --clone          # re-extract from upstream; exit code 3 = something changed
python -m pytest -q
```

## Repository map

```
data/               weights.json · params.json · constants.json · retention_windows.json  (auto-synced)
xboss/             score.py (RankingScorer arithmetic) · lint.py · analyze.py · intake.py · cli.py
knowledge/          01-scoring · 02-reach · 03-suppression · 04-myths · 05-playbook   (every claim cited)
skills/xboss/      SKILL.md   the AI procedure (Claude Code skill format; also copied to ./SKILL.md)
AGENTS.md llms.txt  instructions/index for coding agents
prompts/            system_prompt.md   paste-in version
mcp/                server.py   MCP tools
scripts/            collect_profile.js (export your posts, locally) · sync.py (extract+diff) · render_readme.py
docs/               index.html   simulator + field manual (GitHub Pages)
.github/workflows/  sync.yml   daily upstream sync → commit → issue on change
```

## Honesty notes

- Values are mirrored from the upstream repo's own "production defaults" (`param.rs` header carries the sync timestamp). X runs experiments; not every live variant is in the repo.
- Withheld upstream: Grox LLM prompts, URL-reputation verdict logic, BDSM thresholds, the duplicate-text SQL, "some botmaker rules". The kit says "not in the repo" where that matters.
- The linter's engagement-bait check is a phrase heuristic standing in for a withheld LLM classifier; it is labelled `heuristic` in every finding.
- Analysis runs locally on data you exported from your own profile. The kit never logs in, posts, follows, or sends anything.

## Contributing

Issues and PRs welcome: new intake loaders (other analytics exports), better voice-matching prompts, translations of the knowledge base, corrections with a `file:line`. Run `python -m pytest -q` before opening a PR.

## License

MIT for this kit. The upstream code it reads is Apache-2.0 © X Corp / xAI; this project is not affiliated with X.
