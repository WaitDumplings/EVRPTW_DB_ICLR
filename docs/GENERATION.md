# Generate road instances

The main entry is `bash generate.sh`. It acquires the public inputs for one U.S. city, calls the retained Stage-1 CLE builder, then calls the retained Stage-2 road-state, directed-routing, Amazon order-matching, attribute and independent-certificate modules. `--count N` produces exactly N instances at the requested customer scale, with one view per family and no extra nested views.

These are **independent engineering samples**, not a regeneration of the paper's fixed 11-city cohort. The complete official planner, C3 gates and approval/provenance rules remain available and unchanged. This simpler entry uses its own explicitly unapproved engineering profile, preserving the reference vehicle/energy/charging values. It selects a real Amazon weekday from the frozen training pool, uses one eligible depot and nearby eligible customer/charger pools, and keeps the complete city road graph. It omits official CBG splits, spatial structure matching, region-first cohort selection and statistical cohort acceptance. These boundaries and any Stage-1 manual-review blockers remain in generated manifests and `generation_report.json`.

## Install and run

From the source repository, install the geographic Python dependencies and the one required external executable:

```bash
python -m pip install -e '.[geographic]'
conda install -c conda-forge osmium-tool
```

An equivalent system installation of `osmium-tool` is acceptable; `osmium --version` must work in the shell running generation. Python ZIP/network libraries handle the other downloads. No AWS CLI, AWS account, GPU, checkpoint archive or review-core archive is required for online generation.

