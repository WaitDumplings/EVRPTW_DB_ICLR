# CPU quickstart

Follow the root [README](../README.md) from an extracted `evrptw-db/` directory, with `../review-core/` next to it. Editable installation binds only this extracted source directory. The offline `inspect`, `verify` and `solve` operations described here need no original research checkout, private PYTHONPATH, account, API key, GPU or Gurobi. Online generation requires the AFDC API key described in the README.

Inputs are a frozen manifest, parent matrices plus per-view terminal indices, and an explicit route list. `inspect` reports scientific fields. `verify` performs independent production replay and writes JSON; success is exit code 0 and `VERIFIED`. An invalid route exits 2, has `verified_feasible: false`, and retains diagnostics with null cost. Invalid input or missing files raises an error; there is no random data/model fallback.

The first route's expected cost is **443.09390458194605 USD**, distance **194.13879445940256 km**, and vehicle count **1**. The historical record also contains a different archived cost based on shortest distance; `verify` explicitly reports the current objective and does not overwrite that record.

`solve --seconds 10` includes adaptation, constructor/initialization and ALNS search in its algorithm budget. Loading and final independent replay are outside that timer. The output also reports an enclosing measured wall time. Wall-clock cancellation and cleanup can slightly exceed the requested budget; an absent measurement is not filled with the budget. The demonstrated solution cost was USD 432.2225831307662, but exact search outcomes are not a success criterion.

Generation uses a new output directory: existing generated families are never overwritten. See [GENERATION](GENERATION.md) for one/two-worker comparison, expected new IDs and the separate `train` fixture. All paths accept spaces. The code does not upload logs or contact online experiment trackers. Installation and explicit full-source acquisition are separate from offline review commands.
