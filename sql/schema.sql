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

SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';

insert into DIM_CITY(city_name, latitude, longitude) values ('test',1,1);

insert into fact_air_quality(city_id, reading_time, carbon_monoxide) values (1,'2026-10-12 00:00',1297);

select * from dim_city;
select * from fact_air_quality;

INSERT INTO dim_city (city_name, latitude, longitude)
VALUES ('Mangaluru', 12.9156, 74.8560)
ON CONFLICT (city_name) DO UPDATE SET latitude = EXCLUDED.latitude, longitude = EXCLUDED.longitude;

select city_name, city_id from dim_city;