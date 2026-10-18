DROP TABLE IF EXISTS fact_air_quality;
DROP TABLE IF EXISTS dim_city;

CREATE TABLE dim_city(
    city_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    city_name VARCHAR(100) UNIQUE NOT NULL,
    latitude NUMERIC(9,6) NOT NULL,
    longitude NUMERIC(9,6) NOT NULL
);

CREATE TABLE fact_air_quality(
   city_id INT NOT NULL REFERENCES dim_city(city_id),
   reading_time TIMESTAMP  NOT NULL,
   pm10 NUMERIC(8,2),
   pm2_5 NUMERIC(8,2),
   carbon_monoxide NUMERIC(8,2),
   dust NUMERIC(8,2),
   carbon_dioxide NUMERIC(8,2),
   nitrogen_dioxide NUMERIC(8,2),

   
   PRIMARY KEY (city_id, reading_time)
);


select * from dim_city;
select * from fact_air_quality;



select city_name, city_id from dim_city;




select c.city_name, f.reading_time::date as DAY, count(*) as row_count
from fact_air_quality f
join dim_city c on c.city_id=f.city_id
group by c.city_name,DAY
having count(*)<>24
order by c.city_name,DAY;



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



select c.city_name, round(AVG(f.pm2_5),1) as avg_pm25, 
rank() over(order by avg(f.pm2_5) desc) as rnk
from fact_air_quality f
join dim_city c on c.city_id=f.city_id
group by c.city_name
order by rnk;


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
