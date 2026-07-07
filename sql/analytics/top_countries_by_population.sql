SELECT 
    country_name,
    region,
    subregion,
    population,
    area,
    ROUND(population / NULLIF(area, 0), 2) AS population_density
FROM 
    country_population.countries_curated
ORDER BY 
    population DESC
LIMIT 50;
