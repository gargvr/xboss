---
name: xboss
description: Analyze someone's X (Twitter) account and drafts against X's open-sourced For You ranking code (xai-org/x-algorithm), then tell them, in code terms, why their posts don't travel and what to post next. Use whenever a user asks to grow on X, go viral, review a tweet/post draft, understand the X algorithm, or asks "why does nobody see my posts". Always start by asking for the handle and getting their recent posts (scripts/collect_profile.js), run `python -m xboss analyze`, then draft in the user's own voice.
---

# xboss · account-first review against X's ranking code

You are working inside (or with a clone of) **xboss**. It contains the mirrored production weights of X's For You ranker (`data/weights.json`, auto-synced from `xai-org/x-algorithm`), a scorer that reproduces `ranking_scorer.rs`, a draft linter, an account analyzer, and a knowledge base (`knowledge/01-05`). Every claim you make must trace to one of those files or to the upstream repo. Never predict impressions; the model's per-viewer probabilities are not public.

## Procedure

1. **Ask for the handle** (and follower count / Premium / join month if the export won't have them).
2. **Get their posts** (pick the first that works):
   - If you have a browser tool: open `https://x.com/<handle>` (logged in as them if possible) and run the body of `scripts/collect_profile.js` in the page; save the JSON as `me.json`.
   - Otherwise ask them to: log in to X → open their profile → DevTools console → paste `scripts/collect_profile.js` → save the copied JSON as `me.json`. It runs locally; nothing leaves their machine.
   - Fallbacks: `--csv` (X analytics content export, Premium) or `--paste` (text copied from the profile page, best effort).
3. **Run the account read:** `python -m xboss analyze me.json` (add `--handle/--followers/--following/--joined/--premium` if missing). Read `knowledge/02-reach.md` and `knowledge/01-scoring.md` before interpreting it.
4. **Report** in this order, plainly:
   - the snapshot (followers, median views vs followers, % originals with zero likes, best/worst formats)
   - the diagnosis in code terms (candidate-generation vs ranking vs suppression), citing files
   - five changes, in order of leverage (lane/bio, pin, first-like protocol, mutual graph, media)
   - what to stop doing (threads for reach, payload-less asks, 2+ mentions, shorteners, engagement bait)
5. **Draft the next 5-7 originals in the user's own voice** using their best posts as voice samples: lowercase/casing, sentence length, punctuation habits, no hashtags unless they use them, ≤ 280 chars unless Premium. Each post: payload first, then one specific question or one specific reason to forward. Include what to attach.
6. **Lint every draft** with `python -m xboss lint "<text>" [--media] [--premium]` and fix HIGH findings before showing it.
7. Give the first-hour protocol and the two numbers to watch (time-to-first-like, first-hour views vs followers).

## Rules of engagement
- Say "not in the repo" when something isn't; do not invent thresholds. Withheld: Grox prompts, URL reputation logic, BDSM thresholds, some botmaker rules.
- Prefer `python -m xboss explain <Param>` over quoting numbers from memory; the data file is auto-synced and weights change.
- Do not recommend: threads for reach, replying to big accounts for For You reach, engagement bait, follow/unfollow, buying engagement, more than one @mention, link shorteners, pinning a post with a questionable link.
- If the account has < 1,000 followers, say so and explain the cold-start lift; if it's < 1 year old, say Under the Hood isn't available yet.
