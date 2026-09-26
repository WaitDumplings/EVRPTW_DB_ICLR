# Dataset contract

EVRP-TW-D stores semi-synthetic delivery-day instances built from geographic/infrastructure layers and operational attribute templates. Public terminal coordinates and source identifiers describe scientific inputs; an assigned Amazon template does not mean Amazon delivered to that geographic customer location.

## Family, view and terminal identity

A matrix family contains the directed road-state matrices and the parent terminal roster. A view specifies an ordered subset of parent terminal indices, a customer count and its actual charging-station roster, together with delivery attributes and a feasibility certificate. `family_id` binds shared road state; `view_id` identifies the exact instance; terminal `source_id` identifies a geographic candidate. Order-template IDs are a separate namespace.

The local terminal order is depot at index 0, customers at indices `1..n`, then non-depot charging stations at `n+1..n+m`. Matrix row `i`, column `j` means directed travel from `i` to `j`. The reverse arc need not have the same distance or duration. Routes use these local terminal indices, not parent indices or geographic source IDs.

The reader reconstructs a view by slicing parent matrices with `terminal_parent_indices` in the manifest order. The review bundle retains original float32 matrices. It does not round values, convert dtype, or regenerate routes to reduce storage.

```python
from evrptw_stage2.artifacts import load_materialized_view

family = '../review-core/materialized/families/mf_f00002829bd8a1180a26e4cb'
view = load_materialized_view(family, 'iv_4073f1928fa0c95f3de64257')
assert len(view['customers']) == 100
assert len(view['charging_stations']) == 20
assert view['running_time_shortest_matrix_s'].shape == (121, 121)
```

## Fields and units

| Field | Meaning | Unit |
| --- | --- | --- |
| `distance_matrix_km` | Length of a shortest-distance road path | km |
| `distance_path_travel_time_s` | Travel time along that shortest-distance path | s |
| `running_time_shortest_matrix_s` | Minimum running time over admissible directed road paths | s |
| `running_time_path_distance_km` | Distance along the path attaining that running time | km |
| `running_time_path_energy_kwh` | Fastest-path distance multiplied by frozen linear consumption | kWh |
| `demands_cm3`, vehicle `cargo_capacity_cm3` | Package volume and vehicle volume capacity | cm³ |
| `service_time_s`, `tw_s` | Customer service duration and hard service-start window | s |
| `working_start_s`, `working_end_s` | Departure-day operating horizon | s |
| `charging_power_kw` | Effective station-side power before the profile's charging derating factor | kW |
| vehicle `battery_capacity_kwh` | Usable battery capacity | kWh |
| `full_cs_to_depot_time_s` | Minimum feasible return duration from a full-charge station state under the certificate model | s |

The current benchmark adapter uses `running_time_shortest_matrix_s` for scheduling and `running_time_path_distance_km` for energy and monetary cost. Do not use the shortest-distance matrix as the objective distance merely because its name is shorter. The coefficient file is `configs/paper/objective.json`; use its unrounded values. The homogeneous task uses single-trip vehicles, hard time windows, full recharge and no fixed fleet-size cap.

Successful materialization requires finite terminal-to-terminal physical matrices with zero diagonals. Missing/unreachable paths must not be replaced by zero. A feasibility-cache infinity represents an unreachable return state where allowed by the certificate model; NaN is invalid. Matrices remain directed even when a downstream model also uses geographic coordinates.

## Counts and splits

The inspected canonical release inventory contains 71,500 main views and 500 additional paired controls, with 7,500 families across 11 cities. These counts are reported in `../review-core/data_inventory.json`, not inferred from the small review sample.

| Cohort | Cus100 | Cus500 | Cus1000 | Cus2000 |
| --- | ---: | ---: | ---: | ---: |
| Training | 50,000 | 10,000 | 5,000 | — |
| Validation | 500 | 500 | 500 | — |
| T1: new delivery days in training locations | 500 | 500 | 500 | — |
| T2: held-out communities in training cities | 500 | 500 | 500 | — |
| T3: held-out Jacksonville | 500 | 500 | 500 | — |
| Unseen scale in training cities | — | — | 500 paired controls | 500 |

The main-view total excludes paired Cus1000 controls and legacy Cus50 views. Cus100 has 20 non-depot stations; Cus500 and larger use 50. Cross-scale comparisons involving Cus100 therefore also change the station roster. Unseen-scale Cus2000 and its control share a genuine parent family; they must not be paired by city or nearest cost.

## Review subset and validation

`../review-core/sample_manifest.json` freezes 22 original evaluation views: two per T1/T2/T3 × Cus100/Cus500/Cus1000 stratum, plus two Cus2000 views and their two exact Cus1000 controls. Seed `20260925` and SHA-256 of `seed:view_id` fix selection before solver results are examined. The subset covers eight cities and 20 families; it is not a representative performance study.

`../review-core/numerical_validation.json` records exact source-to-bundle array shape, dtype and value comparisons for all 22 views. Every single-customer certificate is recomputed from that view's actual matrices and stations. A smaller child does not inherit a certificate that assumes access to omitted parent stations.

Data validation and route validation have different roles. The former verifies a well-defined input and a sufficient individual-customer reachability certificate. The latter independently replays a complete route set and checks all task constraints. See [BENCHMARK.md](BENCHMARK.md). New `demo_train_*` and `demo_demo_*` views described in [GENERATION.md](GENERATION.md) are separate engineering artifacts, not added evaluation observations.
