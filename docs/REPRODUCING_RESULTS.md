# Reconstructing recorded results

The current delivery contains **three bundles: source code, review-core, and real inference checkpoints**. It does not include `paper-records/`, the complete historical evaluation records, or a frozen paper BKS. Full experiment records are being updated and are outside this delivery. Consequently, these three bundles **cannot reconstruct the complete paper tables or figures**. Complete aligned records, cohort/configuration manifests and frozen BKS must be supplied separately by the authors; no release date or download location is promised here.

The source retains the `evrptw-db report` interface. Its aggregation rules are covered by the included regression tests. To rebuild a particular experiment, first obtain the complete inputs for that same declared protocol and snapshot, including failed and missing positions. The final manuscript/Appendix D and aligned eight-method records remain to be supplied or confirmed.

## Reporting interface with separately supplied inputs

The following is an **input template, not a runnable example using the three delivered bundles**. From `evrptw-db/` after core installation, set `RECORDS_DIR` to a directory you obtained separately and replace the scope label with that experiment's actual protocol:

```bash
RECORDS_DIR=/path/to/author-supplied-records
evrptw-db report \
  --records "$RECORDS_DIR/instance_results.csv" \
  --cohort "$RECORDS_DIR/cohort_manifest.csv" \
  --bks "$RECORDS_DIR/bks.csv" \
  --configurations "$RECORDS_DIR/expected_configurations.csv" \
  --scope author_supplied_protocol_snapshot \
  --output outputs/supplied-records-report
```

Required inputs must agree on their instance and configuration identities:

| Input | Required columns / meaning |
| --- | --- |
| `instance_results.csv` | `config_id`, `cohort_id`, `instance_id`, `verified_feasible`, `cost_usd`, `online_time_s`; retain actual failures and missing values |
| `cohort_manifest.csv` | `cohort_id`, `instance_id`; the complete expected instance set for every declared cohort |
| `expected_configurations.csv` | `config_id`; the complete expected configuration list, including configurations with no results |
| `bks.csv` | `cohort_id`, `instance_id`, `bks_cost_usd`, `freeze_status`; a disclosed frozen reference, not newly selected demo winners |

Omit `--bks` if a frozen reference is unavailable; gaps then remain blank. Preserve the original records' candidate budget, objective, timing boundary, batch and device metadata alongside these reporting columns. Select a coherent protocol before aggregation; a user-supplied scope label does not certify paper alignment or make different timing boundaries comparable.

Outputs are `summary.csv`, a standalone exportable `feasibility.svg`, and `report.json`. The explicit configuration list is crossed with every declared cohort, including entirely absent configurations/cohorts. Without that optional list, only configuration IDs present in records can be inferred. Every expected instance contributes to the FR denominator. Quality means require full-cohort FR=1. Missing measured times remain missing; duplicate keys, unknown instances and nonfinite measured runtimes are rejected. Gaps require complete positive finite frozen BKS. The report does not create a new reference pool. The SVG presents feasibility only and carries the declared scope.

## What the delivered sample establishes

The 22-input review sample supports actual independent route replay, new short-budget search, bounded generation and the documented real-weight inference. It is not the complete 500-instance cohort for any stratum. Its historical learning routes used 100 candidates and shortest-distance monetary costs. The paper's current target is 30 candidates with fastest-time-path distance for monetary cost; supplied checkpoints retain their recorded objective contracts, as explained in [TRAINING_AND_EVALUATION.md](TRAINING_AND_EVALUATION.md). Do not relabel historical costs or combine these scopes into one ranking.

Reconstructing a table from complete recorded metrics checks aggregation; independently verifying every route also requires all corresponding numerical instances and route artifacts. Neither operation reconstructs the original solver runtime. The three-bundle sample does not supply those full-corpus materials.

The headroom experiment is separate from the main comparison: 500 Cus1000 T1 instances, five Road-1000 policies in the initial pool, then 7,200 seconds of ALNS per instance. A three-policy reference or validation-only run is not that experiment. No headroom result is supplied here, and new smoke solutions do not update a frozen paper BKS. Full original training, full generation, the 1,800-second eight-method evaluation and 7,200-second headroom are **NOT RUN** in this local delivery. See [DATA_AVAILABILITY.md](DATA_AVAILABILITY.md) for the remaining inputs.
