# Optional canonical-format evaluation export

The main [evaluation example](../../README.md) reads the original family/view data directly from `review-core/`. This JSON is retained as a canonical-format loading example.

[road_100.json](road_100.json) is a canonical JSON export of the first frozen real review view, `iv_4073f1928fa0c95f3de64257`: Chicago, T1, 100 customers, 20 charging stations and one depot. Its source evaluation split, track, instance/family IDs, resource values and directed road-network matrix values are preserved. It is separate from both packaged training views and their families. The complete 22-view review sample remains in `review-core/`.

After installing the source package, this input can be loaded directly with `EVRPTWInstance.from_dict(json.loads(path.read_text()))` or passed as the explicit instance file to checkpoint evaluation. It needs no private data path or external parent matrix directory. The source's absolute family path was removed; `usage: review_evaluation_demo` and canonical JSON storage metadata were added.

[verification.json](verification.json) records the input checksum, 31 exact array-value restoration checks, view-specific feasibility certificate recomputation and independent singleton-route verification. No training-instance or training-family overlap was found. The T1 protocol can share geographic pools with training; this single-view demonstration is not a geographic holdout or a full benchmark.

Shortest-distance and fastest-time-path quantities remain separate. Use the specified checkpoint's objective contract and independently verify its exported routes. The accompanying route figure, if requested, is a terminal schematic rather than actual road-path geometry. Source attribution and data-use boundaries are described in [LICENSING.md](../../docs/LICENSING.md).
