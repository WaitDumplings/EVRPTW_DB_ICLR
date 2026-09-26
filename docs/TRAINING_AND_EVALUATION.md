# Training, checkpoint inventory and evaluation

The five learning implementations are AM-EVRPTW, EVRPTW-RL, TERRAN, RRNCO and DRL-TS. The source tree retains their native training and evaluation entrypoints. `configs/training/learning_inventory.json` inventories 20 actual checkpoints: each method has Euclid-100, Road-100, Road-500 and Road-1000 weights. D/G denote the road representation; E denotes Euclidean/synthetic training. Training representation does not change the physical constraints of a road test instance.

## What is included

The adjacent `review-checkpoints/` directory contains 20 genuine inference checkpoints, approximately 132 MiB in total (see the manifest for exact file hashes). Each `.pt` contains model tensors, required constructor arguments, objective and normalization settings, a neutral artifact identifier and the recorded best epoch. It contains no optimizer, sampler/RNG state, original command line, host path, run directory or Git history. All tensors were compared exactly to their source checkpoints and all 20 models loaded with `strict=True`. Do not use these artifacts to claim exact resumed training.

Eight AM/EVRPTW-RL artifacts are from the later curriculum runs. The twelve TERRAN/RRNCO/DRL-TS artifacts are from the historical result export. Their relationship to the final manuscript remains **UNCONFIRMED**; the inventory does not infer it. The later eight use the running-time-path distance in their economic objective. Historical artifacts use shortest-distance objective matrices while physical travel time and energy follow running-time paths. Historical final evaluation exports used 100 candidates; the review command below uses 30. Neither objective definitions nor historical candidate counts have been silently relabeled.

| Method | Euclid-100 best epoch | Road-100 best epoch | Road-500 best epoch | Road-1000 best epoch |
|---|---:|---:|---:|---:|
| AM-EVRPTW | 1700 | 1300 | 2000 | 1300 |
| EVRPTW-RL | 2000 | 1700 | 2500 | 1000 |
| TERRAN | 4200 | 3300 | 2100 | 700 |
| RRNCO | 5800 | 4900 | 4700 | 200 |
| DRL-TS | 2700 | 4300 | 4000 | 100 |

These are checkpoint-recorded epochs, including the recorded curriculum-stage convention, not an asserted common number of optimizer updates or total accumulated training epochs. The release is a fixed snapshot; subsequent source-run progress is not part of it.

## Install the CPU learning dependencies

Use Python 3.11 or 3.12. From the repository root:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install torch==2.5.1 --index-url https://download.pytorch.org/whl/cpu
python -m pip install -e '.[learning]'
```

The editable install includes the core dataset/verifier dependencies as well as the learning extras. Installation requires package access or a pre-populated wheel cache; the generation, inference and gradient checks run offline after installation. No CUDA toolkit, GPU or solver license is required for these learning review commands. See the root installation documentation for the exact clean-environment dependency lock.

## Quick training and route figures

The reviewer entry point is `python train.py --model evrptw_rl --scale 100`, defaulting to five epochs on the two bundled original Road-100 `core/train` instances. Each epoch visits both instances once, so five epochs produce ten actual native-learning updates. Models are `am`, `evrptw_rl`, `terran`, `rrnco` and `drl_ts`. The terminal shows one run summary, each epoch's loss and the final checkpoint path; detailed update diagnostics remain in `loss.jsonl` and `summary.json`. The script verifies training-input hashes and split/representation/scale contracts and saves its final demo checkpoint with objective/constructor metadata and strict reload verification. No Euclidean sample is used by this entry point.

Use `python eval_plot.py --ckpt <checkpoint.pt> --inst_path ../review-core/materialized/families/mf_f00002829bd8a1180a26e4cb/views/iv_4073f1928fa0c95f3de64257/view_manifest.json` to decode, independently verify and draw a route using the separate original T1 test view directly from `review-core/`. The actual instance size determines the decoding horizon. The [README](../README.md) and [reviewer guide](QUICK_DEMOS.md) show the short commands and parameters.

This is a runnable training-framework demonstration on a tiny sample, not a reproduction of the full training dataset, batch configuration, convergence, or reported performance. It uses the shared model and native learning components; the full paper reward/baseline-refresh/curriculum/validation protocol is not reproduced. Its differences are listed in each `summary.json`; loss need not decrease monotonically. The older `scripts/quick_train.py` eight-customer AM integration check and `scripts/learning_smoke.py` diagnostic gradient check remain available as developer checks and are not the default Road-100 training workflow.

## Offline real-weight inference

From the repository root, after installing the learning dependencies:

```bash
python scripts/learning_demo.py --bundle ../review-core \
  --checkpoint ../review-checkpoints/am_evrptw_road_100.pt \
  --candidates 30 --seed 1234 --max-steps 360 --threads 1 \
  --output outputs/am_road100.json
