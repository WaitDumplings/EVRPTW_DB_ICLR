# Local release acceptance

## Current three-entry reviewer workflow

The README now leads with `bash generate.sh`, `python train.py`, and `python eval_plot.py`. The source package includes two genuine core/train Road-100 examples and a small offline generation fixture. The main evaluation command reads its separate T1/test Road-100 view directly from `review-core/`. An optional canonical JSON export remains for format compatibility; earlier checks below used that equivalent export. No Euclidean training sample is used. The [workflow acceptance manifest](../manifests/reviewer_workflows_acceptance.json) records the following source-preparation checks; the external delivery report records the final extracted-archive run.

| Check | Status | Evidence / boundary |
| --- | --- | --- |
| Generation entrypoint and parameters | PASS | 15 focused tests; exact instance count, worker equality, spaces in paths, and dry-run without files, network or credentials |
| Existing complete city CLE to Road-100 | PASS | One new 100-customer, 20-station instance through the strict CLE adapter and retained Stage-2 modules; 18.37 s; original source-quality blockers preserved |
| Fresh public downloads and Stage 1 | NOT RUN | Source documentation and public Amazon object headers checked; no multi-GB body download or fresh Stage-1 city build was executed |
| Native short training for all five models | PASS | AM, EVRPTW-RL, RRNCO, DRL-TS and TERRAN; 5 epochs over 2 original training views; 10 actual optimizer updates each; finite losses and gradients, changed parameters, strict saved-state reload |
| Training input validation | PASS | 20 checks covering hashes, IDs, splits, representation, scales and canonical matrix shape/values |
| Newly trained weights to held-out route and SVG | PASS | All five short-run checkpoints evaluated on the separate T1/test sample, 4 candidates each; selected route independently verified and SVG parsed |
| Supplied genuine AM weights with two required arguments | PASS | Road-100 sample, 30 candidates, automatic step limit 484; verified route and SVG; 3.17 s including startup |
| Current repository suite | PASS | 73 tests passed in 7.91 s |

One epoch visits both supplied training instances once. These checks establish that training and inference execute; they do not establish convergence or reproduce full paper training. The five-model runs preceded a final input-validation tightening that did not change training mathematics; final validation checks and checkpoint metadata were rerun. The final extracted delivery additionally reruns the default EVRPTW-RL five-epoch command. The plots are terminal-to-terminal route schematics, not road polylines.

The training console was subsequently simplified to one overview, one loss line per epoch and the saved checkpoint path. A fresh default EVRPTW-RL five-epoch run preserved all ten update records, every prior loss and all 15 checkpoint tensors exactly. Only console messages changed; the detailed metrics remain in JSON logs. This targeted check is recorded under `console_simplification` in the workflow manifest.

The current README evaluation command was also run directly against the `review-core` view manifest for `iv_4073f1928fa0c95f3de64257`: 100 customers, 30 AM candidates, an independently verified selected route and a parsed SVG. The `core_path_evaluation` entry records this run separately from earlier canonical-export checks.

## Earlier release checks

The tested interpreter is Python 3.11.13 on Linux x86_64. Core dependencies were installed into a new virtual environment without system-site-packages. Optional PyTorch 2.5.1+cpu was installed afterward. No Gurobi, CUDA device or private account was needed. `requirements/tested-cpu-environment.txt` records only the small test environment; it is not a dump of the original research machine. Geographic extras and commercial solver installation were not fully exercised.

