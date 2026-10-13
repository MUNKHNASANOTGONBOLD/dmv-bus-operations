# From Live Bus GPS to Operational Intelligence
## Building an Auditable WMATA Metrobus Analytics Pipeline

**Munkhnasan Otgonbold | Data Engineering • SQL • Transit Operations Analytics | October 2026**

> **Project in one sentence:** I built a Python–SQLite pipeline that repeatedly captures WMATA bus positions, records ingestion failures, reduces repeated GPS observations to route-hour samples, and exports auditable operational indicators for Tableau.

**Technology:** Python 3.11+, WMATA Bus Positions API, SQLite, SQL window functions, CSV, Tableau-ready datasets.  
**Coverage:** WMATA's regional Metrobus system across Washington, DC, Maryland, and Virginia.  
**Observation period:** October 9, 2026, 22:08 UTC to October 10, 2026, 22:49 UTC (~24.7 hours).  
**Repository:** https://github.com/MUNKHNASANOTGONBOLD/dmv-bus-operations

---

## Executive summary

Transit managers need to understand where bus operations appear irregular—but real-time GPS feeds can create misleading dashboards if observations are counted as distinct vehicles or if failed API requests are interpreted as service interruptions. I designed an ingestion and analytical workflow to separate *what the feed observed* from *what the operation actually did*.

Across the observed window, the collector attempted **2,902 API polls**, of which **2,901 succeeded** and **one returned HTTP 401**. Successful polls produced **1,143,917 position observations**. After aggregation, the analytical export contained **2,256 route-hour rows** across **126 routes**, representing **20,261 deduplicated vehicle/trip/hour samples**. These numbers describe observations and analytical units—not 1.14 million individual buses.

Among **20,251 samples with a valid API-reported deviation**, **4,771 (23.6%)** exceeded the project's exploratory **five-minute positive-deviation threshold**. This is *not* WMATA's official late-arrival rate or passenger-weighted delay. The project is a foundation for identifying candidates for further investigation, not proof of specific operational bottlenecks.

## 1. The business problem

A fleet-monitoring dashboard can answer superficially simple questions: Which routes look irregular? At what hours? Is the incoming data reliable? But a live API produces repeated snapshots of the same buses, potentially hundreds of times. A naive `COUNT(*)` exaggerates activity, while a blank chart during an API outage can be mistaken for a route with no service.

I framed the project around three analytical questions:

1. **Observability:** Can we tell whether the collection process was operating normally?
2. **Comparability:** Can repeated snapshots be transformed into more comparable route-hour observations?
3. **Triage:** Which route-hour combinations merit deeper investigation using schedules, headways, and verified location data?

## 2. Architecture and data flow

```text
WMATA Bus Positions API
       |
       | HTTP request; subscription key read from environment
       v
Python collector.py
       |-- polls: request timestamp, success/error, HTTP code, row count
       |-- positions: route, vehicle, trip, timestamp, coordinates, deviation
       v
Local SQLite database
       |
       | SQL ROW_NUMBER() deduplication + GROUP BY
       v
route_hour.csv                  pipeline_health.csv
       |                                  |
       +---------------+------------------+
                       v
             Tableau / operational review
```

**Why SQLite?** It provided a simple, inspectable local persistence layer with relational queries and window functions, without introducing a cloud service before the data model was validated. **Why separate health from operations?** It makes ingestion failure visible instead of silently treating missing data as zero activity.

### Collector design

The collector retrieves the bus-position feed, validates the expected JSON structure, records each polling attempt, and writes position rows linked to a poll ID. The API key is supplied through the `WMATA_API_KEY` environment variable; it is not hard-coded or published. The raw local database is excluded from GitHub. A small sanitized sample can be generated separately.

The `polls` table is as important as `positions`: a successful response with no observations and a failed request are analytically different events.

## 3. Data model and transformations

**Poll-level grain:** one row per API request. Fields include poll ID, fetch time in UTC, status, HTTP status, returned row count, and error classification.

**Position-level grain:** one bus-position observation returned in a particular poll. Fields include poll ID, vehicle ID, route ID, trip ID, source-local time, coordinates, and API-reported deviation.

**Analytical grain:** one latest available record per `route_id × vehicle_id × trip_id × source-local hour`, then summarized to `route_id × hour`. This is an intentional modeling choice: it reduces repeated polling weight, but it is not a count of distinct vehicles over a day. The same vehicle can appear in different trips and hours.

### SQL logic

The core transformation uses a window function:

```sql
ROW_NUMBER() OVER (
  PARTITION BY route_id, vehicle_id, trip_id,
               SUBSTR(source_time_local, 1, 13)
  ORDER BY source_time_local DESC, poll_id DESC, row_number DESC
) AS sample_rank
```

