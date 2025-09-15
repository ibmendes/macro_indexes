import yfinance as yf
import pandas as pd
from datetime import date, timedelta
import pyspark.sql.functions as F

import subprocess
import sys

def get_referencia(
    pg_conn,
    schema: str = "raw",
    tabela: str = "cotacoes_indices"
):
    """
    Retorna a data de referência mais recente no banco de dados.
    pg_conn = modulo de conexão ao banco (PostgresConnector / PostgresConnection)
    schema = schema do banco (default "raw")
    tabela = tabela onde buscar a data (default "cotacoes_indices")
    """
    conn = None
    try:
        conn = pg_conn.connect("sgs_bacen")
        cur = conn.cursor()
        cur.execute(f"SELECT MAX(datacotacao) FROM {schema}.{tabela};")
        max_data = cur.fetchone()[0]  # pode ser date ou None
        cur.close()
    except Exception:
        # Se ocorrer erro, devolve None
        max_data = None
    finally:
        if conn:
            conn.close()

    return max_data

def get_indexes(
    spark,
    pg_conn,
    start = None,
    end = None,
    tickers=None,
    repair=True,
    schema: str = 'raw',
):
    """
    Obtém as informações da bibioteca do yfinance (yahoo finance)
    documentação da api: https://ranaroussi.github.io/yfinance/
    - spark: SparkSession
    - pg_conn: Conector Postgres (para eventualmente usar get_referencia)
    - start: data de inicio, se não preenchida irá atrás dos dados no banco de dados
    - fim: se não preenchida, 10 anos, se inicio for vazia irá pegar hoje
    - tickers: possível colocar uma tupla de tickers
    - repair: true corrige por dividendo, false não (default é true).
    - schema: procura ref no schema do postgres

    """
    if tickers is None:
        tickers = ['VT', '^BVSP', '^GSPC', 'IDIV.SA', 'DIVO11.SA', 'BTC-USD','^XAU']
        
    # Se datas customizadas não forem passadas, define pelo histórico no Postgres
    if start is None:
        last_ref = get_referencia(pg_conn, schema=schema)
        if last_ref is not None:
            start_ref = last_ref.strftime("%Y-%m-%d")
        else:
            start_ref = (date.today() - timedelta(days=364*10)).strftime("%Y-%m-%d")
        end_ref = (date.today()- timedelta(days=1)).strftime("%Y-%m-%d")

    else:
        # start customizado
        start_ref = start
        if end is None:
            # se end não fornecido, define 5 dias a partir do start
            start_date_obj = pd.to_datetime(start).date()
            end_ref = (start_date_obj + timedelta(days=5)).strftime("%Y-%m-%d")
        else:
            end_ref = end
        # no caso de janelas moveis quero trazer o primeiro dia (start) também, diferente do append acima
        last_ref = pd.to_datetime(start_ref).date() - timedelta(days=1)
  
    print(f"[INFO] Buscando Índices desde {pd.to_datetime(start_ref).strftime('%d/%m/%Y')} até {pd.to_datetime(end_ref).strftime('%d/%m/%Y')}...")

    #### inicio do processo de ingestão da API
    data = yf.download(
        tickers,
        start=start_ref,
        end=end_ref,
        repair=repair
        )

    # transformar MultiIndex em formato longo
    df = data.stack(level=1).reset_index()

    # renomear colunas
    df = df.rename(columns={
        "Date": "date",
        "level_1": "ticker"
    })

    ### spark fix
    df_spark = spark.createDataFrame(df)

    ## final format 
    df_spark = (
        df_spark
        .withColumn("High", F.round(df_spark["High"], 2))
        .withColumn("Low", F.round(df_spark["Low"], 2))
        .withColumn("Open", F.round(df_spark["Open"], 2))
        .withColumn("Close", F.round(df_spark["Close"], 2))
        .withColumn("Volume", F.round(df_spark["Volume"], 2))
        .withColumn("dataCotacao", F.to_date(F.col("date")))
        .withColumn("dt_ingestao",  F.current_timestamp())
        .withColumn(
            "tickerNome",
            F.when(F.col("Ticker") == "VT", F.lit("Vanguard Total World"))
            .when(F.col("Ticker") == "^BVSP", F.lit("Ibovespa"))
            .when(F.col("Ticker") == "^GSPC", F.lit("S&P 500"))
            .when(F.col("Ticker") == "IDIV.SA", F.lit("IDIV"))
            .when(F.col("Ticker") == "BTC-USD", F.lit("BTC"))
            .when(F.col("Ticker") == "^XAU", F.lit("OURO"))
            .otherwise(F.col("Ticker"))
        )
        .withColumn(
            "codigoTicker",
            F.when(F.col("Ticker") == "VT", F.lit("VT"))
            .when(F.col("Ticker") == "^BVSP", F.lit("IBOV"))
            .when(F.col("Ticker") == "^GSPC", F.lit("S&P500"))
            .when(F.col("Ticker") == "IDIV.SA", F.lit("IDIV"))
            .when(F.col("Ticker") == "DIVO11.SA", F.lit("IDIV - DIVO11 IT ETF"))
            .when(F.col("Ticker") == "BTC-USD", F.lit("BTC"))
            .when(F.col("Ticker") == "^XAU", F.lit("OURO"))
            .otherwise(F.col("Ticker"))
        )
        .select(
            F.col("dataCotacao"),
            F.col("Ticker").alias("ticker"),
            F.col("codigoTicker"),
            F.col("tickerNome"),
            F.col("Close").alias("fechamento"),
            F.col("High").alias("maiorAlta"),
            F.col("Open").alias("abertura"),
            F.col("Repaired?").alias("corrigiuDividendos"),
            F.col("Volume").alias("volume"),
            F.col("date").alias("dataHoraCotacao"),
            F.col("dt_ingestao")
        )
        .orderBy(F.col("dataCotacao").desc(), F.col("ticker")) \
    )

## filtro de duplicidades 
    df_spark = df_spark.filter(F.col("datacotacao") > start_ref) \
                       .dropDuplicates(["dataCotacao", "ticker","codigoTicker"])
    

    return df_spark
