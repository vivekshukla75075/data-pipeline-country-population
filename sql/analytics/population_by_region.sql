SELECT 
    region,
    SUM(population) AS total_population,
    COUNT(*) AS country_count,
    ROUND(AVG(population), 2) AS avg_population,
    MAX(population) AS max_population,
    MIN(population) AS min_population
FROM 
    country_population.countries_curated
GROUP BY 
    region
ORDER BY 
    total_population DESC;
