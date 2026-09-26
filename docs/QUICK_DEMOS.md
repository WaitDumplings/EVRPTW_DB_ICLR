# Three reviewer commands

The [README](../README.md) is the main guide. These commands cover source acquisition and generation, short road-data training, and checkpoint evaluation with route plotting.

## Generate

```bash
export NLR_API_KEY='your_api_key'
bash generate.sh --city "Fort Worth" --state TX --count 2 --scale 100 \
  --output outputs/generated
```

`--count` controls instance count and `--scale` controls customers per instance. `--seed` controls random choices. `--cache-dir` lets repeated runs reuse downloaded source files. `--dry-run` prints the plan without downloading or generating. Only AFDC needs an API key; no AWS account or credentials are required for the public Amazon inputs.

This online path needs geographic Python dependencies and `osmium-tool`. It starts from source datasets and calls the two-stage generation modules. It is distinct from the optional old cached-CLE smoke demonstration. Source acquisition, exact output paths, quality checks and the full paper-cohort boundary are in [GENERATION.md](GENERATION.md).

## Training workflow demo

```bash
python train.py --model evrptw_rl --scale 100 --epochs 5
```

The bundled manifest is `examples/training/road_100/sample_manifest.json`. It selects two original `core/train` instances, each with 100 customers and 20 charging stations. Original view/family identifiers and train split are preserved. Neither is an evaluation view; the T1 protocol can share geographic source locations across different train/test views. See the [training sample README](../examples/training/road_100/README.md).

Each epoch is one pass over both training instances. Five epochs therefore perform ten optimizer updates. The terminal shows one line with the model, sample count, road scale, epochs and CPU device, followed by each epoch's loss and the final checkpoint path. Gradient norms, parameter changes and other update details remain in `loss.jsonl` and `summary.json`. `demo_checkpoint.pt` holds the resulting parameters with constructor/objective metadata and a strict reload check. This tiny sample demonstrates execution of the shared model, rollout, loss and optimizer code. It does not reproduce the full training corpus or batch configuration, and its losses/checkpoint do not establish convergence or paper performance. The checkpoint is the final update, without validation selection.

Choose `--model am`, `evrptw_rl`, `terran`, `rrnco`, or `drl_ts`. All use the retained full model architectures. The REINFORCE models use their native rollouts and cost losses; TERRAN uses its native PPO actor/critic loss. This small schedule omits the full training corpus, validation selection, baseline-refresh tests and scale curriculum; the exact differences are written to `summary.json`. Loss is stochastic and need not decrease every epoch.

`--scale 100` uses the included road sample. Other scales need a corresponding `--data-dir` with a validated original `core/train` road manifest; an unavailable scale fails explicitly. Instances are never reduced or relabeled to match a requested scale, and no Euclidean conversion occurs. Learning-rate, trajectory-count, thread and seed controls are listed by `python train.py --help`.

The default creates a fresh directory under `outputs/` and prints the checkpoint path. Use `--output outputs/my_training` for an explicit new directory. Existing directories are not overwritten.

## Evaluate and plot

```bash
python eval_plot.py \
  --ckpt ../review-checkpoints/am_evrptw_road_100.pt \
  --inst_path ../review-core/materialized/families/mf_f00002829bd8a1180a26e4cb/views/iv_4073f1928fa0c95f3de64257/view_manifest.json
```

This reads the actual family/view data and parent matrices from `review-core/`, and evaluates a genuine trained AM checkpoint on T1 test view `iv_4073f1928fa0c95f3de64257` (Chicago, 100 customers, 20 charging stations). Its view and family are separate from both training examples. Keep the `review-core/materialized/families/` hierarchy intact; `review-core/sample_manifest.json` lists the other available views. To inspect the model just trained, replace `--ckpt` with the printed `demo_checkpoint.pt` path; five epochs do not guarantee a feasible or high-quality solution.

`--inst_path` accepts a canonical instance JSON, a generated view directory, or its `view_manifest.json`. The model comes from the checkpoint metadata; the scale comes from the actual customer count. By default, 30 candidates are sampled and the decoding limit matches the native environment limit of four times the terminal count. `--candidates`, `--max-steps`, `--seed`, `--threads` and `--output` can override defaults.

The command strictly loads the requested weights, decodes candidates, selects the lowest-cost complete candidate that passes independent verification, and writes `result.json` plus `routes.svg`. The SVG uses distinct vehicle colors, arrows and depot/customer/station symbols. Hover over a vehicle legend for its full visit order. `--annotate` adds terminal numbers.

The drawing connects terminal positions with straight segments; it does not reconstruct roads. Verified objective, distance and resource use come from the declared instance matrices. The checkpoint's objective metadata is honored, including historical distance-contract differences in the real checkpoint inventory.

A missing or incompatible checkpoint is an error, with no random-weight fallback. If every candidate is incomplete or invalid, the command saves a failure result, returns exit status 2, and does not draw a successful-route SVG. The default output directory is fresh; an explicitly supplied existing directory is rejected.

## Evidence and scope

[ACCEPTANCE.md](ACCEPTANCE.md) separates executed CPU checks from unexecuted online/full-cohort paths. The final delivery report binds the tested extracted archive hashes. All demos are local; none reproduces the full paper training or benchmark protocol. Complete historical result records and frozen BKS remain outside the three-bundle delivery.
