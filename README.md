# EVRP-TW-D/B

Road-based electric-vehicle routing instances, a two-stage generator, and eight routing solvers.

For offline checks using the compact submission ZIP, start with [Reviewer quickstart](REVIEW.md). The larger delivery described below contains more data and weights than the compact ZIP; each package lists its actual contents.

**The small-sample training demo checks that the shared model, rollout, loss and optimizer code runs. It does not establish full-dataset or full-batch training, convergence, or paper performance.** Choose the path you need:

| Task | Start here |
|---|---|
| Run the small-sample training demo | [Install](#install) → [Step 2](#2-run-the-training-workflow-demo) |
| Evaluate supplied weights and verify routes | [Install](#install) → [Step 3](#3-evaluate-a-checkpoint-and-draw-its-routes); no generation or training is needed |
| Generate road instances | [Install](#install) → [Step 1](#1-download-source-data-and-generate-instances) |
| Prepare full data and run native training | [Install](#install) → [Step 4](#4-prepare-full-data-and-use-native-training) |

## Install

Use Python 3.11. Extract the three bundles as sibling directories: `evrptw-db/` (code), `review-core/` (evaluation data), and `review-checkpoints/` (genuine weights). Step 3 reads its instance directly from `review-core/`.

```bash
cd evrptw-db
python3.11 -m venv .venv
. .venv/bin/activate
python -m pip install torch==2.5.1 --index-url https://download.pytorch.org/whl/cpu
python -m pip install -e '.[learning,geographic]'
```

Step 1 also needs the `osmium` executable: install it with `conda install -c conda-forge osmium-tool` (or your system package manager). Steps 2 and 3 do not need this tool.

The source includes two **Road-100 training examples** for the runnable demonstration. Evaluation uses a separate real **Road-100 test view from `review-core/`**. Both commands work offline after installation and use EVRPTW-D road matrices.

## 1. Download source data and generate instances

Only the AFDC charging-station source needs an API key. Set it in your shell; the other configured sources use public downloads:

```bash
export NLR_API_KEY='your_api_key'
bash generate.sh --city "Fort Worth" --state TX --count 2 --scale 100 \
  --output outputs/generated
```

This downloads missing source inputs into a reusable cache, builds the city environment (**Stage 1**), and generates road instances (**Stage 2**). The first run includes city/state source downloads even when generating only a few instances. Later runs reuse the cache. Use `--dry-run` to inspect the inputs and stages before downloading.

| Parameter | Meaning | Example |
|---|---|---|
| `--city`, `--state` | US city and state code; defaults `Fort Worth`, `TX` | `--city "Fort Worth" --state TX` |
| `--count` | Number of instances; default `2` | `--count 10` produces 10 instances |
| `--scale` | Customers per instance; default `100` | `--scale 100` gives 100 customers each |
| `--seed` | Random seed; default `1234` | Keep it fixed to repeat a configuration |
| `--output` | New data directory; default `outputs/generated` | `--output outputs/road100` |
| `--cache-dir` | Reusable cache; default `generation-cache/` beside the source | Share this across generation runs |
| `--dry-run` | Show the workflow without downloading or generating | Add to any command above |

The configurable small run uses the retained generation modules; it does not reproduce the complete fixed paper cohort. Source-quality checks and the full-generation protocol are documented in [generation](docs/GENERATION.md).

## 2. Run the training workflow demo

No generation run or API key is needed to use the included training samples:

```bash
python train.py --model evrptw_rl --scale 100
```

The default is **5 epochs**, with each epoch visiting both included training instances. The terminal shows one run summary, the loss for each epoch, and the saved checkpoint path. Detailed updates remain in `loss.jsonl` and `summary.json`. **Scope:** this tiny sample only demonstrates that the training program runs. It uses the same model, rollout, loss and optimizer components as the training framework, but does not reproduce the full training data or batch configuration. Its losses and checkpoint are not evidence of convergence or paper-level performance.

| Parameter | Meaning |
|---|---|
| `--model` | `evrptw_rl`, `am`, `terran`, `rrnco`, or `drl_ts` |
| `--scale` | Customer count; the included training sample is `100` |
| `--epochs` | Number of passes over the sample; default `5` |
| `--data-dir` | Your matching road-training sample directory, when supplying other data |
| `--output` | Optional new output directory; otherwise a fresh directory is created automatically |
| `--seed` | Seed for the short training run |

For example, `python train.py --model am --scale 100 --epochs 5` runs the AM training demonstration. See [training details](docs/TRAINING_AND_EVALUATION.md) for the original full-training entry points.

## 3. Evaluate a checkpoint and draw its routes

Use a supplied genuine checkpoint and the Road-100 T1 test view in `review-core/`:

```bash
python eval_plot.py \
  --ckpt ../review-checkpoints/am_evrptw_road_100.pt \
  --inst_path ../review-core/materialized/families/mf_f00002829bd8a1180a26e4cb/views/iv_4073f1928fa0c95f3de64257/view_manifest.json
```

The model is identified from the checkpoint and the scale from the instance. Open `routes.svg` in the printed output directory; `result.json` contains routes, cost and independent verification. You can also pass the checkpoint saved by `train.py`.

| Parameter | Meaning |
|---|---|
| `--ckpt` | Checkpoint file to load |
| `--inst_path` | Instance JSON, or a generated view directory / `view_manifest.json` |
| `--candidates` | Number of sampled candidates; default `30` |
| `--output` | Optional new output directory |
| `--annotate` | Add terminal numbers to the figure |

The figure shows terminal visit order; straight segments are not road-path geometry. Distance and feasibility use the instance matrices. If no complete verified solution is found, the command saves diagnostics and exits with code `2` without a successful-route plot.

## 4. Prepare full data and use native training

Follow [full Stage 1 and Stage 2](docs/GENERATION.md#full-stage-1-and-full-stage-2) for data preparation, then [full training and evaluation](docs/TRAINING_AND_EVALUATION.md#full-training-and-evaluation) for the original method-specific trainers and configurations.

`generate.sh` produces engineering samples, and root `train.py` runs the small-sample demo. Increasing `--count` or `--epochs` does not turn these into paper reproduction. Full training requires the formal data splits and indices, the matching source/calibration inputs, and each method's configuration supplied to its native training entry point. Full training and complete cohort reproduction remain **NOT RUN** in this delivery.

---

[Data and format](docs/DATASET.md) · [Eight solvers](docs/BASELINES.md) · [Tests and acceptance](docs/ACCEPTANCE.md) · [Data availability](docs/DATA_AVAILABILITY.md) · [Licensing and attribution](docs/LICENSING.md)

The delivery contains source, review materials and genuine weights. Full historical experiment records are excluded. Detailed reproduction boundaries and pending publication checks remain in the linked documentation.
