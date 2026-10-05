-- GA4 purchase funnel: product view -> add to cart -> checkout -> purchase
-- Google's public GA4 e-commerce sample (Google Merchandise Store), Nov 2020 - Jan 2021.
-- A user counts at a step only if they did it AFTER the previous step (sequenced funnel).
WITH ev AS (
  SELECT
    user_pseudo_id,
    event_name,
    event_timestamp,
    device.category AS device,
    traffic_source.medium AS medium,
    (SELECT value.int_value FROM UNNEST(event_params) WHERE key = 'ga_session_number') AS session_number
  FROM `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`
  WHERE _TABLE_SUFFIX BETWEEN '20201101' AND '20210131'
    AND event_name IN ('view_item', 'add_to_cart', 'begin_checkout', 'purchase')
),
-- Segment each user by the context of their FIRST product view.
first_view AS (
  SELECT * EXCEPT (rn) FROM (
    SELECT
      user_pseudo_id,
      event_timestamp AS t1,
      device,
      IFNULL(medium, '(none)') AS medium,
      IF(session_number = 1, 'New', 'Returning') AS user_type,
      FORMAT_TIMESTAMP('%Y-%m', TIMESTAMP_MICROS(event_timestamp)) AS month,
      ROW_NUMBER() OVER (PARTITION BY user_pseudo_id ORDER BY event_timestamp) AS rn
    FROM ev
    WHERE event_name = 'view_item'
  ) WHERE rn = 1
),
s2 AS (
  SELECT e.user_pseudo_id, MIN(e.event_timestamp) AS t2
  FROM ev e JOIN first_view f USING (user_pseudo_id)
  WHERE e.event_name = 'add_to_cart' AND e.event_timestamp >= f.t1
  GROUP BY 1
),
s3 AS (
  SELECT e.user_pseudo_id, MIN(e.event_timestamp) AS t3
  FROM ev e JOIN s2 USING (user_pseudo_id)
  WHERE e.event_name = 'begin_checkout' AND e.event_timestamp >= s2.t2
  GROUP BY 1
),
s4 AS (
  SELECT e.user_pseudo_id, MIN(e.event_timestamp) AS t4
  FROM ev e JOIN s3 USING (user_pseudo_id)
  WHERE e.event_name = 'purchase' AND e.event_timestamp >= s3.t3
  GROUP BY 1
),
users AS (
  SELECT f.*, s2.t2, s3.t3, s4.t4
  FROM first_view f
  LEFT JOIN s2 USING (user_pseudo_id)
  LEFT JOIN s3 USING (user_pseudo_id)
  LEFT JOIN s4 USING (user_pseudo_id)
),
segments AS (
  SELECT 'All users' AS segment_type, 'All' AS segment, * FROM users
  UNION ALL SELECT 'Device', device, * FROM users
  UNION ALL SELECT 'Medium', medium, * FROM users
  UNION ALL SELECT 'User type', user_type, * FROM users
  UNION ALL SELECT 'Month', month, * FROM users
)
SELECT
  segment_type,
  segment,
  COUNT(*)                         AS viewed_item,
  COUNTIF(t2 IS NOT NULL)          AS added_to_cart,
  COUNTIF(t3 IS NOT NULL)          AS began_checkout,
  COUNTIF(t4 IS NOT NULL)          AS purchased,
  ROUND(APPROX_QUANTILES(IF(t4 IS NOT NULL, (t4 - t1) / 3.6e9, NULL), 2)[OFFSET(1)], 2) AS median_hours_view_to_purchase
FROM segments
GROUP BY 1, 2
ORDER BY 1, viewed_item DESC;
