# Small Road-100 training sample

This directory contains **two real EVRPTW-D road-network training views**, each with 100 customers, 20 charging stations and one depot. They are canonical exports of existing `core/train` views, not eight-customer fixtures relabeled as Road-100 and not Euclidean replacements. Their original identifiers, source split (`train`), family cohort (`core/train`), resource values and directed matrix values are preserved. `usage: review_training_demo` describes the packaged use; it does not rename the source split.

| Instance | City | Customers | Stations |
| --- | --- | ---: | ---: |
| `iv_38209784bbd529e20dcb731d` | Chicago | 100 | 20 |
| `iv_dbe0ddae27bf5257359dc80d` | Chicago | 100 | 20 |

The selection was fixed before consulting any solver outcomes: among the 50,000 `core/train` Cus100 views, sort by the hexadecimal SHA256 of the UTF-8 string `20260925:road100train:` followed by the view ID, then select the first two. Selection seeds, source-index checksum, per-file hashes and relative paths are recorded in [sample_manifest.json](sample_manifest.json). The existing small generation cache has only 48 customer candidates, so these examples were exported from the genuine training cohort rather than generated from that insufficient cache. This export does not claim a new full two-stage generation run.

The two views and their families are absent from every checked official evaluation/validation index and from the 22-view review sample. The original T1 protocol can share geographic source pools with training. One selected training view shares one customer source location with the 22-view sample; the other shares none. View/family separation therefore does not claim geographic holdout independence. No evaluation view is included in the training list.

## Loading

`sample_manifest.json` lists each input in `views[].instance_path`, relative to this directory. Each file is a standalone canonical instance JSON accepted by `EVRPTWInstance.from_dict`; no private source tree, NPZ helper or materialized parent family is required.

```python
import json
from pathlib import Path
from evrptw_core.schema import EVRPTWInstance

root = Path('examples/training/road_100')
manifest = json.loads((root / 'sample_manifest.json').read_text())
instances = [
    EVRPTWInstance.from_dict(json.loads((root / row['instance_path']).read_text()))
    for row in manifest['views']
]
assert all(instance.num_customers == 100 for instance in instances)
assert all(instance.metadata['split_id'] == 'train' for instance in instances)
```

The original shortest-distance matrix and fastest-time-path distance/time/energy fields remain distinct. Native training must select its explicit objective contract; these arrays are not replaced by coordinate distances. JSON retains exact source numeric values. The export adds usage/storage metadata and removes the workstation's absolute source-family path; private source provenance is retained outside the public package.

[verification.json](verification.json) records exact restoration checks for 31 array fields per view, finite nonnegative 121-by-121 matrices, directed asymmetry, recomputation of the view-specific feasibility certificates, and independent resource verification of the 100 singleton witness routes. These checks establish usable inputs and constructive feasibility, not learned-policy performance.

This small sample supports bounded training demonstrations. Two examples do not reproduce the full paper training corpus, learning curves, or benchmark quality. Original source attribution and data-use boundaries remain in [LICENSING.md](../../../docs/LICENSING.md).
