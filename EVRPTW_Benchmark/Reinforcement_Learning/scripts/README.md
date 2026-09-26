# Scientific preparation and analysis helpers

These retained helpers construct training inputs, calibrate declared representations/rewards, and inspect recorded learning results. They retain the original implementation; no scientific values or algorithms were changed for packaging. The hotpath diagnostic permits absent Git metadata in a source archive and reports it as unavailable. Historical machine launchers, remote-host manifests, stop/watch scripts and deployment-only tests are excluded.

Run from the repository root after installing the appropriate core/learning extras. Inspect the actual arguments before supplying complete training inputs:

```bash
python -m EVRPTW_Benchmark.Reinforcement_Learning.scripts.build_training_stream --help
python -m EVRPTW_Benchmark.Reinforcement_Learning.scripts.build_support_sets --help
python -m EVRPTW_Benchmark.Reinforcement_Learning.scripts.calibrate_euclidean_representation --help
python -m EVRPTW_Benchmark.Reinforcement_Learning.scripts.calibrate_training_reference_cost --help
python -m EVRPTW_Benchmark.Reinforcement_Learning.scripts.clustered_bootstrap --help
```

`build_training_stream` freezes ordered training IDs and source digests; `build_support_sets` selects family-level support; the two calibration scripts determine the declared Euclidean representation and deterministic training-only reward reference. They require separately provisioned full training data and are not substitutes for the final frozen calibration artifacts. Do not calibrate using the 22 evaluation views in review-core.

`audit_rrnco_comparison` pairs existing validation rows and discloses missing metadata. `summarize_drl_experiments` reads existing experiment directories. `generate_terran_synthetic100` and `audit_terran_synthetic100` create/audit the separately declared upstream-derived synthetic corpus; they do not generate EVRP-TW-D road instances. `prepare_preverified_stream_marker` and `refresh_preverified_training_streams` manage explicit already-verified stream metadata, without silently declaring new data verified.

`benchmark_drl_hotpaths`, `diagnose_evrptw_policy`, and `probe_evrptw_stability` are bounded engineering diagnostics, not paper evaluation records. The latter uses a local script import and should be invoked as:

```bash
python EVRPTW_Benchmark/Reinforcement_Learning/scripts/probe_evrptw_stability.py --help
```

The release check executes targeted scientific regression tests and principal CLI help. Complete corpus calibration, full training, and large diagnostic sweeps were not run during packaging. Method/common tests remain alongside their source; root release acceptance uses the explicitly documented curated checks.
