# Troubleshooting

- **Missing review data:** extract the review-core archive beside the code directory, not inside it. Use `--bundle` for another location. A manifest/hash mismatch is a failure: use the intact archive rather than editing expected checksums to hide corruption.
- **No torch/Gurobi/geographic package:** core replay/search deliberately needs none of these. Install the corresponding optional extra only for that path. A commercial license is obtained separately; none is bundled.
- **Torch CPU installation:** use the official PyTorch CPU package index for the documented version if the default wheel includes CUDA libraries. No GPU is required for the small inference smoke, but large policies/instances can be slow on CPU.
- **Out of memory:** reduce a demo batch or candidate chunk size only where the entry exposes it; keep the total formal candidate budget and report actual settings. Do not silently switch model/checkpoint or treat OOM as infeasible success.
- **Existing generation directory:** choose a fresh output directory. The generator deliberately refuses to overwrite an existing family.
- **Source release gate:** cached engineering generation is explicitly a non-release pilot. Full cohort generation requires its actual input manifests and recorded source-quality gates. See GENERATION for archive source-provenance mode.
- **Invalid recorded route:** read the violation list and retain the failure. Historical source `verified_feasible` is not a substitute for current independent replay. Some archived TERRAN routes contain customer-free trips rejected by the current strict verifier.
- **Different demo cost/time:** replaying the same input and route should match within the documented tolerance. Wall-clock search and cross-device sampling can select different valid routes. A changed objective or candidate budget requires a distinct experiment record.
- **Installing from an extracted folder with spaces:** quote paths as usual. The acceptance run uses such a directory. No private PYTHONPATH or original source symlink is needed. Python 3.11 is the tested interpreter.
- **Tests:** root `python -m pytest` runs the curated review contract tests. Additional retained research tests have optional learning/geographic/commercial prerequisites and are not all claimed as release acceptance.
