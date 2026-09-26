# Available materials and reproduction scope

This local review delivery contains **three bundles: source code (`evrptw-db/`), review-core (`review-core/`), and real inference weights (`review-checkpoints/`)**. Extract these as sibling directories. Complete historical experiment records and `paper-records/` are not included in this delivery while the authors update the records. No public hosting endpoint or downloadable full-corpus URL has been created. Each delivered archive's actual files, sizes and SHA-256 values are listed in the final delivery manifests.

| Material | Included locally | Scope |
| --- | --- | --- |
| Generator, task, verifier, solver and training/evaluation source | `evrptw-db/` | Preserved implementations plus portable review wrappers; method provenance limitations are disclosed in BASELINES and LICENSING |
| Road-only short-training sample | `evrptw-db/examples/training/road_100/` | Two original core/train Road-100 views, preserved scientific values and IDs; five-epoch native-loss demos |
| Optional canonical-format export (not used by the main evaluation command) | `evrptw-db/examples/evaluation/road_100.json` | Original T1 test view, copied from the 22-view review-core sample; disjoint training view/family IDs |
| Embedded quick-training fixture | `evrptw-db/examples/quick_train/` | Independent 8-customer demo/train family; code-only quick training and checkpoint-to-route integration |
| Evaluation inputs used by `eval_plot.py` in the README | `review-core/materialized/` | 22 views from 20 families, with exact original matrices and attributes; the README selects one genuine Road-100 T1 test view |
| Frozen selection and input evidence | `review-core/sample_manifest.json`, `numerical_validation.json`, `data_inventory.json` | Deterministic selection, exact numerical checks and canonical-release inventory |
| Historical routes | `review-core/routes/`, `route_inventory.json` | Available historical learning routes, including invalid and missing cases; their historical protocol differs from the current final protocol |
| Offline generation fixture | `review-core/generation/` | Compact cached CLE, real derived order templates, freshly generated engineering demo/train views and worker-consistency evidence |
| Model weights | `review-checkpoints/manifest.json` | Per-configuration availability and provenance govern; exported inference weights do not include all resume-training state |
| Complete experiment records and frozen BKS | Not included | Authors must supply the aligned records, full cohort/configuration manifests and disclosed frozen reference separately; no release date or download location is promised |
| Full canonical instance corpus | Not included | 71,500 main views plus 500 controls in the inspected inventory |
| Full original Stage-1 raw inputs and frozen CLE caches | Not included | The online generate.sh downloads/cache selected city/state inputs under provider terms; source inputs are not bundled |

The inspected instance-release directory uses 169,073,085,130 logical file bytes (about 157.46 GiB) and 171,072,815,104 allocated bytes. This is a bounded filesystem measurement of that directory only, including existing legacy Cus50 artifacts; it excludes separately stored CLE graphs, raw geographic inputs and model checkpoints. It is neither the size of the review archives nor a measurement of every project dependency. The measurement method and scope are recorded in `data_inventory.json`.

The current three bundles cannot reconstruct the complete paper tables or figures. The source reporting interface remains available and its aggregation rules are tested, but complete aligned result records and frozen BKS are separate required inputs. [REPRODUCING_RESULTS.md](REPRODUCING_RESULTS.md) describes an explicitly user-supplied-input template; it does not depend on an absent records package for the default review workflow.

A complete scientific rerun additionally needs the exact frozen CLE/source/calibration snapshots and full train/validation/test manifests, all intended checkpoint identities, the final evaluation protocol and compute budgets. Provider links below obtain data sources; current downloads are not guaranteed to reproduce older frozen snapshots. Do not substitute newly downloaded maps, change station rosters, regenerate matrices or silently fill missing result rows and call the result the paper corpus.

## Planned full dataset release

We plan to release the complete dataset publicly on Hugging Face with the
camera-ready version.
The Hugging Face dataset URL and version identifier will be added when available.
The current review packages contain the documented subsets; no full-dataset
download link or DOI is available yet. Source-specific licensing obligations
continue to apply to the planned release.

## Source acquisition

| Provider | Input role and access |
| --- | --- |
| [OpenStreetMap](https://www.openstreetmap.org/copyright) / [Geofabrik US extracts](https://download.geofabrik.de/north-america/us.html) | Directed road network and depot candidates; obtain the configured extract and preserve snapshot/hash |
| [Microsoft US Building Footprints](https://github.com/microsoft/USBuildingFootprints) | Building geometries used for customer candidates; state archives under upstream ODbL terms |
| [USACE NSI 2022 documentation](https://www.hec.usace.army.mil/confluence/nsi/technicalreferences/2022/technical-documentation) | Public structure attributes used in customer construction; do not replace public fields with restricted NSI fields |
| [U.S. Census TIGER/Line](https://www.census.gov/geographies/mapping-files/time-series/geo/tiger-line-file.html) | City boundaries and Census block groups; retain configured vintage and geographic identifiers |
| [AFDC data downloads](https://afdc.energy.gov/data_download) | Charging infrastructure snapshot; data download/API conditions apply, and API acquisition may require a user key |
| [EPA MOVES](https://www.epa.gov/moves/latest-version-motor-vehicle-emission-simulator-moves) | Frozen MOVES5-derived speed profiles; the full simulator/database is not bundled |
| [Amazon Last Mile 2021 dataset](https://registry.opendata.aws/amazon-last-mile-challenges/) | Operational templates derived from the published challenge data; CC BY-NC 4.0 applies |

The `generate.sh` entry point automates acquisition and the two generation stages for configurable engineering instances. It requires one AFDC API key and the geographic/system dependencies; public source downloads need no other credentials. The complete online path has not been executed in this local acceptance run. The cached test mode is explicit and does not stand in for raw-input reconstruction.

Source-specific terms and unresolved provenance are in [LICENSING.md](LICENSING.md). Stage-1 manual review blockers remain in the source metadata; numerical feasibility checks do not resolve them. A complete raw-input Stage-1 mini demo and full-cohort regeneration were not run; [GENERATION.md](GENERATION.md) states the precise cached-input boundary.

The small local package supports input inspection, historical-route replay, short CPU search, bounded generation and the documented weight-based inference checks. Full training convergence, all final 1,800-second comparisons and 7,200-second headroom studies are separate reproduction levels, not results established by the smoke checks.
