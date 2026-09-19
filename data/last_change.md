## 2026-09-19 · upstream 8b25829 (2026-09-18) · param.rs sync 2026-09-18T16:21:20Z

- **param removed** `DwellRegretAlphaFavorite` (was `1.0`)
- **param removed** `DwellRegretAlphaQuote` (was `1.0`)
- **param removed** `DwellRegretAlphaReply` (was `1.0`)
- **param removed** `DwellRegretAlphaRetweet` (was `1.0`)
- **param removed** `DwellRegretAlphaShare` (was `1.0`)
- **param removed** `DwellRegretAlphaShareViaCopyLink` (was `1.0`)
- **param removed** `DwellRegretAlphaShareViaDm` (was `1.0`)
- **param removed** `DwellRegretDwellFloor` (was `1.0`)
- **param removed** `DwellRegretGateBias` (was `1.033918`)
- **param removed** `DwellRegretGateHysteresisBand` (was `0.0`)
- **param removed** `DwellRegretGateThreshold` (was `-0.634264`)
- **param removed** `DwellRegretGateWeights` (was `'seq_len:0.530298,n_fav:-0.082139,n_reply:0.485541,n_rt_quote:0.056561,n_vqv:-0.072778,n_click:-0.176675,n_bm_share:-0.167574,n_profile_follow:-0.221285,n_photo:-0.106004,n_negfb:0.031839,n_7d:-0.075799,n_1d:-0.241730,active_days:0.047017,active_days_7d:-0.126896,days_since_last:-0.034238,span_days:-0.052186,followers:-0.066642,followings:0.064140,account_age_years:-0.045455'`)
- **param removed** `DwellRegretNegBlockAuthor` (was `-8000.0`)
- **param removed** `DwellRegretNegMuteAuthor` (was `-15000.0`)
- **param removed** `DwellRegretNegNotInterested` (was `-10000.0`)
- **param removed** `DwellRegretNegReport` (was `-60000.0`)
- **param removed** `DwellRegretTemperature` (was `10.0`)
- **param added** `PhoenixColdStartMaxResults` = `0`
- **param** `PhoenixRetrievalMOEInferenceClusterId`: `'Experiment2Memy04'` → `'Experiment3Memy04'`
- **param removed** `ValueModelMode` (was `'weighted'`)
- **const removed** `home-mixer/scorers/ranking_scorer.rs::DWELL_REGRET_MEAN_EPS` (was `'1e-9'`)
- **const removed** `home-mixer/scorers/ranking_scorer.rs::DWELL_REGRET_MIN_TEMPERATURE` (was `'1e-6'`)
- **const removed** `home-mixer/scorers/ranking_scorer.rs::DWELL_REGRET_SIGMOID_MODE` (was `'dwell_regret_sigmoid'`)
- **const removed** `home-mixer/scorers/ranking_scorer.rs::GATED_DWELL_REGRET_MODE` (was `'gated_dwell_regret'`)
- **const removed** `home-mixer/scorers/ranking_scorer.rs::GATE_WEIGHTS_ALL_ZERO` (was `'seq_len:0,n_fav:0,n_reply:0,n_rt_quote:0,n_vqv:0,n_click:0,n_bm_share:0,n_profile_follow:0,n_photo:0,n_negfb:0,n_7d:0,n_1d:0,active_days:0,active_days_7d:0,days_since_last:0,span_days:0,followers:0,followings:0,account_age_years:0'`)
- **const added** `home-mixer/scorers/ranking_scorer.rs::WEIGHTED_VALUE_MODEL_MODE` = `'weighted'`

