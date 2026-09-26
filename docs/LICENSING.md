# Licensing and source attribution

The root [LICENSE](../LICENSE) governs only the scope stated there. It does not replace upstream software licenses, grant rights over provider data, or automatically license trained weights and derived datasets. Private version-control storage does not establish permission for public redistribution. Public provider pages were checked on 2026-09-25; their current wording does not establish the acquisition terms of every historical snapshot.

## Software

| Component | Source and preserved terms |
| --- | --- |
| AM-EVRPTW upstream attention code | [Wouter Kool's attention-learn-to-route](https://github.com/wouterkool/attention-learn-to-route), MIT; original copyright/license retained in the vendored tree and `licenses/attention-learn-to-route.MIT.txt` |
| RRNCO-EVRPTW upstream network code | [AI4CO real-routing-nco](https://github.com/ai4co/real-routing-nco), MIT; original copyright/license retained in the vendored tree and `licenses/real-routing-nco.MIT.txt` |
| TERRAN upstream code | [NanpengYu/TERRAN](https://github.com/NanpengYu/TERRAN), Apache-2.0; pinned source and local modifications are recorded in `EVRPTW_Benchmark/Reinforcement_Learning/TERRAN/third_party/terran/UPSTREAM.md`, with its original LICENSE alongside it |
| Project task/verifier/wrappers and local implementations | Scope and grant are as stated in root LICENSE; no upstream endorsement is claimed |
| Gurobi | Optional external proprietary dependency; obtain an appropriate [Gurobi license](https://www.gurobi.com/solutions/licensing/). No license key or commercial solver distribution is included |

An algorithm citation and source-code license are different things. EVRPTW-RL and DRL-TS are disclosed as paper-guided local implementations; ALNS and VNS/TS likewise use local implementations based on their cited methods. The project does not claim those methods' authors released or endorsed these adaptations. See [BASELINES.md](BASELINES.md) for actual implementation provenance and restrictions. Installed Python dependencies retain their own licenses and are not relicensed here.

## Data components

| Source | Included or used component | Terms and limits |
| --- | --- | --- |
| OpenStreetMap contributors | Road graph, directed topology, access/depot data and derived road matrices | [Open Database License 1.0](https://opendatacommons.org/licenses/odbl/1-0/). Retain attribution to OpenStreetMap contributors and applicable database share-alike obligations. [Provider copyright page](https://www.openstreetmap.org/copyright) |
| Microsoft | Building-derived customer geometry | Microsoft publishes US Building Footprints under ODbL. The original footprint geometry is processed into customer candidates and access points. [Official data repository](https://github.com/microsoft/USBuildingFootprints) |
| USACE National Structure Inventory | Public structure attributes used in customer construction | The [NSI 2022 FAQ](https://www.hec.usace.army.mil/confluence/nsi/technicalreferences/2022/frequently-asked-questions) distinguishes publicly accessible primary fields from additional restricted fields. No restricted NSI data-use-agreement rights are claimed. A snapshot-specific standalone redistribution license was not located in the inspected material; public API access alone is not a new project license. |
| U.S. Census Bureau | City boundaries and block-group identifiers/splits in the full pipeline | Census federal materials are reproducible with source citation; TIGER/Line boundaries are for statistical purposes and are not legal land descriptions. TIGER/Line is a registered Census trademark. [Official technical documentation, sections 1.5–1.6](https://www2.census.gov/geo/pdfs/maps-data/data/tiger/tgrshp2018/TGRSHP2018_TechDoc.pdf) |
| U.S. DOE / AFDC | Public charging-station locations and technical attributes | The [AFDC download terms](https://afdc.energy.gov/data_download) permit use for any purpose while retaining no-endorsement, no-support, indemnity and warranty/liability conditions. The [AFDC disclaimer](https://afdc.energy.gov/disclaimer) notes limitations of accuracy and fitness. Do not relabel these terms as the code license. |
| U.S. EPA MOVES5 | Derived weekday/weekend road speed profiles | Cite [USEPA (2024), MOVES5](https://www.epa.gov/moves/latest-version-motor-vehicle-emission-simulator-moves). The full MOVES software is not vendored. Its [source license notice](https://github.com/USEPA/EPA_MOVES_Model/blob/master/License.txt) names the GPL; this is not evidence that every derived statistic has the same license or that the project may replace its terms. |
| Amazon.com, Inc. or affiliates | Derived package volumes, counts, service times, windows and template IDs | [2021 Amazon Last Mile Routing Research Challenge Dataset](https://registry.opendata.aws/amazon-last-mile-challenges/), [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/). Retain attribution, license link and modification notices; the noncommercial condition applies to the licensed material. |

The generation fixture has separate road/speed, terminal and order-template files. Its new materialized views combine these sources, while the original review views are frozen semi-synthetic artifacts. Geographic features were cropped, mapped to directed access edges and used to compute matrices; Amazon records were transformed into operational templates and assigned to different geographic candidates. These transformations are modifications, not newly collected real delivery records.

There is no blanket MIT grant over review data or checkpoints. The local artifact inventory identifies source components and preserves their notices. This document does not certify that a single combined-dataset license settles all ODbL database rights, Amazon content rights, NSI snapshot rights or model-weight redistribution rights. The unresolved combined-material grant and any additional source permission must be settled before a broad public redistribution; the material is presently delivered locally for review preparation.

## Source quality is separate from rights

The cached Fort Worth CLE retains six manual-review blockers: `microsoft_nsi_geometry`, `customer_road_access_review`, `depot_release`, `charging_coordinate_validation`, `charging_release`, and `delivery_communities`. These are source-quality status labels, not licenses. The supplied numerical checks neither clear those labels nor certify real-world access, depot legitimacy or charging availability.

Normal third-party names, upstream repository URLs, citations and legally required copyright notices are intentionally retained for attribution. They must not be removed as part of author anonymization. [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md) provides the accompanying attribution record.