Keeping `sample_rank = 1` avoids weighting a repeatedly observed bus dozens of times within the same route/trip/hour group. The downstream aggregation computes the number of retained samples, the number with valid deviation, mean reported deviation, and the proportion above the exploratory five-minute threshold. The complete SQL is in [`sql/route_hour.sql`](https://github.com/MUNKHNASANOTGONBOLD/dmv-bus-operations/blob/main/sql/route_hour.sql).

**Important caveat:** The source-local hour is currently extracted as a string. Future iterations should normalize timestamps with explicit timezone/DST rules and evaluate whether the *latest* sample is representative of an entire hour.

## 4. What the dataset actually shows

| Metric | Observed value | Interpretation |
|---|---:|---|
| Poll attempts | 2,902 | Recorded HTTP attempts |
| Successful polls | 2,901 | Feed responses ingested successfully |
| Failed polls | 1 | HTTP 401; not zero bus activity |
| Position observations | 1,143,917 | Repeated snapshots, not unique buses |
| Routes represented | 126 | Regional WMATA feed |
| Route-hour aggregate rows | 2,256 | Exported analytical groups |
| Vehicle/trip/hour samples | 20,261 | After analytical deduplication |
| Samples with valid deviation | 20,251 | Denominator for threshold analysis |
| Samples above +5 minutes | 4,771 | 23.6% of valid samples |

### A route-level investigation shortlist—not a ranking of actual service quality

As a descriptive check, I aggregated the exported route-hour samples by route and restricted the comparison to routes with **at least 100 valid deviation samples**. The highest proportions above the project's +5-minute threshold included:

| Route | Deduplicated samples | Share above +5 min |
|---|---:|---:|
| D36 | 199 | 53.3% |
| D1X | 172 | 48.3% |
| A11 | 143 | 43.4% |
| D32 | 184 | 42.4% |
| C55 | 130 | 41.5% |

These figures are **exploratory indicators**, not official on-time-performance scores. They are sensitive to the one-day sample window, source deviation semantics, route composition, time-of-day coverage, and the latest-record deduplication rule. They should guide where to inspect schedule adherence and headways next, not be used to label routes as definitively poor performers.

## 5. Dashboard design: from metrics to decisions

I would organize the Tableau experience into three views:

**A. Operations overview.** KPI tiles for observed routes, route-hour samples, share above the project threshold, and collection success rate. The date window and the distinction between GPS observations and unique buses must remain visible.

**B. Route-hour investigation.** A heatmap with route on rows and source-local hour on columns, colored by the share of valid samples above the threshold. Add a minimum-sample filter so small denominators do not dominate attention. A linked table should show sample counts and average reported deviation.

**C. Data pipeline health.** Polling success/failure over time, HTTP codes, and records returned per successful poll. A 401 should be highlighted as an authentication/collection issue rather than a transit disruption.

A true GPS route map is a separate step. The public aggregate CSV does **not** contain latitude/longitude, so it cannot by itself support a geospatial route map. A validated sampled position export, spatial boundaries, and freshness checks are needed.

## 6. Data quality, engineering trade-offs, and limits

**Repeated observations:** Over one million source observations are not independent. The window-function approach reduces overcounting, but does not eliminate sampling bias.

**Time coverage:** Approximately 24.7 hours is too short to infer a typical weekday, weekend, seasonal trend, or durable route bottleneck.

**Source semantics:** API `Deviation` needs verification against current WMATA documentation. A positive value above five minutes is a *project-defined analytical threshold*, not an agency service-standard classification.

**Spatial scope:** The API captures a regional network. The project is not a validated District-only spatial analysis.

**Passenger outcomes:** There are no observed boarding counts, rider wait times, crowding measures, or intervention savings in this dataset.

**Authentication failure:** The single HTTP 401 demonstrates why polling status belongs in the analytical model. It should not be hidden or treated as zero vehicles.

**Reproducibility and security:** Code and SQL are published, while API credentials and the two approximately 979 MB local SQLite files are excluded. The repository includes a script for creating a small sanitized SQLite preview. Full data redistribution should be assessed against applicable source terms before publication.

## 7. What I would build next

1. **Longer observation window:** continuously collect across multiple weeks and monitor gaps, duplicate rates, and stale source timestamps.
2. **Schedule and headway validation:** join compatible scheduled stop times and investigate observed versus expected headways, not only source deviation.
3. **Geospatial validation:** sample coordinates, verify route geometry, and distinguish regional from DC-specific coverage.
4. **Operational drill-down:** compare recurring route-hour patterns with confidence/coverage thresholds, and prioritize analyst review.
5. **Production readiness:** add automated checks, structured logging, scheduled deployment, alerting, and reproducible data snapshots.

## 8. What this project demonstrates

This project shows that I can translate a business question into an auditable pipeline: ingest a live external API, design relational tables, validate polling health, write SQL window functions, define defensible metrics, and prepare data for decision-oriented visualization. The key lesson is that *trustworthy operational intelligence begins with observation quality and clear metric definitions*.

---

### Repository and sources

- [GitHub repository and source code](https://github.com/MUNKHNASANOTGONBOLD/dmv-bus-operations)
- [WMATA Developer Portal](https://developer.wmata.com/)
- [WMATA Open Data Hub](https://www.wmata.com/about/open-data-hub.html)

*All numeric findings above were calculated from the supplied `route_hour.csv` and `pipeline_health.csv` exports. They describe the specified collection window and should not be generalized beyond it.*