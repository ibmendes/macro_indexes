{{ config(
    materialized='incremental',
    unique_key='dataCotacao||ticker'
) }}

WITH cdi_v AS (
    SELECT
        data as dataCotacao,
        upper(nm_indice) AS indicador,
        cod_sgs::text as ticker,
        upper(nm_indice) as tickernome,
        valor as fechamento,
        -- COALESCE(valor / NULLIF(LAG(valor) OVER (PARTITION BY cod_sgs ORDER BY data), 0) - 1, 0) AS variacao_diaria
        valor AS variacao_diaria  -- python-bcb indexes actually are already daily/monthly vars. 
    FROM raw.cdi
    {% if is_incremental() %}
        WHERE data > (SELECT max(dataCotacao) FROM {{ this }})
    {% endif %}
),

ipca_v AS (
    SELECT
        data as dataCotacao,
        upper(nm_indice) AS indicador,
        cod_sgs::text as ticker,
        upper(nm_indice) as tickernome,
        valor as fechamento,
        -- COALESCE(valor / NULLIF(LAG(valor) OVER (PARTITION BY cod_sgs ORDER BY data), 0) - 1, 0) AS variacao_diaria
        valor AS variacao_diaria  -- python-bcb indexes actually are already daily/monthly vars. 
    FROM raw.ipca
    {% if is_incremental() %}
        WHERE data > (SELECT max(dataCotacao) FROM {{ this }})
    {% endif %}
),

igpm_v AS (
    SELECT
        data as dataCotacao,
        upper(nm_indice) AS indicador,
        cod_sgs::text as ticker,
        upper(nm_indice) as tickernome,
        valor as fechamento,
        -- COALESCE(valor / NULLIF(LAG(valor) OVER (PARTITION BY cod_sgs ORDER BY data), 0) - 1, 0) AS variacao_diaria
        valor AS variacao_diaria  -- python-bcb indexes actually are already daily/monthly vars. 
    FROM raw.igpm
    {% if is_incremental() %}
        WHERE data > (SELECT max(dataCotacao) FROM {{ this }})
    {% endif %}
),

cotacoes_indices_v AS (
    SELECT
        dataCotacao,
        upper(codigoticker) AS indicador,
        upper(ticker) as ticker,
        upper(tickernome) as tickernome,
        fechamento,
        COALESCE(fechamento / NULLIF(LAG(fechamento) OVER (PARTITION BY ticker ORDER BY dataCotacao), 0) - 1, 0) AS variacao_diaria
    FROM raw.cotacoes_indices
    {% if is_incremental() %}
        WHERE dataCotacao > (SELECT max(dataCotacao) FROM {{ this }})
    {% endif %}
),

cotacao_moedas_v AS (
    SELECT
        dataCotacao,
        upper(moeda) AS indicador,
        upper(moeda) as ticker,
        upper(moeda) as tickernome,
        cotacaovenda as fechamento,
        COALESCE(cotacaovenda / NULLIF(LAG(cotacaovenda) OVER (PARTITION BY moeda ORDER BY dataCotacao), 0) - 1, 0) AS variacao_diaria
    FROM raw.cotacao_moedas
    {% if is_incremental() %}
        WHERE dataCotacao > (SELECT max(dataCotacao) FROM {{ this }})
    {% endif %}
)

SELECT * FROM cdi_v
UNION ALL
SELECT * FROM ipca_v
UNION ALL
SELECT * FROM igpm_v
UNION ALL
SELECT * FROM cotacoes_indices_v
UNION ALL
SELECT * FROM cotacao_moedas_v
