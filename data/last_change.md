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

