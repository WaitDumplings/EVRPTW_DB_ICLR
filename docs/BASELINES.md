# Eight retained baseline implementations

Paths below are relative to `EVRPTW_Benchmark/`. These are benchmark adaptations; this release is not endorsed as an official EVRP-TW implementation by the cited method authors. Original training and inference code is retained alongside thin review wrappers.

| Method | Implementation and entry | Provenance and limitations |
|---|---|---|
| Gurobi | `Exact/Gurobi_Solver/gurobi_solver.py`, `run_gurobi.py` | Local MIP; requires separately installed Gurobi and valid license, finite station copies (default 2), 1,800-second formal cap |
| ALNS | `MetaHeuristics/ALNS_Solver/solver.py`, `run_alns.py` | Local literature-guided implementation, full-charge adaptation, certificate warm start, cost-aware removal/insertion/local search; no claim of importing authors' original implementation |
| VNS/TS | `MetaHeuristics/VNS_TS_Solver/solver.py`, `run_vns_ts.py` | Local variable-neighborhood/tabu implementation, full-charge replay, certificate and bounded consolidation, fast/full search profiles; initialization remains inside budget |
| AM-EVRPTW | `Reinforcement_Learning/AM_EVRPTW/` | Kool, van Hoof and Welling, *Attention, Learn to Solve Routing Problems!* (ICLR 2019); CVRP architecture adapted with EV resources and common action mask; upstream MIT notice/version retained |
| EVRPTW-RL | `Reinforcement_Learning/EVRPTW_RL/` | Lin, Ghaddar and Nathwani, *Deep Reinforcement Learning for the Electric Vehicle Routing Problem with Time Windows* (IEEE T-ITS); paper-guided local architecture/aggregation implementation, no verified original code claim |
| DRL-TS | `Reinforcement_Learning/DRL_TS/` | Chen et al., *Deep Reinforcement Learning with Two-Stage Training Strategy for Practical Electric Vehicle Routing Problem with Time Windows* (PPSN 2022); local implementation, two-stage training and additional action rules; exact paper-equation alignment not certified by these smoke checks |
| TERRAN | `Reinforcement_Learning/TERRAN/` | Adapted from the public TERRAN EVRP-TW source (Apache-2.0), with verified model-file lineage; shared environment, PPO/POMO-style rollouts and shaping. Upstream license and public repository attribution are retained under `TERRAN/third_party/terran/`; all four clean weights are included |
| RRNCO-EV | `Reinforcement_Learning/RRNCO_EVRPTW/` | Adaptation of [real-routing-nco](https://github.com/ai4co/real-routing-nco), MIT provenance retained: directed row/column road relations, D/T/E/bearing channels and EV resource context. Local training protocol/optimization changes are not upstream's unmodified POMO recipe |

AM source: [official repository](https://github.com/wouterkool/attention-learn-to-route) and [paper](https://arxiv.org/abs/1803.08475). EVRPTW-RL: [DOI](https://doi.org/10.1109/TITS.2021.3105232). DRL-TS: [chapter](https://doi.org/10.1007/978-3-031-14714-2_25). RRNCO publication is *Towards Real-World Routing with Neural Combinatorial Optimization* (ICLR 2026; see the primary citation in THIRD_PARTY_NOTICES). The exact ALNS/VNS-TS bibliography and final method descriptions require final-manuscript confirmation; no guessed citation is substituted.

## Full search entry points

With complete source data installed separately, from the repository root (replace the two explicit full-data paths):

```bash
python EVRPTW_Benchmark/MetaHeuristics/ALNS_Solver/run_alns.py   --dataset_path ../full-data/generation_plan/core/test/test1_new_seed/view_index.parquet   --family_root ../full-data/materialized/families --scales Cus100   --save_path outputs/alns-formal --num_workers 1 --time_limit_s 1800   --objective_config configs/paper/objective.json --seed 2026
```

Use `MetaHeuristics/VNS_TS_Solver/run_vns_ts.py` or `Exact/Gurobi_Solver/run_gurobi.py` with their verified `--help` parameters for the corresponding method. Always pass the objective explicitly when reusing historical entry points. These full runs were **NOT RUN** for release preparation. See [training/evaluation](TRAINING_AND_EVALUATION.md) for actual five-method interfaces and per-checkpoint configuration. CPU ALNS smoke is tested; optional Gurobi and full VNS/TS evaluation are not certified by that test.