| Check | Status | Evidence / boundary |
|---|---|---|
| Clean core installation and imports | PASS | Fresh venv; no original checkout, private PYTHONPATH or source symlink |
| Real CPU route replay | PASS | First frozen view; K=1, D=194.13879445940256 km, C=443.09390458194605 USD |
| Raw and reconstructed sample equivalence | PASS | 22 views; raw matrices unchanged; exact original/packaged loaded arrays and terminal order |
| View-specific singleton certificates | PASS | 22 original views, correct station rosters |
| Historical sample route audit | PASS as an audit | 400 routes retained, 387 current-verifier PASS and 13 FAIL; 40 missing positions retained |
| Cached-CLE Stage-2 engineering generation | PASS | New demo/train IDs using actual production routing, order and certificate modules |
| Worker and portability checks | PASS | 1 vs 2 workers, exact scientific payloads; directories with spaces; corrupted certificate rejected |
| Short actual ALNS solve | PASS | 10-second budget; feasible incumbent independently replayed, measured runtime retained |
| Resource/cost/report regression tests | PASS | 11 focused tests; malformed routes, resources, asymmetric distinct path matrices, missing groups, nonfinite timing/BKS |
| Checkpoint export | PASS | All 20 strict loads, exact tensors and fixed-seed output comparisons; no optimizer/resume promise |
| Real policy inference | PASS | All 5 Road-100 models, first real view, 30 candidates, CPU; selected route independently verified |
| Learning gradients and optimizer | PASS | All 5 recorded architecture sizes, separate 8-customer train fixture; diagnostic loss, not native full training |
| Quick training and generic checkpoint evaluation | PASS in source preparation | 29 checks; eight native REINFORCE/Adam updates, five real Road-100 methods with 30 candidates each, verified routes and SVG; details below |
| Earlier repository contract suite | PASS | 58 tests passed in 2.89 s, including quick training, route figures and existing resource/report contracts |
| Reporting contracts | PASS | Cohort completeness, missing outcomes, nonfinite timing and BKS tests; full experiment records are not distributed |
| Anonymous full-generation local source setup | PASS | New neutral clean Git snapshot accepted by unchanged provenance gate; dirty snapshot rejected |
| Text, paths, serialized metadata and binaries | PASS on inspected candidate | Explicit private identity/path/credential scan, 20 restricted checkpoint loads, NumPy/Parquet metadata inspection; necessary upstream attribution retained |
| Extracted functional checks | PASS | CPU, generation, search, learning and contract checks passed from extracted sources. See [measured evidence](../manifests/acceptance.json). The separate delivery report binds the current three archive checksums and packaging checks. |
| Raw-input Stage-1 mini and complete Stage1/Stage2 | NOT RUN | Whole source inputs and manual source-quality approvals omitted |
| Native full training / exact resume | NOT RUN / NOT SUPPORTED by inference weights | Full training corpus and run states omitted; native source retained |
| Full eight-method 1800s evaluation / Gurobi / 7200s headroom | NOT RUN | No expensive run launched; historical 2h/distance and 100-candidate records not relabeled |
| Final manuscript and Appendix D alignment | NOT RUN | Author-selected manuscript unavailable |
| Original code grant / combined data-weight public grant | NOT RUN | Author license decision and source-specific unresolved scope remain pending |
| Anonymous reviewer hosting | NOT RUN | No anonymous reviewer endpoint has been verified; private version-control storage is separate |

Network connections are blocked during the clean acceptance replay/generation/learning commands after dependency installation. Runtime and peak-memory evidence for the final extracted archives is retained in the separate delivery report. No source training jobs were stopped. Historical route failures are observations, not hidden acceptance successes.

## Earlier CPU path measurements

CPU: AMD Ryzen Threadripper 3970X 32-Core Processor, Linux x86_64, Python 3.11.13. Learning uses one CPU thread and PyTorch 2.5.1+cpu. These are complete subprocess measurements including imports and startup, not formal per-instance benchmark times. Peak RSS does not sum simultaneous workers. Exact measurements and exit codes are in `manifests/acceptance.json`; dependency versions are in `requirements/tested-cpu-environment.txt`.

| Path | Process wall time (s) | Peak RSS (MiB) |
|---|---:|---:|
| Real route replay | 0.87 | 192.9 |
| ALNS with 10-second algorithm budget | 11.99 | 558.5 |
| Stage-2 demo, one worker | 1.12 | 197.0 |
| Stage-2 demo, two workers | 1.82 | 194.9 |
| AM-EVRPTW, real Road-100, 30 candidates | 3.07 | 449.3 |
| EVRPTW-RL, real Road-100, 30 candidates | 5.22 | 489.2 |
| TERRAN, real Road-100, 30 candidates | 3.17 | 473.2 |
| RRNCO, real Road-100, 30 candidates | 4.47 | 551.9 |
| DRL-TS, real Road-100, 30 candidates | 4.72 | 537.7 |
| Five-method diagnostic optimizer check | 3.32 | 599.1 |

The timings above were measured during source preparation; they cover the listed subprocesses, not a full benchmark. Full historical records were subsequently excluded from this three-bundle delivery. Final packaging evidence is recorded separately in the delivery report. Timing on another CPU can differ. Run commands and output locations are in [Quickstart](QUICKSTART.md), [generation](GENERATION.md), [learning](TRAINING_AND_EVALUATION.md) and [reconstruction](REPRODUCING_RESULTS.md).

## Quick-demo source-preparation acceptance

The earlier `scripts/quick_train.py` and `scripts/evaluate.py` entry points completed 29 acceptance checks, all PASS. This count includes command exits, output contracts and the repository test suite; it does not represent 29 benchmark runs. Commands ran with network connections blocked, on CPU with one thread, Python 3.11.13 and PyTorch 2.5.1+cpu. The [quick-demo acceptance manifest](../manifests/quick_demo_acceptance.json) records these source-preparation outcomes. Final extracted-archive verification and archive checksums are recorded separately in the delivery report.

