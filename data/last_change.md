## 2026-09-17 · upstream 42266f3 (2026-09-17) · param.rs sync 2026-09-16T16:23:12Z

- **param removed** `ClickDwellLowFavRatePenaltyAlpha` (was `0.5`)
- **param removed** `ClickDwellLowFavRatePenaltyBaseline` (was `0.01`)
- **param removed** `ClickDwellLowFavRatePenaltyCap` (was `1.0`)
- **param removed** `ClickDwellLowFavRatePenaltyFloor` (was `0.01`)
- **param** `ColdStartMaxPostAgeSecs`: `86400` → `172800`
- **param added** `EnableCdwellOnImpr` = `False`
- **param removed** `EnableClickDwellLowFavRatePenalty` (was `False`)
- **param added** `EnableFavHoldout` = `False`

