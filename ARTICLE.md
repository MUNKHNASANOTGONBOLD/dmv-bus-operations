# From Live Bus GPS to Operational Intelligence: Building a DMV Metrobus Analytics Pipeline

*An applied data engineering and business analytics case study | Munkhnasan Otgonbold | October 2026*

## The business question

Transit operations teams need to distinguish a genuine service issue from a gap in their monitoring data. A route may appear unusually delayed because of schedule adherence, sampling frequency, stale location reports, or incomplete API coverage. The first challenge is therefore to build a traceable observation pipeline before making operational claims.

I built a Python–SQLite–SQL workflow that captures WMATA Metrobus positions, records every polling outcome, and converts repeated GPS snapshots into route-hour summaries suitable for exploratory dashboards. The system covers the broader Washington metropolitan transit network, including DC, Maryland and Virginia; it is not a DC-only geographic extract.

## 1. The data source and architecture

The collector requests WMATA's bus-position endpoint using an API subscription key supplied through an environment variable. It writes a `polls` table (fetch timestamp, HTTP status, success/error and record count) and a `positions` table (route, vehicle, trip, coordinates, source time and reported deviation). Failed polls are retained rather than silently dropped. Raw source JSON is retained locally for auditing, but raw databases are excluded from the public repository.

The analysis layer uses a SQLite window function to keep the latest record for each route–vehicle–trip–local-hour combination. This is important: simply counting every API response would multiply the same vehicle across repeated polls and bias route comparisons. SQL produces route-hour indicators, and a Python export script writes CSV files for Tableau.

## 2. What the collection actually captured

From **October 9, 2026 at 22:08 UTC through October 10 at 22:49 UTC**, the supplied pipeline-health export recorded **2,902 polls**, including **2,901 successes** and **one HTTP 401 error**. Successful polls returned **1,143,917 position observations**. Those are observations, not distinct buses.

The exported analytical table contains **2,256 route-hour records across 126 routes** and **20,261 deduplicated vehicle/trip/hour samples**. These counts establish that the collection and transformation pipeline operated over a substantial snapshot dataset. They do not establish long-term reliability, passenger waiting time, or route-level causation.

## 3. Operational indicators

The SQL output provides (a) the number of deduplicated vehicle/trip/hour samples, (b) the number with valid reported deviation, (c) average API-reported deviation in minutes, and (d) the percentage exceeding a **project-defined five-minute threshold**. These are exploratory indicators only. They must not be presented as WMATA's official on-time performance or as passenger-weighted delay.

A companion pipeline-health dataset supports an essential dashboard check: when data is missing because of an authentication or network error, a chart should flag a collection failure instead of suggesting that service disappeared.

## 4. How I would use the dashboard

An operations analyst can filter the aggregate data by route and hour, inspect observation coverage, and identify unusual reported-deviation patterns worth investigating. A route-hour heatmap, ranked investigation table, and polling-health trend are natural outputs. The underlying source includes coordinates, but the public aggregate does not; a geospatial route map requires a separately validated and appropriately sampled GPS export.

The dashboard's role is to **prioritize investigation**, not assert that a given corridor is a proven bottleneck.

## 5. Data quality and limitations

- **Short window:** About 24.7 hours of collection cannot support weekday/weekend or seasonal generalizations.
- **Repeated polling:** Raw observation counts are not unique vehicle counts; the SQL deduplication reduces repeated weighting within each vehicle/trip/hour.
- **Metric semantics:** WMATA's `Deviation` field and local timestamps require source-level validation, including daylight-saving interpretation and freshness rules.
- **Regional coverage:** Route aggregates include the regional WMATA system, not a verified District-only spatial subset.
- **No passenger outcomes:** The feed does not directly measure riders' actual wait time, boarding demand, or intervention savings.
- **No historical backfill:** A live API poll does not retroactively provide a year of GPS traces.

## 6. Next analytical improvements

The next iteration should add continuous monitored collection, source freshness tests, verified route and stop geometry, headway comparisons against published schedules, and date-compatible ridership data. Those additions would support stronger service-reliability and bottleneck analysis.

## Technical stack

**Python 3.11+**, standard-library HTTP/JSON, **SQLite**, **SQL window functions**, CSV exports and **Tableau-ready** datasets. Synthetic unit tests verify ingestion and repeated-poll deduplication.

## Takeaway

The central achievement is a reproducible pipeline that turns live transit API snapshots into auditable route-hour operational indicators. It makes data coverage visible, separates exploratory indicators from official performance metrics, and creates a foundation for more defensible transit operations analysis.

**Source:** [WMATA Developer Portal](https://developer.wmata.com/) · [WMATA Open Data Hub](https://www.wmata.com/about/open-data-hub.html)