# Running tests

Use Python 3.11 and install the dependencies as described in
[REVIEW.md](../REVIEW.md). From the source root:

```bash
python -m pip check
python -m pytest
```

The root suite covers the review interfaces, data and checkpoint contracts,
objective consistency, verification, reporting, and bounded generation/training
workflows. For genuine-weight inference and independent route replay, follow
[REVIEW.md](../REVIEW.md). The archive's file manifests provide SHA-256 checksums.

## Optional native suites

```bash
python -m pytest EVRPTW_Dataset_Generator/tests
python -m pytest EVRPTW_Benchmark
```

Native tests have additional requirements. Geographic tests need geographic
dependencies; Gurobi tests need its optional package and an appropriate license;
GPU tests need CUDA. CPU distributed tests require local process-group
communication and operating-system shared memory. Run only where these facilities
are supported.

Some native integration tests require production cluster launchers or a historical
Git oracle that are not included in this source archive. Those tests explicitly
skip when their prerequisites are absent. No original Git history is included.
The production archive helper also depends on omitted launchers and a real Git
revision; use the documented review entry points for the supplied package.

Passing bounded tests does not establish training convergence, full-cohort paper
results, source-data reconstruction, or paper/checkpoint alignment. See
[reproduction scope](REPRODUCING_RESULTS.md) and
[data availability](DATA_AVAILABILITY.md).
