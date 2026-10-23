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

