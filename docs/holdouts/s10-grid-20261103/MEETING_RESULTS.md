# Flat meeting snapshot

Job 22014741 ran read-only prediction at commit 922a558 on defq-64core (2 CPUs, 8 GiB, 20-minute cap). All four scenarios completed. Live chains were not modified. Output: `/work/abussing/bsfm-consolidation/evidence/meeting-flat-922a558`.

| Circles | Diameter | Production draws | Flat RMSE | Training cell-type baseline RMSE |
| --- | --- | --- | --- | --- |
| 12 | 1/16 | 42 | 0.3719517189 | 0.3805434631 |
| 12 | 1/8 | 47 | 0.3817152269 | 0.3849996289 |
| 8 | 1/16 | 32 | 0.3746175729 | 0.3850995986 |
| 8 | 1/8 | 41 | 0.3772930392 | 0.3840761260 |

All 162 completed production draws were used, with individual conditional-mean Yhat arrays saved in each configuration's `draw_predictions.npz`. Full output hashes and source-record identities are in each `receipt.json`. `report.json` retains all 91 genes' predictions and metrics. Fast conditional means matched the existing Cholesky routine for every factor in each first retained draw: maximum absolute error 1.013e-13. Bridge and warmup excluded.

Compact visualization payload `meeting-data.json.gz` SHA-256: `672a20a1ff4e76d43a9583f1d34fc4ec7ca5ca175cf19f357c54bd0bc54ef751`. The desktop copy was hash-verified before rendering. Local standalone HTML: `C:/Users/andyb/Desktop/BSFM-S10-Meeting.html`. Generator: `build_meeting_html.py`; external geometry files are under `C:/Users/andyb/Desktop/BSFM_ENVIRONMENTS/s10-hole-plots`.

Exploratory gene selection: two highest aggregate observed variances, two highest aggregate RMSE/baseline-RMSE ratios excluding prior selections, then two lowest ratios excluding prior selections. Selected: Ptgds, Apoe, C1qa, Abi3, Camk2a, Cspg5. Selection uses held-out outcomes; it is labeled descriptive. The HTML also tabulates metrics for every gene. Visualization values rounded to three decimals; metrics use full precision.

No convergence or deep-model superiority claim. Full-sample SCT reuse is declared. Scenarios contain different omitted cells and draw counts, so differences do not isolate causal hole-size/count effects. No sampler scientific source was changed for this report.
