# Extending the workbench

`researchgee/catalog.py` defines datasets and scientific metadata. `config.py` owns input validation and manifests. `engine.py` builds EE graphs; `app.py` renders the local interface. Authentication is explicit, never an import side effect.

To add a dataset:
1. Verify its official catalog entry, band names, units, QA semantics, scale/offset, dates and license/citation.
2. Add a Dataset entry and preprocessing in `prepare` if necessary. Keep science bands, timestamps and scene IDs.
3. Declare whether it is static and which temporal reducers are scientifically meaningful. Do not add indices for incompatible bands.
4. Add offline graph/validation tests, then verify a small AOI against the official Code Editor example with an authenticated project.
5. Update README/methods, and capture actual output with its manifest before claiming live support.

## Future research workflows (not implemented)

| Priority | Capability | Required research safeguards |
|---|---|---|
| 1 | Multi-polygon zonal tables, monthly/seasonal series | Stable zone IDs, coverage fractions, explicit temporal weights |
| 1 | Custom assets and dataset search | Schema discovery, scale/QA metadata and access checks |
| 2 | Supervised land-cover classification | Spatial train/test splits, independent validation, confusion matrix |
| 2 | Flood and drought screening | Baseline design, terrain/permanent-water masks, reference validation |
| 2 | Trend and anomaly tools | Seasonality, autocorrelation, multiple-testing controls |
| 3 | Batch scheduling and Cloud Storage/Asset exports | Quotas, resumability, bounded task queues, cost controls |
| 3 | Multi-user hosting | Per-user OAuth, credential isolation, task ownership and authorization |

All Earth Engine algorithms cannot be safely exposed as interchangeable buttons. Add workflows around testable research questions and verified data semantics.
