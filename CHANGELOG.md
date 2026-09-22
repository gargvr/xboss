# Changelog

Every change to X's mirrored production parameters (home-mixer/params/param.rs and friends), as detected by scripts/sync.py. Newest first.

## 2026-09-22 · upstream 3aa0fa3 (2026-09-22) · param.rs sync 2026-09-21T16:23:47Z

- **param added** `NewUserOonWeightFactor` = `1e-05`
- **param added** `PhoenixMoeColdStartMaxResults` = `0`
- **param added** `RetrievalCandidatesKafkaMaxCandidates` = `200`
- **param added** `RetrievalCandidatesKafkaSamplePercent` = `5.0`
- **param added** `SimclustersMaxCandidateAgeHours` = `48`
- **param added** `VMRankerComputeValueModel` = `False`
- **param added** `VMRankerSendValueModelInputs` = `False`
- **const removed** `home-mixer/params/config.rs::NEW_USER_OON_WEIGHT_FACTOR` (was `1e-05`)
- **const removed** `home-mixer/sources/simclusters_source.rs::ANN_MAX_POST_CANDIDATE_AGE_HOURS` (was `48`)
- **retention removed** `MmMetadata/mm_emb_metadata_1day` (was `24`)
- **retention removed** `MmMetadata/mm_emb_metadata_video_2day` (was `48`)
- **retention removed** `MmMetadata/mm_emb_metadata_video_4day` (was `96`)

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

## 2026-09-17 · upstream 42266f3 (2026-09-17) · param.rs sync 2026-09-16T16:23:12Z

- **param removed** `ClickDwellLowFavRatePenaltyAlpha` (was `0.5`)
- **param removed** `ClickDwellLowFavRatePenaltyBaseline` (was `0.01`)
- **param removed** `ClickDwellLowFavRatePenaltyCap` (was `1.0`)
- **param removed** `ClickDwellLowFavRatePenaltyFloor` (was `0.01`)
- **param** `ColdStartMaxPostAgeSecs`: `86400` → `172800`
- **param added** `EnableCdwellOnImpr` = `False`
- **param removed** `EnableClickDwellLowFavRatePenalty` (was `False`)
- **param added** `EnableFavHoldout` = `False`

## 2026-09-16 · upstream fad2f71 (2026-09-16) · param.rs sync 2026-09-15T16:25:02Z

- **param** `EnableAdsBrandSafetyVerdictV2`: `True` → `False`

## 2026-09-15 · upstream 2d4a03c (2026-09-15) · param.rs sync 2026-09-14T16:22:15Z

- **param added** `EnableResponseDiversityStatsExperimentBucket` = `False`

## 2026-09-09 · upstream 49815da (2026-09-08) · param.rs sync 2026-09-08T16:24:06Z

- **param** `PhoenixRetrievalMOEInferenceClusterId`: `'Experiment1Fou'` → `'Experiment2Memy04'`
- **param added** `WeightPerturbationSalt` = `''`
- **param added** `WeightPerturbationSigma` = `0.0`

## 2026-09-04 · upstream 9b0dc31 (2026-09-04) · param.rs sync 2026-09-03T16:23:24Z

- **param added** `PhoenixExperimentOverrides` = `''`

## 2026-09-03 · upstream 85ac72a (2026-09-02) · param.rs sync 2026-09-02T16:03:45Z

- **param** `PhoenixRetrievalAggregationType`: `'DENSE_WITH_SHORT_DWELL'` → `'DENSE_WITH_LONG_DWELL'`

## 2026-09-02 · upstream 7ba7768 (2026-09-01) · param.rs sync 2026-09-01T16:42:25Z

- **param** `AdsBlenderType`: `'partition_organic_low_risk'` → `'multi_risk'`

## 2026-09-01 · upstream 6384ca7 (2026-09-01) · param.rs sync 2026-08-31T16:17:17Z

- **param added** `EnablePhoenixScoreStatsExperimentBucket` = `False`

## 2026-08-29 · upstream bc8e5f0 (2026-08-28) · param.rs sync 2026-08-28T20:07:44Z

- **param added** `RerankerHeadTag` = `0`

## 2026-08-26 · upstream 0d3cdd8 (2026-08-25) · param.rs sync 2026-08-25T16:20:01Z

- **param** `ColdStartTsTopK`: `5` → `2`
- **param** `DwellWeight`: `0.0` → `0.05`
- **param** `EnableAdsBrandSafetyVerdictV2`: `False` → `True`
- **param removed** `EnableMpnScoring` (was `False`)
- **param added** `MultiplierPreOffset` = `False`
- **param** `PhoenixAggregationType`: `'DENSE_WITH_SHORT_DWELL'` → `'DENSE_WITH_LONG_DWELL'`
- **param** `ShadowTrafficPhoenixClusterRates`: `['Experiment6Fou:1.5']` → `[]`
- **param removed** `UseServedSlateContext` (was `False`)
- **param removed** `VMRankerSendHeadWeights` (was `False`)
- **param removed** `VMRankerValueModelId` (was `'dpp'`)
- **param** `VideoOpenWeight`: `0.05` → `0.07`
- **param** `VqvWeight`: `0.05` → `0.0`
- **retention removed** `Ads/evergreen_video_grok_30day` (was `720`)
- **retention added** `Main/1fav_video_2day` = `48`
- **retention removed** `Main/evergreen_video_grok_30day` (was `720`)
- **retention added** `Sid/1fav_video_2day` = `48`
- **retention removed** `Sid/evergreen_video_grok_30day` (was `720`)

## 2026-08-21 · upstream d0cef2f (2026-08-20) · param.rs sync 2026-08-12T04:09:22Z

- **param added** `EnableAiTrendFeedbackContext` = `False`
- **param added** `UseServedSlateContext` = `False`

## 2026-08-18 · upstream b089ce6 (2026-08-17) · param.rs sync 2026-08-12T04:09:22Z

- **param added** `EnableAdsBrandSafetyVerdictV2` = `False`
- **const** `home-mixer/params/config.rs::FOLLOWING_MAX_RESULT_SIZE`: `100` → `110`
- **const** `home-mixer/params/config.rs::FOLLOWING_PIPELINE_RESULT_SIZE`: `102` → `112`
- **const** `home-mixer/params/config.rs::FOLLOWING_POST_FETCH_SIZE`: `91` → `101`

