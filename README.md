# DMV Metrobus Operations Analytics

**Python · WMATA API · SQLite · SQL · Tableau-ready CSV**

An observational data pipeline for exploring route-hour variation in WMATA Metrobus operations across the Washington, DC metropolitan region. The project collects live vehicle-position snapshots, retains ingestion health, deduplicates repeated observations for route-hour indicators, and exports Tableau-ready datasets.

> **Scope:** WMATA's regional network, not exclusively the District of Columbia. Reported schedule deviation is an exploratory API-based measure—not official on-time performance, verified passenger delay, or proof of a causal bottleneck.

## Evidence from the supplied collection

| Measure | Value |
|---|---:|
| Collection window (UTC) | Oct 9, 2026 22:08 – Oct 10, 2026 22:49 |
| API polling attempts | 2,902 |
| Successful polls | 2,901 |
| Failed polls | 1 (HTTP 401) |
| Position observations returned | 1,143,917 |
| Routes in exported aggregates | 126 |
| Route-hour aggregate rows | 2,256 |
| Deduplicated vehicle/trip/hour samples in aggregates | 20,261 |

The position-observation count includes repeated snapshots of vehicles; it is **not** a unique-vehicle count. Coverage is approximately 24.7 hours, so patterns should not be generalized to other weeks or seasons.

## Pipeline

```text
WMATA Bus Positions API
        | (API key in request header only)
        v
Python collector.py -> SQLite polls + positions
        |
        v
SQL route-hour deduplication / aggregation
        |
        v
Python export.py -> route_hour.csv + pipeline_health.csv
        |
        v
Tableau / exploratory operational dashboard
```

## Original SQLite databases and sample preview

The source archive contained `wmata.sqlite` and `wmata_review.sqlite`, each 978,620,416 bytes. Both passed SQLite integrity checks. The **logical contents** of both `polls` and `positions` tables match exactly when streamed in primary-key order; their binary file hashes differ because of database-file layout. Only one full copy is needed.

GitHub blocks normal Git pushes of files above 100 MB, so the full ~979 MB database is **not in this repository**. The original archive remains with the project owner. Use `make_sample_db.py` locally to produce a sanitized SQLite preview (default: 8 polls, up to 800 positions). The preview strips raw JSON payloads; it is for schema and query exploration, not statistically representative analysis.

```bash
python make_sample_db.py --source data/wmata.sqlite --out wmata-sample.sqlite
```

**Security:** The original SQLite payloads were inspected for API-key field names in `polls.raw_json`; none were found. Raw GPS JSON and complete databases remain excluded from GitHub. Do not publish full data without verifying WMATA redistribution terms and data privacy requirements.

## Repository contents

- `collector.py`: requests live bus positions and records both successful and failed polls.
- `export.py`: runs SQL and exports CSV datasets.
- `sql/route_hour.sql`: selects the latest observation per route/vehicle/trip/local hour before aggregating.
- `tests/test_pipeline.py`: synthetic tests for ingestion and deduplication.
- `sample_exports/`: supplied collection's aggregated CSVs (no raw GPS payloads or credentials).
- `make_sample_db.py`: builds a small sanitized SQLite preview from the full local database.
- `ARTICLE.md`: project write-up, methods, findings, limitations and next steps.

## Run locally

Requires Python 3.11+; standard library only. Obtain your own subscription key at https://developer.wmata.com/. **Never commit an API key.**

PowerShell:
```powershell
$env:WMATA_API_KEY = 'YOUR_KEY'
python collector.py --polls 1
python export.py
python -m unittest discover -s tests -v
```

Bash:
```bash
export WMATA_API_KEY='YOUR_KEY'
python3 collector.py --polls 1
python3 export.py
python3 -m unittest discover -s tests -v
```

A longer local collection can use `python collector.py --polls 60 --interval 60` if permitted by your API subscription. No hosted always-on service is claimed.

## Data definitions

- `pipeline_health.csv`: API poll time, status, HTTP code and number of returned position records. A failed poll is **not** interpreted as zero buses.
- `route_hour.csv`: route and source-local-hour aggregate of one latest record per vehicle/trip/hour, with mean API-reported deviation and share of valid deviation samples above a **project-defined** five-minute threshold.
- API timestamps and `Deviation` semantics require validation against current WMATA documentation before formal service-performance claims.
- The supplied export has regional scope. Do not describe it as a DC-only analysis without a verified geographic filter.

## Dashboard and interpretation

The route-hour dataset supports route comparisons, time-of-day patterns and data-quality reporting. GPS location maps require separate appropriately sampled position data; the published aggregate CSV **does not contain latitude/longitude**. An existing Tableau workbook is not included in this repository package.

## Security and data hygiene

`WMATA_API_KEY` is read from the environment. Raw `.sqlite` databases, local `.env` files, and cache files are ignored. The two original ~979 MB databases are deliberately **not** published. Rotate any key that has previously been publicly exposed.

## References

- [WMATA developer portal](https://developer.wmata.com/)
- [WMATA developer resources](https://www.wmata.com/about/developers.html)
- [WMATA Open Data Hub](https://www.wmata.com/about/open-data-hub.html)

## Author

Munkhnasan Otgonbold — Data Analytics / Business Analytics portfolio project.