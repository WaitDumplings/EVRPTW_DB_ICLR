# Independent review-package audit

This audit concerns the supplied source/sample/checkpoint snapshot and the
bounded reviewer workflows. It is not a rerun of the paper's complete experiments.

## Executed checks

Python 3.11.11 on macOS arm64, a fresh virtual environment, PyTorch 2.5.1,
NumPy 2.3.5, pandas 3.0.5, PyArrow 24.0.0 and SciPy 1.17.0.
Dependencies installed successfully and `pip check` found no conflicts.

| Check | Result |
|---|---|
| Root reviewer tests plus native dataset/solver tests | 1,264 passed; 13 explicitly skipped; 12 dependency warnings |
| Five real Road-100 checkpoints on the real T1 review view | All five completed 30-candidate CPU inference and independent route verification |
| Five short Road-100 training workflows | All five completed five epochs / ten optimizer updates with changed model parameters |
| 10-second ALNS search | Returned a route accepted by the independent verifier |
| Cached-road generation with one and two workers | Passed; scientific output hashes matched exactly |
| All 20 supplied inference checkpoints | Restricted loading, strict state loading, finite tensors, counts and manifest metadata passed |
| Full supplied sample | 22 unique views / 20 families; per-file hashes, train/test view and family separation, and paired-scale consistency passed |
| All 400 stored historical route sets | Replayed: 387 accepted, 13 rejected; results matched the supplied replay records |
| Source and archive inspection | No detected known author identity, private path, credential or unsafe archive member after metadata cleanup |

The 13 skips comprise seven checks requiring omitted production/cluster launchers,
four comparisons requiring the original pre-optimization Git oracle, and two
CUDA-only checks. They are not counted as passes. Native multiprocess tests needed
local shared-memory access; the initial sandboxed failures were environmental,
and the distributed tests passed when that access was allowed. Gurobi's 31
small tests are included in the total; no large Gurobi run was performed.

The rejected historical routes are TERRAN Euclid-100 records containing
customer-free routes. They remain present and labeled as failures. Historical
route availability does not establish final-paper reproducibility.

## Corrections made

The final paper objective configuration now explicitly specifies
`running_time_path_distance_km`. The shared core loader validates that field
against its already enforced objective semantics, so core/search and learning
loaders interpret the same configuration consistently. A regression checks both
loaders and rejects conflicting declarations. Historical checkpoint objectives
and omitted-field learning defaults were not silently changed.

Internal source-commit identifiers and cluster-server aliases were removed or
neutralized without changing scientific calibration values. Third-party license
notices and upstream version identifiers remain intact. A pandas 3 missing-value
test was made portable; native optional-launcher tests now state their unavailable
prerequisites, separately from the available training checks.

## Unresolved publication and reproduction scope

- Original-code public licensing is still as stated in the root LICENSE.
- Combined data/weight public-distribution permissions are not certified by this audit.
- Eight AM-EVRPTW/EVRPTW-RL weights use the later fastest-time-distance objective;
  twelve TERRAN/RRNCO/DRL-TS weights retain historical shortest-distance objectives.
  Final manuscript alignment is unconfirmed.
- Full aligned 30-candidate result records, frozen BKS and complete training/test
  corpora are not included. The package cannot reconstruct complete paper tables.
- Fresh multi-GB public-source acquisition, full city construction, full training,
  GPU timings, complete 1,800-second baselines and 7,200-second refinement were not run.
- Anonymous hosted reviewer access is separate from private version-control storage.

See [Reviewer quickstart](../REVIEW.md) for the supported commands. A compact ZIP
contains a documented subset of the larger sample and checkpoint delivery; its
top-level manifest gives the exact included material.
