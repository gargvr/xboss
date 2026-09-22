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