| Check | Status | Evidence / boundary |
| --- | --- | --- |
| Eight native AM REINFORCE/Adam updates | PASS | Separate 8-customer `demo/train` fixture; parameter changes at every step; strict checkpoint reload and tensor identity checked |
| Generated checkpoint evaluation | PASS | Same demo instance, 30 candidates, verified selected route and SVG; an interface check, not held-out evaluation |
| Five genuine Road-100 checkpoints | PASS | AM-EVRPTW, EVRPTW-RL, TERRAN, RRNCO and DRL-TS on the first frozen real view, 30 candidates each; selected routes independently verified and SVG written |
| Instance input equivalence | PASS | Real view ID versus explicit manifest: identical routes; demo canonical JSON versus demo view: identical routes |
| One-step incomplete evaluation | PASS | Exit 2, failure diagnostics saved, no successful-route SVG |
| Missing checkpoint | PASS | Error exit; no result or random-weight fallback |
| Existing output directory | PASS | Training and evaluation both refused the directory |
| Repository contract tests | PASS | 58 passed in 2.89 s |

The recorded first and eighth training losses were 44.877529 and 37.865704. All eight updates changed parameters. Loss is stochastic; these values establish neither monotonic improvement nor reproduction of full paper training. The [saved loss records](../examples/expected/quick_demos/training/loss.jsonl) and [training summary](../examples/expected/quick_demos/training/summary.json) retain the measured values.

| New command path | Process wall time (s) | Peak RSS (MiB) |
| --- | ---: | ---: |
| Eight training updates | 3.32 | 533.2 |
| Generated demo checkpoint, 30 candidates | 2.27 | 444.9 |
| AM-EVRPTW, real Road-100, 30 candidates | 3.17 | 450.0 |
| EVRPTW-RL, real Road-100, 30 candidates | 5.32 | 490.2 |
| TERRAN, real Road-100, 30 candidates | 3.27 | 472.2 |
| RRNCO, real Road-100, 30 candidates | 4.57 | 551.5 |
| DRL-TS, real Road-100, 30 candidates | 4.77 | 537.6 |

These subprocess measurements include imports and startup on the CPU identified above. They are demonstration measurements, not formal paper inference times or full-cohort performance. Commands and observed [demo](../examples/expected/quick_demos/evaluate_demo/routes.svg) and [real AM](../examples/expected/quick_demos/evaluate_real_am/routes.svg) route illustrations are linked in [QUICK_DEMOS.md](QUICK_DEMOS.md). The figures show terminal-to-terminal schematics, not actual road geometry.

## Anonymity boundary

The local audit covers filenames and text, private paths and remotes, credential patterns, archive members and ownership, checkpoint metadata and restricted tensor loading, and NumPy/Parquet metadata. Unnecessary documents, notebooks, logs, caches, credentials and original Git history are excluded. Public third-party source links, copyright notices and scientific city names remain intentionally present. The internal author brief, private mapping and identity vocabulary are not distributed.

This audit uses the identities available in local materials; the complete submission author roster was not supplied. It does not certify a future hosting account, publication permission, or manuscript alignment. Final extracted archives are audited again and identified by the separate delivery checksum report.

## Optional native integration test scope

The retained native tests cover a larger production checkout than this anonymous review bundle. Production cluster launchers are not included: `auto.sh`, `generate_cle.sh`, `generate_instances.sh`, `create_dataset_archive.sh`, and the learning launcher gate `scripts/drl_job_runtime.py`. Tests that specifically exercise these absent files report explicit optional-integration skips. Their original behavior assertions remain available when those files are present. Native periodic-training, checkpoint-selection and saved-artifact assertions run separately from the optional launcher completion gate.

`EVRPTW_Dataset_Generator/scripts/dataset_archive_tool.py` is a retained production helper whose complete archive restore workflow requires the omitted `auto.sh`; it is not a standalone supported review entry point. Use the generation, training and evaluation commands documented in the main README. Production archive creation also requires a real Git revision; an extracted source archive by itself does not satisfy that provenance gate. No original Git history is bundled.

Spawned CPU distributed tests additionally require working operating-system shared memory and local process-group communication. A restricted host can fail before a distributed correctness assertion runs. Those failures are not silently skipped or counted as successful learning checks. The bounded reviewer workflow checks and the broader native test suite have separate acceptance scopes; this package does not claim that every native production integration passes in an extracted anonymous checkout.
