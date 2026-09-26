# Quick-demo execution examples

These files were produced by the commands in [QUICK_DEMOS.md](../../../docs/QUICK_DEMOS.md) using Python 3.11.13 and PyTorch 2.5.1+cpu with one CPU thread, seed 1234 and network connections blocked after installation.

- `training/`: eight actual optimizer updates on the separate source-bundle engineering training fixture; the generated demo checkpoint is intentionally not distributed here. Run quick training to create it.
- `evaluate_demo/`: the checkpoint produced by those eight updates, evaluated on the same training fixture. This checks the integration and is not held-out evaluation.
- `evaluate_real_am/`: the genuine released AM-EVRPTW Road-100 checkpoint on review view `iv_4073f1928fa0c95f3de64257`, with 30 sampled candidates and independent verification.

Open either `routes.svg` in a browser to see the vehicle routes and hover over a vehicle legend for its visit order. Straight lines connect terminal coordinates; they do not reconstruct real road geometry. Resource feasibility and objective values use the instance matrices.

Timing, checkpoint serialization hashes and stochastic outputs can vary across environments. These are small execution examples, not historical experiment logs or full paper tables. Data provenance and scope follow [DATA_AVAILABILITY.md](../../../docs/DATA_AVAILABILITY.md).
