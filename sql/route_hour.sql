-- SQLite: one latest source update per vehicle/trip/local hour.
-- This is an observation-based delay indicator, NOT official on-time performance.
-- Agency-wide WMATA coverage. Add a verified DC boundary before making DC-only claims.
WITH ranked AS (
 SELECT *, substr(source_time_local,1,13) AS local_hour,
 row_number() OVER (
  PARTITION BY route_id,vehicle_id,trip_id,substr(source_time_local,1,13)
  ORDER BY source_time_local DESC,poll_id DESC,row_number DESC
 ) AS sample_rank
 FROM positions
 WHERE route_id IS NOT NULL AND vehicle_id IS NOT NULL AND trip_id IS NOT NULL
 AND source_time_local IS NOT NULL
), samples AS (
 SELECT * FROM ranked WHERE sample_rank=1
)
SELECT route_id,local_hour,count(*) AS vehicle_trip_hour_samples,
 count(deviation_min) AS samples_with_deviation,
 round(avg(deviation_min),2) AS mean_reported_deviation_min,
 sum(CASE WHEN deviation_min>5 THEN 1 ELSE 0 END) AS reported_over_5_min_samples,
 round(100.0*sum(CASE WHEN deviation_min>5 THEN 1 ELSE 0 END)
       /nullif(count(deviation_min),0),1) AS reported_over_5_min_pct
FROM samples
GROUP BY route_id,local_hour
ORDER BY local_hour,route_id;
