# Common benchmark contract

The current monetary profile is [objective.json](../configs/paper/objective.json), copied without rounding from the retained implementation:

`C = 413.6331536717643 × K + (0.39 × 0.38910505836575876) × D`.

`K` counts nonempty single-trip vehicle routes. `D` is the sum of **running_time_path_distance_km**, the distance along the fastest-time paths. Scheduling uses `running_time_shortest_matrix_s`, and battery use uses `running_time_path_energy_kwh`. The distinct `distance_matrix_km` is the shortest-distance matrix and must not silently replace `D`. `select_objective_distance` requires the proper matrix and retains the legacy matrix separately. Matrices are directed and may be asymmetric. The loader's existing numeric casts are retained; bundle equivalence compares original and packaged loader outputs, with raw numeric artifacts unchanged.

The task has homogeneous vehicles, unlimited fleet cardinality, one depot-to-depot trip per vehicle, hard customer service-start windows, cargo capacity, battery capacity, full linear recharge and return within the operating horizon. Charging duration is missing battery energy divided by station power times the instance's derating factor, converted from hours to seconds. Depot index is 0, customers are 1 through n, stations follow. Each customer appears exactly once. Internal depot visits, empty-customer routes, missing/duplicate customers, invalid indices and nonfinite route arcs are rejected.

The independent implementation is `EVRPTW_Benchmark/Exact/Gurobi_Solver/route_validator.py`; it imports no Gurobi. Its resource tolerance is `1e-5` in native units. The thin public reader rejects noninteger route indices before replay, without changing production feasibility. The common search adapter maintains its own aligned replay implementation; public solve output is independently rechecked by the exact-module verifier. Validating a solution does not certify fidelity to an algorithm's original unpublished implementation.

## Results and failures

Routes are JSON lists of lists, each starting/ending at depot 0. Review outputs record instance/config IDs, status, feasibility, cost, vehicle count, objective distance, measured time, timing boundary and diagnostics. Costs of invalid/missing solutions remain null. Completed feasible, no incumbent, invalid input, dependency error, timeout, OOM and unfinished rollout must not be merged into success. Candidate selection accepts only completed trajectories passing independent verification; an invalid later candidate must not erase an earlier valid incumbent.

Formal search budget is 1,800 seconds per instance. Gurobi uses finite charger copies (default two per station); this is an approximation restriction. ALNS and VNS/TS retain their full-charge operators, certificate warm starts and initialization. Learning shares a station-revisit action mask; DRL-TS adds its own action limitations. These restrictions are not relaxed for the demo.

Learning's current final target is 30 complete sampled candidate route sets per instance, followed by feasible minimum-cost selection. Checkpoint validation and archived tests may have different settings; the bundle records those actual values. Current inference does not make archived 100-candidate evaluations equivalent to 30-candidate tests.

FR is verified solutions divided by all expected positions in the specified cohort. Missing and failed rows stay in the denominator. The report's main-quality column is absent unless the entire cohort has FR=1. Runtime averages require measured values for all expected positions and preserve the recorded boundary/batch semantics. A budget is never used as a substitute for measurement. Comparing batch-amortized time with batch-1 return latency requires a separate declared protocol.

BKS is a frozen disclosed per-instance reference pool, not an optimality certificate. This delivery does not include full experiment tables or a frozen BKS. The reporting tool leaves gaps blank when the required BKS values are absent. The new demo does not update BKS. A documented three-model Cus1000 snapshot cannot be described as the requested five-model headroom seed pool. No new 7,200-second headroom run was performed.
