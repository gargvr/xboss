# AGENTS.md: instructions for coding agents working in xboss

**What this repo is.** X's For You ranking, made usable: `data/weights.json` (production weights mirrored from
xai-org/x-algorithm, auto-synced daily), a Python scorer that reproduces `home-mixer/scorers/ranking_scorer.rs`,
a draft linter, an account analyzer, a knowledge base (`knowledge/`), a browser snippet that exports a person's
own posts, and this AI layer.

**If a user asks you to help their X account or review a post:** follow `skills/xboss/SKILL.md`. Short version:
ask for the handle → get their posts (`scripts/collect_profile.js` in their browser, or `--csv` / `--paste`) →
`python -m xboss analyze me.json` → explain in code terms → draft in their voice → `python -m xboss lint` each draft.

**Commands** (no dependencies beyond Python 3.9+; `pip install -e .` gives you the `xboss` command):
```
python -m xboss weights                       # current mirrored weights with file:line refs
python -m xboss explain ReplyWeight           # where a parameter lives upstream
python -m xboss score --probs '{...}' [--mutual --oon --reply-or-repost --video --k N]
python -m xboss lint "draft text" [--media --premium --reply --thread]
python -m xboss analyze me.json [--csv file] [--paste file] [--handle h --followers n ...]
python -m xboss cold-start --followers 25 --views 40 --age-hours 3
python scripts/sync.py --clone                 # re-extract from upstream; exit 3 = something changed
python -m pytest -q                            # tests
```

**Ground truth order:** `data/weights.json` (numbers) → `knowledge/*.md` (mechanics, each with file:line) →
the upstream repo. Never quote a weight from memory; read the data file. Never claim to predict impressions.

**Style for user-facing output:** plain, specific, no hype; cite the upstream file for every mechanism; label
heuristics as heuristics; no em dashes.

**Do not:** post on the user's behalf, log in for them, scrape accounts other than the user's own, or store their
exported data anywhere but where they asked.

**Rate limits and account safety:** X throttles its web endpoints per account (~15-minute windows) and scores
automation-like behaviour (`bdsm/` upstream). Have the person run `scripts/collect_profile.js` themselves, once, in a
foreground tab; never loop it, never retry after a rate-limit message for 15-30 minutes, never drive their logged-in
session with repeated navigations, and never take actions (like/follow/reply/post) through automation. Say this before
they run anything.
