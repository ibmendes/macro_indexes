{{ config(
    materialized='incremental',
    unique_key=['dataCotacao','ticker'],
    post_hook=[
        "COMMENT ON COLUMN {{ this }}.dataCotacao IS 'Data da cotação'",
        "COMMENT ON COLUMN {{ this }}.indicador IS 'Nome do indicador'",
        "COMMENT ON COLUMN {{ this }}.ticker IS 'Código do ticker'",
        "COMMENT ON COLUMN {{ this }}.tickernome IS 'Nome completo do ticker'",
        "COMMENT ON COLUMN {{ this }}.fechamento IS 'Preço de fechamento do índice ou moeda'",
        "COMMENT ON COLUMN {{ this }}.variacao_diaria IS 'Variação diária do índice ou moeda (em percentual)'",
        "COMMENT ON COLUMN {{ this }}.retorno_em_reais IS 'Retorno em reais para índices globais (USD), ou igual à variacao_diaria para outros'",
        "COMMENT ON COLUMN {{ this }}.dolar_fechamento IS 'Fechamento do dólar no dia'",
        "COMMENT ON COLUMN {{ this }}.dolar_variacao IS 'Variação diária do dólar'"
    ]
) }}

WITH base AS (
    SELECT *
    FROM {{ ref('variacao_indices') }}
    {% if is_incremental() %}
      WHERE dataCotacao >= (SELECT max(dataCotacao) - interval '7 days' FROM {{ this }})
    {% endif %}
),

usd AS (
    SELECT
        dataCotacao,
        fechamento AS dolar_fechamento,
        variacao_diaria AS dolar_variacao
    FROM base
    WHERE ticker = 'USD'
)

SELECT
    b.dataCotacao,
    b.indicador,
    b.ticker,
    b.tickernome,
    b.fechamento,
    b.variacao_diaria,

    CASE
        WHEN b.ticker IN ('VT', '^GSPC','BTC-USD','^XAU')
            THEN COALESCE(
                b.variacao_diaria + u.dolar_variacao + (b.variacao_diaria * u.dolar_variacao),
                b.variacao_diaria
            )
        ELSE b.variacao_diaria
    END AS retorno_em_reais,

    u.dolar_fechamento,
    u.dolar_variacao

FROM base b
LEFT JOIN LATERAL (
    SELECT u.dolar_fechamento, u.dolar_variacao
    FROM usd u
    WHERE u.dataCotacao <= b.dataCotacao
    ORDER BY u.dataCotacao DESC
    LIMIT 1
) u ON TRUE
