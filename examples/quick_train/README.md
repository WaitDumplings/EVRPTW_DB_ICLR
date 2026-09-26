# Embedded quick-training fixture

`families/demo_family_train_000/` is a byte-identical copy of the separately generated `demo/train` engineering family used by the offline generation demonstration. It contains an 8-customer/2-station view and its nested 4-customer/1-station view, with all four directed matrices, attributes and certificates. The source-code bundle includes these 44,387 bytes so quick training needs no external review-core bundle after installing dependencies.

This is a new engineering instance produced from the cropped Fort Worth road/CLE fixture and derived Amazon order templates. It is not one of the 22 real evaluation views and is not a paper cohort. Evaluating the demo-trained weights on it only checks the end-to-end interface, not held-out quality. The original data bytes are preserved and covered by the root FILE_MANIFEST.json.

The fixture is source-derived data with component-specific terms; the project-original code license does not replace those terms. See [data terms](../../docs/LICENSING.md) and [source attribution](../../THIRD_PARTY_NOTICES.md), including OpenStreetMap/Microsoft ODbL and Amazon CC BY-NC 4.0, plus the recorded source-specific boundaries. Geographic and order-template transformations remain described in [generation](../../docs/GENERATION.md). No raw-data download or map service is used by the training demo.
