""" Coverage check: list every city and day that does not have exactly 24 rows. 
Hint: GROUP BY, then HAVING COUNT(*) <> 24."""
select c.city_name, f.reading_time::date as DAY, count(*) as row_count
from fact_air_quality f
join dim_city c on c.city_id=f.city_id
group by c.city_name,DAY
having count(*)<>24
order by c.city_name,DAY;

""" Worst time of day: for each city, the hour of day with the highest 
average PM2.5. Hint: EXTRACT(HOUR FROM reading_time)."""
-- For each city, the hour of day with the highest average PM2.5
WITH hourly AS (
    SELECT c.city_name,
           EXTRACT(HOUR FROM f.reading_time)::int AS hour_of_day,
           AVG(f.pm2_5) AS avg_pm25
    FROM fact_air_quality f
    JOIN dim_city c ON c.city_id = f.city_id
    GROUP BY c.city_name, hour_of_day
),
ranked AS (
    SELECT *, RANK() OVER (PARTITION BY city_name ORDER BY avg_pm25 DESC) AS rnk
    FROM hourly
)
SELECT city_name, hour_of_day, ROUND(avg_pm25, 1) AS avg_pm25
FROM ranked
WHERE rnk = 1
ORDER BY city_name;

"""City ranking: rank the cities by average PM2.5 using RANK() OVER (ORDER BY ...)."""
select c.city_name, round(AVG(f.pm2_5),1) as avg_pm25, 
rank() over(order by avg(f.pm2_5) desc) as rnk
from fact_air_quality f
join dim_city c on c.city_id=f.city_id
group by c.city_name
order by rnk;

"""3-day moving average of daily PM2.5 per city. 
Hint: AVG(...) OVER (PARTITION BY ... ORDER BY ... ROWS BETWEEN 2 PRECEDING AND CURRENT ROW)."""
WITH daily AS (
    SELECT city_id, reading_time::date AS day, AVG(pm2_5) AS avg_pm25
    FROM fact_air_quality
    GROUP BY city_id, day
)
SELECT c.city_name, d.day,
       ROUND(d.avg_pm25, 1) AS daily_avg,
       ROUND(AVG(d.avg_pm25) OVER (
           PARTITION BY d.city_id
           ORDER BY d.day
           ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
       ), 1) AS moving_avg_3d
FROM daily d
JOIN dim_city c ON c.city_id = d.city_id
ORDER BY c.city_name, d.day;

"""Threshold days: the number of days per city whose average PM2.5 is above a threshold. Look up WHO’s 
24-hour PM2.5 guideline value yourself and note its source in a comment. Don’t take my word or guess it."""
WITH daily AS (
    SELECT city_id, reading_time::date AS day, AVG(pm2_5) AS avg_pm25
    FROM fact_air_quality
    GROUP BY city_id, day
)
SELECT c.city_name,
       COUNT(*) FILTER (WHERE d.avg_pm25 > 15) AS days_above_guideline,
       COUNT(*) AS days_measured
FROM daily d
JOIN dim_city c ON c.city_id = d.city_id
GROUP BY c.city_name
ORDER BY days_above_guideline DESC;

"""Worst day per city: the single day with the highest average PM2.5 for each city. 
Hint: a CTE plus RANK() or ROW_NUMBER() partitioned by city."""
WITH daily AS (
    SELECT c.city_name, f.reading_time::date AS day, AVG(f.pm2_5) AS avg_pm25
    FROM fact_air_quality f
    JOIN dim_city c ON c.city_id = f.city_id
    GROUP BY c.city_name, day
),
ranked AS (
    SELECT city_name, day, avg_pm25,
           RANK() OVER (PARTITION BY city_name ORDER BY avg_pm25 DESC) AS rnk
    FROM daily
)
SELECT city_name, day, ROUND(avg_pm25, 1) AS avg_pm25
FROM ranked
WHERE rnk = 1
ORDER BY city_name;
