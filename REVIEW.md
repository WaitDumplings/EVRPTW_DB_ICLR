# Reviewer quickstart

The source supports dataset generation, eight solver implementations, independent
route verification, and reporting. The bundled examples support bounded CPU
checks; they do **not** reproduce complete paper tables or full training.

For the compact submission ZIP, start with its top-level `README.md`. It lists
the exact subset of data and weights actually included. The source documentation
also describes a larger delivery containing 22 evaluation views and 20 weights;
those counts do not apply to the compact ZIP.

## Install

From this directory, use Python 3.11 and a fresh virtual environment:

```bash
python3.11 -m venv .venv
. .venv/bin/activate
python -m pip install torch==2.5.1
python -m pip install -e '.[learning,geographic,test]'
python -m pip check
python -m pytest
```

On Linux, the CPU-only PyTorch wheel can instead be installed using
`python -m pip install torch==2.5.1 --index-url https://download.pytorch.org/whl/cpu`.
The review commands run on CPU. Gurobi and `osmium` are optional and are not
required below. Installation needs package access; the following checks work
offline afterward.

## Genuine checkpoint inference

```bash
python eval_plot.py \
  --ckpt ../review-checkpoints/am_evrptw_road_100.pt \
  --inst_path examples/evaluation/road_100.json \
  --candidates 30 --output outputs/review-am
```

This is a real T1 Road-100 evaluation view, separate from the two training
examples. Inspect `outputs/review-am/result.json` for routes and independent
verification, and `routes.svg` for terminal visit order. The straight SVG
segments are not road-path geometry. A missing/incompatible checkpoint is an
error; incomplete or infeasible inference exits with code 2.

The other Road-100 checkpoint names are `evrptw_rl`, `terran`, `rrnco`, and
`drl_ts`, followed by `_road_100.pt`. Their archived objectives differ:
AM-EVRPTW and EVRPTW-RL use fastest-time-path distance; the three historical
artifacts retain shortest-distance monetary objectives. The demos preserve each
checkpoint's contract and must not be used as an aligned five-method paper
comparison. See [checkpoint provenance](docs/TRAINING_AND_EVALUATION.md).

## Training and generation checks

```bash
python train.py --model evrptw_rl --scale 100 --epochs 5 \
  --output outputs/review-training
python scripts/generate_demo.py --fixture examples/generation/fixture \
  --output-dir outputs/review-generated --workers 1
```

Training performs ten updates on two genuine training views; it does not
establish convergence. Generation uses a small cached road graph and derived
delivery templates. It creates new engineering instances and verifies their
certificates, but does not rebuild the complete city layer or paper corpus.
Use fresh output paths when rerunning.

## Replay and bounded search

With the adjacent `review-core/` from either review distribution:

```bash
python -m evrptw_db.cli integrity ../review-core
python -m evrptw_db.cli inspect --bundle ../review-core
python -m evrptw_db.cli verify --bundle ../review-core \
  --routes ../review-core/routes/iv_4073f1928fa0c95f3de64257__am_evrptw__road_100.json \
  --output outputs/review-replay.json
python -m evrptw_db.cli solve --bundle ../review-core --seconds 10 \
  --output outputs/review-alns.json
```

The replayed route has one vehicle, 194.13879445940256 km and
443.09390458194605 USD under the current fastest-time-path objective.
The stored historical score is separately labeled. The 10-second solve is an
engineering check, not the paper's 1,800-second baseline comparison.

## Scope and terms

See [availability](docs/DATA_AVAILABILITY.md), [method sources](docs/BASELINES.md),
and [licensing](docs/LICENSING.md). Full aligned result records, frozen BKS,
training corpora, GPU timings, and exact optimizer-resume states are not supplied
by these demos. Final paper-to-checkpoint alignment and distribution permissions
remain explicit publication checks; running these commands does not certify them.