Obtain a key from the [NLR Developer Network signup page](https://developer.nlr.gov/signup/). AFDC is the only source in this acquisition path that needs a developer key. The legacy environment name `NREL_API_KEY` is also accepted. Keep the actual key in your environment, not source/config files:

```bash
export NLR_API_KEY='your-developer-key'
bash generate.sh --city 'Fort Worth' --state TX --count 2 --scale 100 --output outputs/generated
```

Inspect the planned sources without making requests, creating files or supplying a key:

```bash
bash generate.sh --city 'Fort Worth' --state TX --count 2 --scale 100 --dry-run
```

A first city build downloads state-scale geography even when requesting two instances. The three Amazon JSON inputs alone had a combined HTTP Content-Length of 2,271,556,331 bytes when checked on 2026-09-25. The build also uses state OSM/building archives and city infrastructure; downloading, extraction and full-city CLE construction can be substantial. This delivery did not run the complete online acquisition/Stage-1 chain.

| Parameter | Default / meaning |
| --- | --- |
| `--city`, `--state` | `Fort Worth`, `TX`; a U.S. Census Place and state abbreviation, name or FIPS |
| `--count` | `2`; positive integer, exact number of output instances |
| `--scale` | `100`; customers per instance, integer 1–2000 |
| `--seed` | `1234`; integer 0–4294967295 |
| `--output` | `outputs/generated`, relative to the invoking working directory; must be new |
| `--cache-dir` | `generation-cache` beside the source repository; reused public inputs and CLE work |
| `--workers` | `1`; family workers and Stage-1 NSI download workers |
| `--stations` | Optional override; otherwise 20 at scale 100, 50 above 100, and `max(1, min(10, scale // 4))` below 100 |
| `--dry-run` | Display source URLs and stages; no network, writes or key required |
| `--cached-fixture` | Explicit offline Stage-2-only test, described below |

Paths with spaces are supported. The source tree is not used as the raw-data cache. City work and CLE caches are separated by state and city, so identically named cities in different states do not share their geographic inputs. Source data live under `<cache>/sources/<state>/`; Amazon inputs use `<cache>/sources/amazon-last-mile-2021/`. Outputs contain `families/`, `instances.jsonl`, `generation_config.json`, `generation_profile.json` and `generation_report.json`. Each `instances.jsonl` row gives a `view_manifest` path relative to the output directory. Pass that actual file to the evaluation entry's `--inst_path` option. The family stores all four directed matrices and the actual view-specific attributes/certificates.

A stage failure exits nonzero and records `status: FAIL`, the failing stage and diagnostic in `generation_report.json`. Partial outputs are not counted as successful instances. A rerun needs a new `--output`; existing outputs are never silently overwritten. Cached source inputs are reused, and new S3 downloads are streamed atomically with checksums. No failed online stage falls back to the bundled fixture.

## Public source endpoints

The dry run prints the concrete URLs for the chosen state. The production acquisition chain uses:

- [Census TIGER/Line 2025](https://www2.census.gov/geo/tiger/TIGER2025/) Places, counties and intersecting AREAWATER archives.
- [Geofabrik U.S. OSM extracts](https://download.geofabrik.de/north-america/us.html) and [Microsoft U.S. Building Footprints](https://github.com/microsoft/USBuildingFootprints) state archives.
- [FHWA geospatial services](https://geo.dot.gov/server/rest/services/Hosted/) for public HPMS road attributes.
- [AFDC All Stations API](https://developer.nlr.gov/docs/transportation/alt-fuel-stations-v1/all/), using the exported key; [Census address geocoding](https://geocoding.geo.census.gov/geocoder/) and OSM charger POIs provide coordinate evidence.
- The retained NSI public endpoint `https://nsi.sec.usace.army.mil/nsiapi/structures` for city-tiled building attributes, without a separate token in this code path.
- [Amazon Last Mile Routing Research Challenge](https://registry.opendata.aws/amazon-last-mile-challenges/) public S3 training inputs plus its license/readme. This wrapper uses public HTTPS object URLs, not AWS credentials or AWS CLI.
- The bundled compact MOVES5 speed profile; the full MOVES simulator/database is not downloaded.

Provider availability, snapshot changes and manual site-quality checks remain separate from successful computation. Data terms and source attribution are in [LICENSING.md](LICENSING.md). A successful sample does not clear manual CLE review labels or establish that an operational delivery site was manually verified.

## Offline test of the new entry

A compact, checksummed real-road CLE fixture is included in the source package. Request a scale it actually supports:

```bash
bash generate.sh --cached-fixture examples/generation/fixture --count 2 --scale 8 --output outputs/offline-generated
```

This command needs only the core Python dependencies. It explicitly records Stage 1 as `NOT RUN`; it makes no network requests and needs no key or osmium. The fixture has 48 customer candidates and four station candidates. A default scale-100 request against it fails instead of substituting fewer customers. The new entry was tested with one and two workers: an exact three-instance request produced identical IDs, indices and scientific hashes; scale one, seed boundaries, checksum failures, existing-output protection and credential-free logs were also checked. A separate read-only test loaded the existing complete Fort Worth CLE and Amazon artifacts through the strict production reader, built a 400-customer/40-station candidate pool, and generated one 100-customer/20-station instance on the full city graph with passing independent certificates. That test did not rebuild Stage 1 or download source data. The full online download → fresh Stage 1 → sample sequence remains **NOT RUN** in this delivery. The source tree also retains the earlier two-family/nested-view demonstration below; its output counts differ intentionally.

## Earlier bounded cached-CLE demo

The offline demo starts from a compact cached City Logistics Environment (CLE). It generates new views with the production Stage-2 road-state, directed-routing, order-matching, attribute and certificate modules. It does not copy an existing evaluation instance. It does not rebuild Stage 1 or run the complete official Stage-2 cohort-selection pipeline.

### Run the earlier offline demo

Extract the code and review-core archives beside each other. From `evrptw-db/`, install the core package as described in the README, then run:

```bash
python scripts/generate_demo.py --output-dir outputs/generated-demo --workers 1
python scripts/generate_demo.py --output-dir "outputs/generated demo parallel" --workers 2
```

No API key, internet connection, Gurobi or GPU is used. Existing family directories are not overwritten. `--fixture` and `--config` accept alternate paths. The default inputs are `../review-core/generation/fixture/` and `configs/demo/generation.json`; input file checksums are checked before computation.

Expected output is two families, each with an eight-customer/two-station parent and a four-customer/one-station nested view. IDs are `demo_demo_000`, `demo_demo_000_nested`, `demo_demo_001`, and `demo_demo_001_nested`. Each family contains directed matrices, a terminal table, view indices, customer/charging attributes and a verification report. `generation_report.json` must report `status: PASS`.

For a separate learning smoke fixture:

```bash
python scripts/generate_demo.py --split train --output-dir outputs/generated-train --workers 1
```

The `demo_train_*` IDs, random stream and artifacts are distinct from the supplied 22 evaluation views and from `demo_demo_*`. The train and demo engineering fixtures use a common small source pool; they are not statistically independent benchmark splits. The pre-generated train fixture is included at `../review-core/generation/generated_train/` for the learning smoke checks.

## Included inputs and generation boundary

The fixed Fort Worth fixture contains 184 road nodes, 304 directed edges, one depot candidate, 48 eligible customer candidates, four charger candidates, and 128 derived Amazon order templates from `DAU1:2018-07-20`. The terminal pool was selected before running any solver: the first eligible depot by stable source ID, followed by nearby eligible customer/charger candidates. The road crop retains directed access anchors and the union of shortest-distance and reference weekday/weekend time paths connecting those anchors to a fixed hub, plus original edges between retained nodes. Original geographic coordinates, access-edge offsets and order-template IDs remain scientific source fields.

Cropping changes geographic coverage, available alternative paths and the edge distribution used for connector-speed calculation. This fixture demonstrates engineering behavior, not the full-city distribution or paper benchmark quality. Source attribution and terms are in [LICENSING.md](LICENSING.md).

The wrapper calls the retained production functions:

1. `build_family_road_state` with the frozen weekday profile;
2. `PhysicalRoadNetwork.route_terminals` to calculate all four directed matrix families;
3. `match_amazon_order_templates` to assign real derived package/service/window templates;
4. `view_parent_terminal_indices` for nested customer sets and road-time-based child station selection;
5. `build_view_attributes_from_amazon` for each actual view and its station roster;
6. `verify_materialized_family` to check storage, matrices and recompute each view's single-customer feasibility certificate.

Whole-city Census block-group splits, spatial structure matching, joint-support gates, region-first family selection and official Phase-1 statistical acceptance are omitted from this bounded demo. Manifests therefore use `review_engineering_subset_v1`, `non_release_pilot: true` and `scope: engineering_demo_not_benchmark_cohort`. The official benchmark loader deliberately does not treat this contract as an official evaluation cohort.

`configs/demo/generation_profile.json` retains all scientific values from the selected release profile. Only internal approval/provenance metadata was removed. Operating hours are 08:00–24:00 in seconds. Directed fastest-path time controls scheduling; distance along that same fastest path controls energy. The four-customer child recomputes its certificate using its one-station roster rather than inheriting a certificate from the two-station parent. These tiny examples need no charging on their single-customer certificates; they do not demonstrate a charging-required case.

The source CLE still records six manual review blockers: `microsoft_nsi_geometry`, `customer_road_access_review`, `depot_release`, `charging_coordinate_validation`, `charging_release`, and `delivery_communities`. A numerical demo PASS does not clear these source-quality blockers or establish a manually validated operational deployment dataset.

## Determinism and observed checks

`../review-core/generation/multiprocessing_check.json` records exact equality of loaded scientific payloads and terminal dataframes for one versus two workers, including all arrays, resources, source IDs and certificates. Wall-clock/routing timings and directory locations are excluded. Stored certificate energy margins were deliberately changed in memory, and independent recomputation rejected the changes. A directory containing spaces was used successfully.

On the recorded Python 3.11.13 / NumPy 2.3.5 / pandas 2.3.3 environment, the generation timer measured about 0.17 seconds with one worker and 1.07 seconds with two workers for two tiny families. The timer excludes Python startup and input-manifest reading; these values are not solver inference times or full-cohort throughput estimates. Process startup dominates this tiny workload. A second run in the newly installed clean environment (pandas 3.0.5) also passed with exactly the same loaded scientific payloads; see `../review-core/generation/clean_environment_check.json`.

After the two commands above, compare the stable scientific digests:

```bash
python - <<'PY'
import json
from pathlib import Path
roots = [Path('outputs/generated-demo'), Path('outputs/generated demo parallel')]
values = []
for root in roots:
    report = json.loads((root / 'generation_report.json').read_text())
    assert report['status'] == 'PASS'
    values.append({r['family_id']: r['scientific_sha256'] for r in report['families']})
assert values[0] == values[1]
print('PASS: one and two workers give identical scientific payloads')
PY
```

The hashes compare numerical content, not compressed-file byte layout or timing metadata. Pre-generated outputs are inspection examples; new runs should use new output directories.

## Full Stage 1 and full Stage 2

Production entries are retained:

```bash
python EVRPTW_Dataset_Generator/scripts/generate_us_city_cle.py --help
python EVRPTW_Dataset_Generator/scripts/build_stage2_instances.py --help
```

The first builds city boundaries/configurations, obtains OSM/building/NSI/AFDC and other configured source layers, and constructs the CLE. It requires the optional geographic dependencies, source downloads/caches and provider access where applicable. `--prepare-only` prepares city configuration/boundaries and is not an end-to-end CLE build. The second accepts frozen CLE, Amazon calibration artifacts, cohort configuration and the reference profile, then executes plan/materialize/verify/metrics stages under the production run discipline. See its complete `--help` before selecting inputs or run mode.

The offline fixture omits original national/state raw inputs, full-city support layers and official cohort inputs. Full Stage 1, a raw-input Stage-1 mini demonstration, and complete cohort regeneration are **NOT RUN** in this delivery. A faithful compact raw-input Stage-1 fixture was not assembled. The preserved entry points and provider acquisition links are available for separately provisioned full inputs; the small cached demo must not be reported as a full two-stage reconstruction.

### Optional clean work copy for full generation

The retained full Stage-2 runner requires a clean Git revision and its expected generation branch. The delivery archives contain no `.git` directory. Create a **new** local work copy when provisioning a full generation run:

```bash
python scripts/prepare_generation_snapshot.py --output-dir ../evrptw-generation-work
cd ../evrptw-generation-work
python -m pip install -e '.[geographic]'
python EVRPTW_Dataset_Generator/scripts/build_stage2_instances.py --help
```

The preparation script copies the anonymous source, creates one new commit with per-repository identity `Anonymous Review <review@example.invalid>`, and uses the runner's required `stage2-repair-candidate` branch. It copies no original Git history and creates no remote. Choose a new destination; the script refuses to overwrite an existing directory. It excludes generated outputs, Python caches, virtual environments and package-install metadata. Store datasets and generated outputs outside the work copy, and commit any intentional source/config edits before using the full runner.

This preparation does not launch generation, clear CLE review blockers, or supply absent full inputs. The unchanged production provenance resolver accepted a fresh snapshot and rejected an untracked modification in the tested private work copy. The source identity is the new local commit, not an original private commit; different users can produce different commit IDs for the same source content.