```

This loads the first real Cus100 view from `sample_manifest.json`, performs strict checkpoint loading, samples 30 routes in parallel trajectories, and chooses the lowest-cost environment-successful candidate that passes independent resource/route verification. An infeasible or incomplete final candidate cannot replace an earlier valid candidate. Exit status 2 means no complete verified solution was selected. Missing, incompatible or unrecognized checkpoints produce an error; there is no random-weight inference fallback.

The checkpoint names for the other Road-100 methods are `evrptw_rl_road_100.pt`, `terran_road_100.pt`, `rrnco_road_100.pt` and `drl_ts_road_100.pt`. Pass `--view-id` to choose another listed view. Larger views need a larger explicit `--max-steps` budget and substantially more compute; the 360-step default is the bounded Cus100 review demonstration. Inference on a different problem size is an explicit generalization evaluation, not evidence that the checkpoint was trained at that size.

Output includes selected routes, checkpoint hash and epoch, objective contract, environment completion, independent verification, seed, candidate count, software versions and timing. `model_setup_and_decode_s` is the native timed encoder/decoder section after environment reset; it excludes file loading and independent verification. `end_to_end_s` includes checkpoint/model loading, view/environment preparation, decoding and verification. CPU timing depends on the machine and is not a substitute for paper GPU timing.

All five real Road-100 models completed this command on view `iv_4073f1928fa0c95f3de64257` with 30 candidates and verified feasible selected routes. The measured decode times were approximately 0.93 s AM, 2.83 s EVRPTW-RL, 1.01 s TERRAN, 1.99 s RRNCO and 2.32 s DRL-TS (CPU, one Torch thread). Recorded outputs are in `examples/expected/*_road100_30.json`. These single-instance timings and results are engineering checks, not benchmark averages or a quality ranking; the checkpoint generations also use different objective-distance contracts.

## Training plumbing check on separate data

Generate the independent `demo/train` fixture using `scripts/generate_demo.py` as described in the generation documentation, or use the bundled generated fixture, then run:

```bash
python scripts/learning_smoke.py \
  --family-dir ../review-core/generation/generated_train/families/demo_family_train_000 \
  --view-id demo_train_000 --seed 1234 --output outputs/learning_smoke.json
```

The check uses eight customers, two stations, CPU and the full recorded Road-100 architecture for each method. It initializes fresh diagnostic models, runs differentiable native rollouts (TERRAN uses an actor/critic transition), checks finite nonzero gradients, and performs one Adam update. It reports the number of changed parameter tensors and writes no model checkpoint. This is explicitly a forward/backward/optimizer check. Its generic diagnostic loss does not reproduce each method's native baseline, PPO schedule, staged shaping or complete training protocol. All five checks passed. Benchmark test views are rejected by this script; no training used the 22 real review views.

## Full training and evaluation

The 20 files `configs/training/<artifact_id>.json` record checkpoint-observed training parameters and explicitly identify unresolved external data inputs. They are source-configuration records, not self-contained training archives. Fields written as `<external:...>` must be bound to the appropriate dataset index, materialized families, training-ID stream, reward calibration or initialization artifact. Do not substitute the small review test package for a training corpus. Do not claim the inference-only exports resume optimizers or reproduce a source run's data order.

Native entrypoints, shown as Python modules, are:

| Method | Training module | Evaluation module |
|---|---|---|
| AM-EVRPTW | `EVRPTW_Benchmark.Reinforcement_Learning.AM_EVRPTW.train` | `EVRPTW_Benchmark.Reinforcement_Learning.AM_EVRPTW.eval` |
| EVRPTW-RL | `EVRPTW_Benchmark.Reinforcement_Learning.EVRPTW_RL.train` | `EVRPTW_Benchmark.Reinforcement_Learning.EVRPTW_RL.eval` |
| TERRAN | `EVRPTW_Benchmark.Reinforcement_Learning.TERRAN.train` | `EVRPTW_Benchmark.Reinforcement_Learning.TERRAN.eval` |
| RRNCO | `EVRPTW_Benchmark.Reinforcement_Learning.RRNCO_EVRPTW.train` | `EVRPTW_Benchmark.Reinforcement_Learning.RRNCO_EVRPTW.evaluate_checkpoint` |
| DRL-TS | `EVRPTW_Benchmark.Reinforcement_Learning.DRL_TS.train` | `EVRPTW_Benchmark.Reinforcement_Learning.DRL_TS.eval` |

Run a module with `python -m <module> --help` to inspect its exact inputs. The four non-TERRAN trainers take CLI arguments; use the corresponding record's `recorded_arguments`. TERRAN takes `--config`, `--seed` and optional overrides; its `native_config_template` supplies the recorded native JSON layout. The native evaluation entrypoints expect their original training-checkpoint format. Use `scripts/learning_demo.py` for the cleaned inference-only format supplied here.

A representative AM native training invocation, after preparing a genuine training corpus and its separate validation split, is:

```bash
python -m EVRPTW_Benchmark.Reinforcement_Learning.AM_EVRPTW.train \
  --dataset-path "$DATA_ROOT/generation_plan/core/train/view_index.parquet" \
  --family-root "$DATA_ROOT/materialized/families" --scale Cus100 \
  --split-ids train --track-ids train --training-representation G \
  --objective-config EVRPTW_Benchmark/Reinforcement_Learning/configs/rivian_energy_vehicle_cost_v2.json \
  --seed 1234 --device cpu --output-dir outputs/am_training
```

This illustrates the native interface only; a full reproduction must apply every selected configuration's rollout budget, optimization settings, calibrated reward contract, ordered training stream, validation selection rule, stopping rule and curriculum initialization. In particular, it must choose the exact objective-distance contract rather than assuming the illustration's historical profile matches later curriculum runs. Euclid-100 native data requires either its frozen synthetic corpus or the specified calibrated Euclidean representation; it is not obtained by relabeling road matrices.

Full 20-configuration training, all-paper evaluation, exact resume and large-scale GPU performance measurements are **NOT RUN** for this local bounded delivery. The repository preserves those implementations and records their inputs; the review bundle demonstrates loading, physical validation, real inference and training gradients.

## Checkpoint and attribution audit

`examples/expected/checkpoint_acceptance.json` reports strict-load, tensor-identity and fixed-seed output equivalence for all 20 artifacts. The AM Road-100 pre/post-cleaning comparison uses the real 100-customer view and 30 candidates. The other 19 comparisons use the separate eight-customer fixture with two candidates to test export fidelity; they do not measure the model's target-scale quality. Route lists, completion, served-customer counts, distance and dispatch counts matched exactly before and after metadata cleaning.

AM's vendored attention encoder retains its MIT license. RRNCO's upstream architecture attribution and MIT license remain in its `third_party` directory. TERRAN's public upstream revision `926665870d08e24b1acea33a57f1412c96376758` is licensed Apache-2.0; the complete license and adaptation description are in `TERRAN/third_party/terran`. Public third-party attribution remains visible even when a name overlaps a submitter's identity. This is necessary attribution, not a workstation identity leak.
