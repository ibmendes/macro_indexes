-- tests/not_null_retorno_indices.sql
SELECT *
FROM {{ ref('retorno_indices') }}
WHERE dataCotacao IS NULL
   OR ticker IS NULL
