"""xboss: X's For You ranking, made usable.

- xboss.weights   load the mirrored production parameters (data/weights.json)
- xboss.score     the exact RankingScorer arithmetic (home-mixer/scorers/ranking_scorer.rs)
- xboss.lint      check a draft post against code-derived rules
"""
from .weights import load_weights, weights_path  # noqa: F401
from .score import Weights, score, cold_start_eligible, author_diversity_multiplier  # noqa: F401
from .lint import lint  # noqa: F401

__version__ = "0.1.0"
