# Component licenses and source attribution

The root [license notice](../LICENSE) applies **CC BY-NC 4.0** to project-original code and documentation, and to the authors' applicable rights in supplied project-trained model weights and evaluation records. The complete legal text is in [CC_BY_NC_4_0.txt](../licenses/CC_BY_NC_4_0.txt). Third-party components and applicable source/derivative database rights remain subject to the separate terms below. A ZIP file is a delivery container, not a single new license for every component inside it. This change does not revoke licenses already granted for earlier lawfully obtained versions.

Licenses are assigned by component, not by taking a single license
"intersection". A license for original software cannot replace source-data or
third-party software terms. ODbL distinguishes independent databases in a
collection from a derivative database; its share-alike grant cannot simply be
replaced by an additional noncommercial restriction. The classification of the
combined road and delivery materials depends on their actual provenance and
transformations, not just whether they share a ZIP file. See
[ODbL sections 2.3, 4.4 and 4.5](https://opendatacommons.org/licenses/odbl/1-0/).

## Software

| Component | Source and preserved terms |
| --- | --- |
| AM-EVRPTW upstream attention code | [Wouter Kool's attention-learn-to-route](https://github.com/wouterkool/attention-learn-to-route), MIT; original copyright/license retained in the vendored tree and `licenses/attention-learn-to-route.MIT.txt` |
| RRNCO-EVRPTW upstream network code | [AI4CO real-routing-nco](https://github.com/ai4co/real-routing-nco), MIT; original copyright/license retained in the vendored tree and `licenses/real-routing-nco.MIT.txt` |
| TERRAN upstream code | [NanpengYu/TERRAN](https://github.com/NanpengYu/TERRAN), Apache-2.0; pinned source and local modifications are recorded in `EVRPTW_Benchmark/Reinforcement_Learning/TERRAN/third_party/terran/UPSTREAM.md`, with its original LICENSE alongside it |
| Project-original generator, task, verifier, wrappers, local implementations, scripts, and documentation | CC BY-NC 4.0, Copyright (c) 2026 Anonymous EVRP-TW-D/B Authors; scope in root LICENSE and full legal text in licenses/CC_BY_NC_4_0.txt; no upstream endorsement is claimed |
| Gurobi | Optional external proprietary dependency; obtain an appropriate [Gurobi license](https://www.gurobi.com/solutions/licensing/). No license key or commercial solver distribution is included |

An algorithm citation and source-code license are different things. EVRPTW-RL and DRL-TS are disclosed as paper-guided local implementations; ALNS and VNS/TS likewise use local implementations based on their cited methods. The project does not claim those methods' authors released or endorsed these adaptations. See [BASELINES.md](BASELINES.md) for actual implementation provenance and restrictions. Installed Python dependencies retain their own licenses and are not relicensed here.

## Project-trained model weights

To the extent they hold applicable rights, the Anonymous EVRP-TW-D/B Authors
license their project-trained inference tensors and project-original model
metadata supplied in `review-checkpoints/` under **Creative Commons
Attribution-NonCommercial 4.0 International (CC BY-NC 4.0)**. The complete,
unmodified license is in
[PROJECT_WEIGHTS_CC_BY_NC_4_0.txt](../licenses/PROJECT_WEIGHTS_CC_BY_NC_4_0.txt),
retrieved from the [official legal code](https://creativecommons.org/licenses/by-nc/4.0/legalcode.txt).
The license permits noncommercial reuse, adaptation, and sharing subject to
attribution and its other conditions. Retain the designation
"Anonymous EVRP-TW-D/B Authors", this license notice, and the model's artifact
identifier; indicate any changes.

This is an explicit license choice for the authors' rights in these artifacts,
not an assertion that a training dataset's license automatically determines a
model's license. It does not grant third-party data rights, replace upstream
software licenses, or license provider trademarks. A license also does not
establish which evaluation table an artifact reproduces: checkpoint provenance
and evaluation configuration remain part of its model documentation. The
distributed checkpoints contain inference tensors and metadata, not optimizer
states or bundled training databases.

## Evaluation records

To the extent they hold applicable rights, the Anonymous EVRP-TW-D/B Authors
license their original contributions to supplied route sets, metrics, and run
metadata under CC BY-NC 4.0. Retain the author designation, artifact identifiers,
license link and modification notices. Embedded source content and applicable
database rights retain their upstream terms; this grant does not relicense
instance inputs. Historical replay fixtures remain distinct from current-policy
evaluation outputs, as described in their accompanying records.

## Data components

| Source | Included or used component | Terms and limits |
| --- | --- | --- |
| OpenStreetMap contributors | Road graph, directed topology, access/depot data and derived road matrices | [Open Database License 1.0](https://opendatacommons.org/licenses/odbl/1-0/). Retain attribution to OpenStreetMap contributors and applicable database share-alike obligations. [Provider copyright page](https://www.openstreetmap.org/copyright) |
| Microsoft | Building-derived customer geometry | Microsoft publishes US Building Footprints under ODbL. The original footprint geometry is processed into customer candidates and access points. [Official data repository](https://github.com/microsoft/USBuildingFootprints) |
| USACE National Structure Inventory | Public structure attributes used in customer construction | The source adapter uses fields in the public NSI 2026 Base schema, including `resunits`, `ftprntsqft`, and `bldheight`, which are explicitly public in the [2026 technical documentation](https://www.hec.usace.army.mil/confluence/nsi/technicalreferences/2026/technical-documentation). No restricted-field or Data Use Agreement entitlement is claimed. Retain USACE attribution and the distinction between modeled attributes and verified building-level observations; this does not relicense NSI data under the project license or CC0. |
| U.S. Census Bureau | City boundaries and block-group identifiers/splits in the full pipeline | Census federal materials are reproducible with source citation; TIGER/Line boundaries are for statistical purposes and are not legal land descriptions. TIGER/Line is a registered Census trademark. [Official technical documentation, sections 1.5–1.6](https://www2.census.gov/geo/pdfs/maps-data/data/tiger/tgrshp2018/TGRSHP2018_TechDoc.pdf) |
| U.S. DOE / AFDC | Public charging-station locations and technical attributes | The [AFDC download terms](https://afdc.energy.gov/data_download) permit use for any purpose while retaining no-endorsement, no-support, indemnity and warranty/liability conditions. The [AFDC disclaimer](https://afdc.energy.gov/disclaimer) notes limitations of accuracy and fitness. Do not relabel these terms as the code license. |
| U.S. EPA MOVES5 | Derived weekday/weekend road speed profiles | Cite [USEPA (2024), MOVES5](https://www.epa.gov/moves/latest-version-motor-vehicle-emission-simulator-moves). The full MOVES software is not vendored. Its [source license notice](https://github.com/USEPA/EPA_MOVES_Model/blob/master/License.txt) names the GPL; this is not evidence that every derived statistic has the same license or that the project may replace its terms. |
| Amazon.com, Inc. or affiliates | Derived package volumes, counts, service times, windows and template IDs | [2021 Amazon Last Mile Routing Research Challenge Dataset](https://registry.opendata.aws/amazon-last-mile-challenges/), [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/). Retain attribution, license link and modification notices; the noncommercial condition applies to the licensed material. |

The generation fixture has separate road/speed, terminal and order-template files. Its new materialized views combine these sources, while the original review views are frozen semi-synthetic artifacts. Geographic features were cropped, mapped to directed access edges and used to compute matrices; Amazon records were transformed into operational templates and assigned to different geographic candidates. These transformations are modifications, not newly collected real delivery records.

There is no blanket CC BY-NC 4.0 grant over all review data or third-party components. The local artifact inventory identifies source components and preserves their notices. This document does not certify that a single combined-dataset license settles all ODbL database rights, Amazon content rights, NSI snapshot rights or model-weight redistribution rights. The unresolved combined-material grant and any additional source permission must be settled before a broad public redistribution; the material is presently delivered locally for review preparation.

## Source quality is separate from rights

The cached Fort Worth CLE retains six manual-review blockers: `microsoft_nsi_geometry`, `customer_road_access_review`, `depot_release`, `charging_coordinate_validation`, `charging_release`, and `delivery_communities`. These are source-quality status labels, not licenses. The supplied numerical checks neither clear those labels nor certify real-world access, depot legitimacy or charging availability.

Normal third-party names, upstream repository URLs, citations and legally required copyright notices are intentionally retained for attribution. They must not be removed as part of author anonymization. [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md) provides the accompanying attribution record.
